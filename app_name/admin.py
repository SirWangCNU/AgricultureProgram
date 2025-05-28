from django.contrib import admin
from .models import FieldInfo

@admin.register(FieldInfo)
class FieldInfoAdmin(admin.ModelAdmin):
    list_display = ('file_index', 'file_name')
    search_fields = ('file_index', 'file_name')
