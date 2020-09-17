from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.db.models import Q, QuerySet
from django.http import HttpRequest
from django_admin_display import admin_display

from dkc.core.models import File
from dkc.core.tasks import file_compute_sha512


class _FileChecksumExistsFilter(admin.SimpleListFilter):
    title = 'checksum computed'
    parameter_name = 'checksum_exists'

    def lookups(self, request: HttpRequest, model_admin: ModelAdmin):
        return [('yes', 'Yes'), ('no', 'No')]

    def queryset(self, request: HttpRequest, queryset: QuerySet) -> QuerySet:
        value = self.value()
        if value == 'yes':
            return queryset.filter(~Q(checksum=''))
        elif value == 'no':
            return queryset.filter(checksum='')
        return queryset


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'short_checksum', 'created', 'owner', 'folder']
    list_display_links = ['id', 'name']
    list_filter = [
        _FileChecksumExistsFilter,
        ('created', admin.DateFieldListFilter),
        'owner__username',
    ]
    list_select_related = True
    # list_select_related = ['owner']

    search_fields = ['name']
    actions = ['compute_sha512']

    fields = ['name', 'blob', 'sha512', 'owner', 'created', 'modified']
    autocomplete_fields = ['owner']
    readonly_fields = ['sha512', 'size', 'created', 'modified', 'folder']

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
