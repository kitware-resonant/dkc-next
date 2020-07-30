from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import render
from django.views.generic import ListView


from .models import File


class GalleryView(ListView):
    queryset = File.objects.order_by('created')
    template_name = 'gallery.html'
    paginate_by = 20


def file_summary(request):
    return render(
        request,
        'summary.html',
        {
            'user_summary': User.objects.annotate(
                processed_files=Count('file', filter=Q(file__checksum__isnull=False)),
                unprocessed_files=Count('file', filter=Q(file__checksum__isnull=True)),
            )
        },
    )
