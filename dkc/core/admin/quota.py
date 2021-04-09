from django.contrib import admin
from django.db import models
import humanize

from dkc.core.models import Quota


@admin.register(Quota)
class QuotaAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'human_used', 'human_allowed', 'usage_percent']
    list_select_related = ['user']

    search_fields = ['user__username']

    readonly_fields = ['used', 'usage_percent']

    @admin.display(description='Used', ordering='used')
    def human_used(self, obj: Quota) -> str:
        return humanize.naturalsize(obj.used, binary=True)

    @admin.display(description='Allowed', ordering='used')
    def human_allowed(self, obj: Quota) -> str:
        return humanize.naturalsize(obj.allowed, binary=True)

    @admin.display(
        description='% Used',
        ordering=models.Case(
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
