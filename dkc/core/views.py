from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, F, Max
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render

from dkc.core.models import Tree


@staff_member_required
def staff_home(request: HttpRequest) -> HttpResponse:
    return render(request, 'core/staff_home.html')


@staff_member_required
def staff_tree_list(request: HttpRequest) -> HttpResponse:
    sort_by = request.GET.get('sort_by', 'files')
    try:
        order_by = {
            'files': '-num_files',
            'size': '-size',
            'latest_file': F('latest_file').desc(nulls_last=True),
        }[sort_by]
    except KeyError:
        raise Http404('Invalid sort_by')

    trees_annotated = (
        Tree.objects.annotate(
            num_files=Count('all_folders__files'),
            latest_file=Max('all_folders__files__created'),
        )
        .filter(all_folders__parent__isnull=True)
        .annotate(
            name=F('all_folders__name'),
            size=F('all_folders__size'),
        )
        .order_by(order_by)
    )
    return render(request, 'core/staff_tree_list.html', {'trees': trees_annotated})
