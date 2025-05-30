import csv
from datetime import datetime, date, time
from importlib.metadata import files

from django.db.backends.base.introspection import FieldInfo
from django.db.models import CharField
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from io import BytesIO, TextIOWrapper
import chardet
from django.views import View
from django.core.serializers import serialize
import json
from zoneinfo import ZoneInfo  # Python 3.9+
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET, require_http_methods
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.db.models import Count

from app_name.models import IrregularBlock, FieldInfo, UserProfile

def login_view(request):
    if request.method == 'POST':
        # 处理AJAX请求
        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                username = data.get('username')
                password = data.get('password')
                user_type = data.get('user_type', 'user')
            except:
                return JsonResponse({'status': 'error', 'message': '无效的请求数据'}, status=400)
        else:
            # 处理表单提交
            username = request.POST.get('username')
            password = request.POST.get('password')
            user_type = request.POST.get('user_type', 'user')
        
        # 验证用户
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # 检查用户类型是否匹配
            is_admin = user.is_staff or user.groups.filter(name='管理员').exists()
            if (user_type == 'admin' and not is_admin) or (user_type == 'user' and is_admin):
                if request.headers.get('Content-Type') == 'application/json':
                    return JsonResponse({'status': 'error', 'message': '用户类型不匹配'})
                else:
                    return render(request, 'login.html', {'error': '用户类型不匹配'})
            
            login(request, user)
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'status': 'success', 'redirect': '/index/'})
            else:
                return redirect('/index/')
        else:
            if request.headers.get('Content-Type') == 'application/json':
                return JsonResponse({'status': 'error', 'message': '用户名或密码错误'})
            else:
                return render(request, 'login.html', {'error': '用户名或密码错误'})
    
    # GET请求显示登录页面
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('/login/')

def is_admin(user):
    return user.is_staff or user.groups.filter(name='管理员').exists()

def is_user(user):
    return user.groups.filter(name='普通用户').exists()

@login_required(login_url='/login/')
def index(request):
    if is_admin(request.user):
        return render(request, 'admin_index.html')
    else:
        return render(request, 'index.html')

@login_required(login_url='/login/')
@user_passes_test(is_admin)
def admin_dashboard(request):
    # 获取所有用户
    users = User.objects.all()
    
    # 获取统计数据
    total_users = User.objects.count()
    total_fields = FieldInfo.objects.count()
    total_tracks = IrregularBlock.objects.count()
    
    context = {
        'users': users,
        'total_users': total_users,
        'total_fields': total_fields,
        'total_tracks': total_tracks
    }
    
    return render(request, 'admin_dashboard.html', context)

@login_required(login_url='/login/')
@user_passes_test(is_admin)
def admin_track_visualization(request):
    # 获取所有地块信息
    fields = FieldInfo.objects.all()
    
    # 获取用户统计数据（与admin_dashboard相同）
    users = User.objects.all()
    total_users = User.objects.count()
    total_fields = FieldInfo.objects.count()
    total_tracks = IrregularBlock.objects.count()
    
    context = {
        'fields': fields,
        'users': users,
        'total_users': total_users,
        'total_fields': total_fields,
        'total_tracks': total_tracks
    }
    
    return render(request, 'admin_index.html', context)

