from typing import Type

from django.core.exceptions import ValidationError
from django.db import models, transaction
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

    @transaction.atomic
    def save(self, *args, **kwargs) -> None:
        if self.used and self.pk and self.allowed is not None:
            # Detect if this is a folder being given a custom quota when it previously had none.
            # If so, we must transfer that amount from the owner's usage.
            stored = FolderQuota.objects.get(pk=self.pk)
            if stored.allowed is None:
                user_quota = self.folder.owner.quota
                user_quota.used = models.F('used') - self.used
                user_quota.save(update_fields=['used'])
                user_quota.refresh_from_db()
        # TODO should we also support a folder going from having a quota to being put back
        # toward a user quota? Never needed that case before, but might be good for consistency.

        super().save(*args, **kwargs)


@receiver(post_save, sender=Folder)
def _create_root_folder_quota(sender: Type[Folder], instance: Folder, created: bool, **kwargs):
    if created and instance.parent is None:
        FolderQuota(folder=instance, allowed=None).save()
