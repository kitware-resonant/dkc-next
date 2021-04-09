from django.contrib import admin
from django.db.models import F

from dkc.core.models import Tree


@admin.register(Tree)
class TreeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'public', 'quota']
    list_display_links = ['id']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(all_folders__parent__isnull=True).annotate(name=F('all_folders__name'))
        return qs

    @admin.display(description='Root folder name', ordering='name')
    def name(self, obj: Tree) -> str:
        return obj.name
