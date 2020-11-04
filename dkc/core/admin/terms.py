from django.contrib import admin

from dkc.core.models import Terms


@admin.register(Terms)
class TermsAdmin(admin.ModelAdmin):
    list_display = ['tree', 'text_preview', 'checksum']
    list_display_links = ['tree']

    search_fields = ['tree__id']

    def text_preview(self, terms: Terms, limit=100):
        if len(terms.text) > limit:
            return f'{terms.text[:limit]}...'
        return terms.text
