from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest
from django_admin_display import admin_display

from dkc.core.models import File
from dkc.core.tasks import file_compute_sha512


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'short_checksum', 'created', 'creator', 'folder']
    list_display_links = ['id', 'name']
    list_filter = [
        ('sha512', admin.EmptyFieldListFilter),
        ('created', admin.DateFieldListFilter),
        'creator__username',
    ]
    list_select_related = True

    search_fields = ['name']
    actions = ['compute_sha512']

    fields = [
        'name',
        'description',
        'user_metadata',
        'blob',
        'sha512',
        'size',
        'creator',
        'created',
        'modified',
        'folder',
    ]
    autocomplete_fields = ['folder']

    def get_readonly_fields(self, request, obj=None):
        fields = ['sha512', 'size', 'created', 'modified', 'creator']
        # Allow setting of folder only on initial creation
        if obj is None:
            return fields
        else:
            return fields + ['folder']

    @admin_display(
        short_description='Checksum prefix',
        empty_value_display='Not computed',
        # Sorting by checksum also sorts the prefix values
        admin_order_field='sha512',
    )
    def short_checksum(self, file: File):
        return file.short_checksum

    @admin_display(short_description='Recompute checksum')
    def compute_sha512(self, request: HttpRequest, queryset: QuerySet):
        for file in queryset:
            file_compute_sha512.delay(file.pk)
        self.message_user(request, f'{len(queryset)} files queued', messages.SUCCESS)
