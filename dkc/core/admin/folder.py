from django.contrib import admin
from django.db import transaction

from dkc.core.models import Folder, Tree


@admin.register(Folder)
class FolderAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'parent']
    list_display_links = ['id', 'name']

    search_fields = ['name', 'id']

    @transaction.atomic
    def save_model(self, request, obj: Folder, form, change: bool):
        if not change:
            if obj.parent:
                obj.tree = obj.parent.tree
            else:
                obj.tree = Tree.objects.create(quota=obj.creator.quota)
        super().save_model(request, obj, form, change)
