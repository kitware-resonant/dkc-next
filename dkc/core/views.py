from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


@staff_member_required
def staff_home(request: HttpRequest) -> HttpResponse:
    return render(request, 'core/staff_home.html')
