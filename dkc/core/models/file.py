import hashlib
from typing import Optional

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from .folder import Folder
from .metadata import UserMetadataField


class File(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['folder', 'name'])]
        ordering = ['name']
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['folder', 'name'], name='file_siblings_name_unique'
            ),
        ]

    name = models.CharField(
        max_length=255,
        validators=[
            validators.RegexValidator(
                regex='/',
                inverse_match=True,
                message='Name may not contain forward slashes.',
            )
        ],
    )

    description = models.TextField(max_length=3000, blank=True)
    content_type = models.CharField(max_length=255, default='application/octet-stream')
    blob = models.FileField()
    size = models.PositiveBigIntegerField(editable=False)
    sha512 = models.CharField(max_length=128, blank=True, default='', db_index=True, editable=False)
    user_metadata = UserMetadataField()

    creator = models.ForeignKey(User, null=True, on_delete=models.SET_NULL, editable=False)
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='files')

    @property
    def short_checksum(self) -> Optional[str]:
        return self.sha512[:10] if self.sha512 else None

    def compute_sha512(self) -> None:
        hasher = hashlib.sha512()
        with self.blob.open() as blob:
            for chunk in blob.chunks():
                hasher.update(chunk)
        self.sha512 = hasher.hexdigest()

    def clean(self) -> None:
        if self.folder.child_folders.filter(name=self.name).exists():
            raise ValidationError(
                {'name': f'There is already a folder here with the name "{self.name}".'}
            )
        super().clean()


@receiver(models.signals.pre_save, sender=File)
def _file_pre_save(sender, instance, *args, **kwargs):
    # TODO this is where we might handle quotas
    instance.size = instance.blob.size
