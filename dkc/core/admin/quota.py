from django.contrib import admin
from django.db import models
from django_admin_display import admin_display
import humanize

from dkc.core.models import Quota


@admin.register(Quota)
class QuotaAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'human_used', 'human_allowed', 'usage_percent']
    list_filter = [
        ('user', admin.EmptyFieldListFilter),
    ]
    list_select_related = ['user']

    search_fields = ['user__username']

    readonly_fields = ['used', 'usage_percent']

    @admin_display(short_description='Used', admin_order_field='used')
    def human_used(self, obj: Quota) -> str:
        return humanize.naturalsize(obj.used)

    @admin_display(short_description='Allowed', admin_order_field='used')
    def human_allowed(self, obj: Quota) -> str:
        return humanize.naturalsize(obj.allowed)

    @admin_display(
        short_description='% Used',
        admin_order_field=models.Case(
            # Prevent division by zero, and sort the result as effectively 100%
            models.When(allowed=0, then=1),
            # Multiply by 1.0 to force floating-point division
            default=(models.F('used') * 1.0 / models.F('allowed')),
            output_field=models.FloatField(),
        ),
    )
    def usage_percent(self, obj: Quota) -> str:
        if obj.allowed == 0:
            return '--'
        return '{:.1%}'.format(obj.used / obj.allowed)
