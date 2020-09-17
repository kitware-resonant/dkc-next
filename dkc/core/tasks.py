from celery import shared_task

from dkc.core.models import File


@shared_task()
def file_compute_sha512(file_id: int):
    file = File.objects.get(pk=file_id)
    file.compute_sha512()
    file.save()
