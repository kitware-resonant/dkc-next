import hashlib
from typing import Optional, Type

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
from girder_utils.models import JSONObjectField
from s3_file_field import S3FileField

from ..permissions import Permission
from .folder import Folder
from .tree import Tree


class File(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['folder', 'name'])]
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['folder', 'name'], name='file_siblings_name_unique'),
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
    size = models.PositiveBigIntegerField()
    content_type = models.CharField(max_length=255, default='application/octet-stream')
    blob = S3FileField(blank=True)
    sha512 = models.CharField(max_length=128, blank=True, default='', db_index=True, editable=False)
    user_metadata = JSONObjectField()
    folder = models.ForeignKey(Folder, on_delete=models.CASCADE, related_name='files')
    # Prevent deletion of User if it has Folders referencing it
    creator = models.ForeignKey(User, on_delete=models.PROTECT)

    @property
    def abs_path(self) -> str:
        """Get a string representation of this File's absolute path."""
        return f'{self.folder.abs_path}{self.name}'

    @property
    def public(self) -> bool:
        return self.folder.tree.public

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
            raise ValidationError({'name': 'A folder with that name already exists here.'})
        super().clean()

    @classmethod
    def filter_by_permission(
        cls, user: User, permission: Permission, queryset: models.QuerySet['File']
    ) -> models.QuerySet['File']:
        """Filter a queryset according to a user's access.

        This method uses the tree's filter_by_permission method to create a queryset containing
        *all* trees with the appropriate permission level.  This queryset is used as a subquery
        to filter the provided queryset by traversing through the folder->tree relationship.
        """
        tree_query = Tree.filter_by_permission(user, permission, Tree.objects).values('pk')
        return queryset.filter(folder__tree__in=models.Subquery(tree_query))

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Return whether the given user has a specific permission for the file."""
        return self.folder.tree.has_permission(user, permission)


@receiver(models.signals.pre_save, sender=File)
def _file_pre_save(sender: Type[File], instance: File, **kwargs):
    # TODO if we allow changing a file's blob & size, we'll need more logic here
    if not instance.pk:
        instance.folder.increment_size(instance.size)


@receiver(models.signals.post_delete, sender=File)
def _file_post_delete(sender: Type[File], instance: File, **kwargs):
    instance.folder.increment_size(-instance.size)
