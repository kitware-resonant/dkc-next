from celery import shared_task

from dkc.core.models import File, Folder


@shared_task()
def file_compute_sha512(file_id: int):
    file = File.objects.get(pk=file_id)
    file.compute_sha512()
    file.save()


@shared_task()
def delete_folder(folder_id: int):
    Folder.objects.get(pk=folder_id).delete()
