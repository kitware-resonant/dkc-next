from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, F
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render

from dkc.core.models import Tree


@staff_member_required
def staff_home(request: HttpRequest) -> HttpResponse:
    return render(request, 'core/staff_home.html')


@staff_member_required
def trees_by_file_count_view(request: HttpRequest) -> HttpResponse:
    trees_annotated = (
        Tree.objects.annotate(num_files=Count('all_folders__files'))
        .filter(all_folders__parent__isnull=True)
        .annotate(
            name=F('all_folders__name'),
            size=F('all_folders__size'),
        )
        .order_by('-num_files')
    )
    return render(request, 'core/trees_by_file_count.html', {'trees': trees_annotated})
