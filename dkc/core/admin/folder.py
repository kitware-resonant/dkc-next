from django.contrib import admin

from dkc.core.models import Folder


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'parent']
    list_display_links = ['id', 'name']

    search_fields = ['name', 'id']
