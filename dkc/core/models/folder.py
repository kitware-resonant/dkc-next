from __future__ import annotations

from typing import List

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from dkc.core.exceptions import MaxFolderDepthExceeded
from dkc.core.models.metadata import UserMetadataField

from .quota import Quota


class Folder(TimeStampedModel, models.Model):
    MAX_TREE_HEIGHT = 30

    class Meta:
        indexes = [models.Index(fields=['parent', 'name'])]
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='folder_siblings_name_unique'),
            models.UniqueConstraint(
                fields=['name'], condition=models.Q(parent=None), name='root_folder_name_unique'
            ),
            models.CheckConstraint(
                check=(
                    (models.Q(parent__isnull=True) & models.Q(quota__isnull=False))
                    | (models.Q(parent__isnull=False) & models.Q(quota__isnull=True))
                ),
                name='root_quota_not_null',
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

    depth = models.PositiveSmallIntegerField(
        validators=[
            validators.MaxValueValidator(MAX_TREE_HEIGHT, message='Maximum folder depth exceeded.'),
        ],
        editable=False,
    )

    description = models.TextField(max_length=3000, blank=True)
    user_metadata = UserMetadataField()

    used = models.PositiveBigIntegerField(default=0)

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_folders'
    )
    root_folder = models.ForeignKey(
        'self', on_delete=models.DO_NOTHING, blank=True, null=True, related_name='+'
    )

    # Prevent deletion of User if it has Folders referencing it
    owner = models.ForeignKey(User, on_delete=models.PROTECT)

    # Prevent deletion of a Quota if it has Folders referencing it,
    # unless Quota is also being deleted implicitly via a permitted CASCADE
    quota = models.ForeignKey(Quota, null=True, on_delete=models.RESTRICT)

    @property
    def effective_quota(self) -> Quota:
        if self.parent is None:
            # Optimization for root folder
            return self.quota
        return self.root_folder.quota

    def path_to_root(self) -> List[Folder]:
        folder = self
        path = [folder]
        while folder.parent is not None:
            folder = folder.parent
            path.append(folder)
            if len(path) > self.MAX_TREE_HEIGHT:
                raise MaxFolderDepthExceeded()

        return path[::-1]

    def clean(self) -> None:
        if self.parent and self.parent.files.filter(name=self.name).exists():
            raise ValidationError(
                {'name': f'There is already a file here with the name "{self.name}".'}
            )
        super().clean()

    def __str__(self) -> str:
        return f'{self.name} ({self.id})'


@receiver(models.signals.pre_save, sender=Folder)
def _folder_pre_save(sender, instance, *args, **kwargs):
    if instance.depth is None:
        if instance.parent is None:
            instance.depth = 0
        else:
            instance.depth = instance.parent.depth + 1
            if instance.depth > Folder.MAX_TREE_HEIGHT:
                raise MaxFolderDepthExceeded()

    if instance.root_folder is None and instance.parent is not None:
        instance.root_folder = instance.parent.root_folder


@receiver(models.signals.post_save, sender=Folder)
def _folder_post_save(sender, instance, *args, **kwargs):
    if instance.parent is None and instance.root_folder is None:
        instance.root_folder = instance
        instance.save()
