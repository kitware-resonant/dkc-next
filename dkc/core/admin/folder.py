from django.contrib import admin
from treebeard.admin import TreeAdmin
from treebeard.forms import movenodeform_factory

from dkc.core.models import Folder

# @admin.register(Folder)
# class FolderAdmin(admin.ModelAdmin):
#     list_display = ['id', 'name']


@admin.register(Folder)
class FolderTreeAdmin(TreeAdmin):
    form = movenodeform_factory(Folder)

    list_display = ['name']
