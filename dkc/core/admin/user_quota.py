from django.contrib import admin

from dkc.core.models import UserQuota

from .mixins import QuotaAdminMixin


@admin.register(UserQuota)
class UserQuotaAdmin(admin.ModelAdmin, QuotaAdminMixin):
    list_display = ['user', 'used', 'allowed', 'usage_percent']
    list_display_links = ['user']

    search_fields = ['user__username']

    readonly_fields = ['used', 'usage_percent']
