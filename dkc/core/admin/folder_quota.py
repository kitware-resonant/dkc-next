from django.contrib import admin

from dkc.core.models import FolderQuota

from .mixins import QuotaAdminMixin


@admin.register(FolderQuota)
class FolderQuotaAdmin(admin.ModelAdmin, QuotaAdminMixin):
    list_display = ['folder', 'used', 'allowed', 'usage_percent']
    list_display_links = ['folder']

    search_fields = ['folder__name', 'folder__id']

    readonly_fields = ['used', 'usage_percent']

    autocomplete_fields = ['folder']
