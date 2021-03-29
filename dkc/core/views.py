from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@staff_member_required
def staff_home(request: HttpRequest) -> HttpResponse:
    return render(request, 'core/staff_home.html')


TREES_BY_FILE_COUNT_Q = """
SELECT folder.id, folder.name, sq.c as file_count, pg_size_pretty(folder.size) as size
FROM core_folder as folder, (
  SELECT tree.id as tree_id, count(*) as c
  FROM core_file as file, core_folder as folder, core_tree as tree
  WHERE file.folder_id = folder.id
  AND folder.tree_id = tree.id
  GROUP BY tree.id
) as sq WHERE folder.tree_id = sq.tree_id AND folder.parent_id IS NULL ORDER BY sq.c DESC
"""


@staff_member_required
def trees_by_file_count_view(request: HttpRequest) -> HttpResponse:
    with connection.cursor() as cursor:
        cursor.execute(TREES_BY_FILE_COUNT_Q)
        rows = cursor.fetchall()
    return render(request, 'core/trees_by_file_count.html', {'rows': rows})
