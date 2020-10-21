from django.contrib import admin
from django_admin_display import admin_display

from dkc.core.models import Quota


@admin.register(Quota)
class QuotaAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'used', 'allowed', 'usage_percent']
    list_filter = [
        ('user', admin.EmptyFieldListFilter),
    ]
    list_select_related = ['user']

    search_fields = ['user__username']

    readonly_fields = ['used', 'usage_percent']

    @admin_display(short_description='% Used')
    def usage_percent(self, obj: Quota) -> str:
        if not obj.allowed:
            return '--'
        return '{:.1%}'.format(obj.used / obj.allowed)
