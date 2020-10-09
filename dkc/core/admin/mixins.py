from django_admin_display import admin_display


class QuotaAdminMixin:
    @admin_display(short_description='% Used')
    def usage_percent(self, quota) -> str:
        if not quota.allowed:
            return '--'
        return '{:.1%}'.format(quota.used / quota.allowed)
