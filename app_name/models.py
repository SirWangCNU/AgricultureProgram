#from distutils.command.install import value

from django.db import models
from django.contrib.auth.models import User


class IrregularBlock(models.Model):
    """地块不规则区域监测数据"""
    id = models.AutoField(primary_key=True)
    point_index = models.IntegerField(verbose_name="序列号")
    gps_time = models.DateField(verbose_name="GPS时间")
    longitude = models.FloatField(verbose_name="经度")
    latitude = models.FloatField(verbose_name="纬度")
    x = models.FloatField(verbose_name="X坐标")
    y = models.FloatField(verbose_name="Y坐标")
    velocity = models.FloatField(verbose_name="速度(km/h)")
    yaw = models.FloatField(verbose_name="航向")
    field_name = models.ForeignKey('FieldInfo', on_delete=models.CASCADE, to_field='file_name', db_column='field_name', verbose_name="地块名称")

    # 假设工作状态为布尔值（True=正常，False=异常）
    STATE_CHOICES = (
        (True, "正常"),
        (False, "异常"),
    )
    state = models.BooleanField(choices=STATE_CHOICES, verbose_name="工作状态")

    amplitude = models.FloatField(verbose_name="幅度")
    depth = models.IntegerField(verbose_name="深度")
    DepthValue = models.IntegerField(verbose_name="深度标准值")

    class Meta:
        db_table = "point_info"
        verbose_name = "地块数据表"
        verbose_name_plural = verbose_name  # 避免管理后台显示中文复数问题

    def __str__(self):
        return f"地块 {self.point_index}"


class FieldInfo(models.Model):
    file_index = models.BigAutoField(primary_key=True, verbose_name='地块编号')
    file_name = models.CharField(max_length=100, unique=True, verbose_name='地块名称')
    
    class Meta:
        verbose_name = '地块信息'
        verbose_name_plural = '地块信息'
        db_table = 'field_info'
        ordering = ['file_index']
    
    def __str__(self):
        return f"{self.file_index} - {self.file_name}"


class UserProfile(models.Model):
    """用户档案模型"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name='手机号码')
    organization = models.CharField(max_length=100, blank=True, null=True, verbose_name='所属单位')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = '用户档案'
        verbose_name_plural = verbose_name

    def __str__(self):
        return f"{self.user.username}的档案"