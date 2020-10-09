from typing import Type

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from .folder import Folder


class FolderQuota(models.Model):
    folder = models.OneToOneField(
        Folder, primary_key=True, on_delete=models.CASCADE, related_name='quota'
    )
    used = models.PositiveBigIntegerField(default=0)
    allowed = models.PositiveBigIntegerField(null=True, blank=True)

    def clean(self) -> None:
        if self.folder.parent is not None:
            raise ValidationError({'folder': 'Only root folders may have quotas.'})

        if self.allowed is not None and self.used > self.allowed:
            raise ValidationError({'allowed': 'Must not be less than used amount.'})


@receiver(post_save, sender=Folder)
def _create_root_folder_quota(sender: Type[Folder], instance: Folder, created: bool, **kwargs):
    if created and instance.parent is None:
        FolderQuota(folder=instance, allowed=None).save()
