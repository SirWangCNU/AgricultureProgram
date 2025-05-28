"""
URL configuration for djangoProject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from sys import path_hooks

from django.contrib import admin
from django.urls import path, include

from app_name.views import (
    index, upload_csv, get_field_info, get_track_data, 
    login_view, logout_view, register, admin_dashboard, 
    admin_track_visualization, admin_settings, get_users, 
    delete_user, delete_field, get_user_info, update_user_info, 
    change_password
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='login'),  # 将登录页面设置为根路径
    path('index/', index, name='index'),
    path('upload/', upload_csv, name='upload_csv'),
    path('api/fields/', get_field_info, name='get_field_info'),
    path('api/fields/<str:field_name>/', delete_field, name='delete_field'),
    path('api/tracks/', get_track_data, name='get_track_data'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),  # 添加注册路由
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),  # 添加管理员仪表盘路由
    path('admin/track-visualization/', admin_track_visualization, name='admin_track_visualization'),  # 添加轨迹可视化路由
    path('admin/settings/', admin_settings, name='admin_settings'),  # 添加系统设置路由
    
    # 用户管理API路由
    path('api/users/', get_users, name='get_users'),
    path('api/users/<int:user_id>/', delete_user, name='delete_user'),
    path('api/user-info/', get_user_info, name='get_user_info'),  # 添加用户信息API路由
    path('api/update-user-info/', update_user_info, name='update_user_info'),
    path('api/change-password/', change_password, name='change_password'),
]
