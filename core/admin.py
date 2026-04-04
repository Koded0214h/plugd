from django.contrib import admin
from .models import PlatformSetting

@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ('key', 'value', 'data_type', 'updated_at', 'updated_by')
    search_fields = ('key', 'description')
    list_filter = ('data_type',)
    readonly_fields = ('updated_at',)
    fields = ('key', 'value', 'description', 'data_type', 'updated_by')

    def save_model(self, request, obj, form, change):
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