def upload_csv(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')

        # 验证文件
        if not csv_file or not csv_file.name.endswith('.csv'):
            return HttpResponse("请上传有效的 CSV 文件", status=400)

        try:
            # 获取文件名（不包含扩展名）
            field_name = csv_file.name.replace('.csv', '')
            
            # 创建地块信息
            field_info = FieldInfo.objects.create(
                file_name=field_name
            )

            # 关键修复：直接读取二进制数据并保存到 BytesIO
            raw_data = csv_file.read()
            csv_file.close()  # 显式关闭文件

            # 编码检测（强制回退到 GB18030）
            result = chardet.detect(raw_data)
            encoding = result['encoding'] if result['confidence'] > 0.7 else 'gb18030'
            if not encoding:  # 防止 encoding=None
                encoding = 'gb18030'

            # 使用 BytesIO 重建文件流
            csv_stream = BytesIO(raw_data)
            csv_text = TextIOWrapper(csv_stream, encoding=encoding, errors='replace')

            reader = csv.DictReader(csv_text)
            objs = []
            error_log = []

            for row_num, row in enumerate(reader, start=1):
                try:
                    # 数据清洗和转换（提取为独立处理逻辑）
                    def parse_int(value, field_name):
                        try:
                            return int(float(value))  # 兼容浮点型数值
                        except:
                            raise ValueError(f"字段 [{field_name}] 值 '{value}' 无法转换为整数")

                    def parse_bool(value):
                        value = str(value).strip().upper()
                        if value in {'1', 'TRUE', 'T', 'YES', 'Y'}:
                            return True
                        elif value in {'0', 'FALSE', 'F', 'NO', 'N'}:
                            return False
                        raise ValueError(f"无效的布尔值: {value}")

                    # 时间处理（兼容多种分隔符）
                    gps_time_str = row['GPS时间'].replace('/', '-').replace(' ', 'T', 1)
                    try:
                        gps_time = datetime.fromisoformat(gps_time_str)
                    except:
                        gps_time = datetime.strptime(gps_time_str, '%Y-%m-%dT%H:%M')
                    gps_time = gps_time.replace(tzinfo=ZoneInfo("Asia/Shanghai"))  # 关键修复

                    # 构建数据对象
                    objs.append(
                        IrregularBlock(
                            point_index=parse_int(row['序列号'], '序列号'),
                            gps_time=gps_time,
                            longitude=float(row['经度']),
                            latitude=float(row['纬度']),
                            x=float(row['x']),
                            y=float(row['y']),
                            velocity=float(row['速度(km/h)']),
                            yaw=float(row['航向']),
                            state=parse_bool(row['工作状态']),
                            amplitude=float(row['幅宽(m)']),
                            depth=parse_int(row['深度(mm)'], '深度(mm)'),
                            DepthValue=parse_int(row['深度标准值'], '深度标准值'),
                            field_name=field_info  # 设置外键关联
                        )
                    )
                except Exception as e:
                    error_log.append(f"第 {row_num} 行错误: {str(e)}")
                    continue

            # 批量插入（带错误回滚保护）
            if objs:
                batch_size = 100
                try:
                    IrregularBlock.objects.bulk_create(objs, batch_size=batch_size)
                except Exception as e:
                    return HttpResponse(f"数据库写入失败: {str(e)}", status=500)

            # 生成导入报告
            success_count = len(objs)
            error_report = "\n".join(error_log) if error_log else "无"
            return HttpResponse(
                f"成功导入 {success_count} 条数据，错误 {len(error_log)} 条\n错误明细:\n{error_report}"
            )

        except Exception as e:
            return HttpResponse(f"服务器处理错误: {str(e)}", status=500)

    return render(request, 'index.html')

@require_GET
def get_field_info(request):
    try:
        fields = FieldInfo.objects.annotate(
            track_count=Count('irregularblock')
        ).values('file_name', 'track_count')
        return JsonResponse({
            'status': 'success',
            'data': list(fields)
        })
    except Exception as e:
        print(f"获取地块信息时出错: {str(e)}")  # 添加错误日志
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@require_GET
def get_track_data(request):
    try:
        field_name = request.GET.get('field_name')
        
        if field_name:
            # 获取指定地块的所有轨迹数据
            locations = IrregularBlock.objects.filter(
                field_name__file_name=field_name
            ).select_related('field_name').order_by('gps_time')
        else:
            # 获取所有轨迹数据
            locations = IrregularBlock.objects.all().select_related('field_name').order_by('gps_time')
        
        # 处理数据
        data = []
        for loc in locations:
            try:
                data.append({
                    'point_index': str(loc.point_index),
                    'gps_time': str(loc.gps_time) if loc.gps_time else None,
                    'longitude': float(loc.longitude),
                    'latitude': float(loc.latitude),
                    'velocity': float(loc.velocity),
                    'yaw': float(loc.yaw),
                    'state': bool(loc.state),
                    'file_name': loc.field_name.file_name if loc.field_name else None
                })
            except Exception as e:
                print(f"处理记录时出错: {str(e)}, 记录ID: {loc.point_index}")
                continue

        return JsonResponse({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        print(f"获取轨迹数据时出错: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': f"服务器错误: {str(e)}"
        }, status=500)

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        user_type = request.POST.get('user_type', 'user')  # 默认为普通用户
        
        # 验证密码是否匹配
        if password != confirm_password:
            return render(request, 'register.html', {'error': '两次输入的密码不一致'})
        
        # 检查用户名是否已存在
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': '用户名已存在'})
        
        # 检查邮箱是否已存在
        if User.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': '邮箱已被注册'})
        
        # 创建新用户
        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            user.save()
            
            # 根据用户类型添加到相应的组
            if user_type == 'admin':
                admin_group, created = Group.objects.get_or_create(name='管理员')
                user.groups.add(admin_group)
                user.is_staff = True  # 设置为管理员
                user.save()
            else:
                user_group, created = Group.objects.get_or_create(name='普通用户')
                user.groups.add(user_group)
            
            # 自动登录新用户
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
        except Exception as e:
            return render(request, 'register.html', {'error': '注册失败，请稍后重试'})
    
    return render(request, 'register.html')

@login_required(login_url='/login/')
@user_passes_test(is_admin)
def admin_settings(request):
    # 获取系统设置
    context = {
        'settings': {
            'site_name': '农业轨迹分析系统',
            'version': '1.0.0',
            'admin_email': 'admin@example.com'
        }
    }
    return render(request, 'admin_settings.html', context)

@login_required
@user_passes_test(is_admin)
def get_users(request):
    """获取所有非管理员用户列表"""
    try:
        # 获取所有非管理员用户
        users = User.objects.filter(is_staff=False).values(
            'id', 'username', 'email', 'date_joined', 'last_login'
        )
        return JsonResponse({
            'status': 'success',
            'data': list(users)
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["DELETE"])
def delete_user(request, user_id):
    """删除指定用户"""
    try:
        # 确保不能删除管理员和自己
        if request.user.id == user_id:
            return JsonResponse({
                'status': 'error',
                'message': '不能删除当前登录的管理员账号'
            }, status=400)
            
        user = User.objects.get(id=user_id)
        if user.is_staff:
            return JsonResponse({
                'status': 'error',
                'message': '不能删除管理员账号'
            }, status=400)
            
        user.delete()
        return JsonResponse({
            'status': 'success',
            'message': '用户删除成功'
        })
    except User.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '用户不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
@user_passes_test(is_admin)
@require_http_methods(["DELETE"])
def delete_field(request, field_name):
    """删除指定地块及其所有轨迹数据"""
    try:
        # 获取地块信息
        field = FieldInfo.objects.get(file_name=field_name)
        
        # 删除地块（这会级联删除所有相关的轨迹数据）
        field.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': '地块删除成功'
        })
    except FieldInfo.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': '地块不存在'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def get_user_info(request):
    """获取用户信息"""
    try:
        user = request.user
        # 获取或创建用户档案
        profile, created = UserProfile.objects.get_or_create(user=user)
        
        return JsonResponse({
            'status': 'success',
            'username': user.username,
            'email': user.email,
            'phone': profile.phone or '',
            'organization': profile.organization or '',
        })
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

@login_required
def update_user_info(request):
    """更新用户信息"""
    if request.method == 'POST':
        try:
            user = request.user
            user.email = request.POST.get('email', user.email)
            
            # 更新或创建用户档案
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone = request.POST.get('phone', profile.phone)
            profile.organization = request.POST.get('organization', profile.organization)
            profile.save()
            
            return JsonResponse({'status': 'success'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})

@login_required
def change_password(request):
    """修改密码"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        
        # 验证当前密码
        if not request.user.check_password(current_password):
            return JsonResponse({'status': 'error', 'message': '当前密码错误'})
        
        # 更新密码
        request.user.set_password(new_password)
        request.user.save()
        
        # 更新session
        update_session_auth_hash(request, request.user)
        
        return JsonResponse({'status': 'success'})
    return JsonResponse({'status': 'error', 'message': '无效的请求方法'})


