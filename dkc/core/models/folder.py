from __future__ import annotations

from typing import List, Type

from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from dkc.core.exceptions import MaxFolderDepthExceeded
from dkc.core.models.metadata import UserMetadataField


class Folder(TimeStampedModel, models.Model):
    MAX_TREE_HEIGHT = 30

    class Meta:
        indexes = [models.Index(fields=['parent', 'name'])]
        ordering = ['name']
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['parent', 'name'], name='folder_siblings_name_unique'
            ),
            models.constraints.UniqueConstraint(
                fields=['name'], condition=models.Q(parent=None), name='root_folder_name_unique'
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

    # TODO: What max_length?
    description = models.TextField(max_length=3000, blank=True)
    user_metadata = UserMetadataField()

    # # TODO: owner on_delete policy?
    # owner = models.ForeignKey(User, on_delete=models.CASCADE)

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_folders'
    )
    root_folder = models.ForeignKey(
        'self', on_delete=models.DO_NOTHING, blank=True, null=True, related_name='+'
    )

    # # Prevent deletion of quotas while a folder references them
    # quota = models.ForeignKey(Quota, on_delete=models.PROTECT)

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


@receiver(models.signals.pre_save, sender=Folder)
def _folder_pre_save(sender: Type[Folder], instance: Folder, **kwargs):
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
def _folder_post_save(sender: Type[Folder], instance: Folder, created: bool, **kwargs):
    if instance.parent is None and instance.root_folder is None:
        instance.root_folder = instance
        instance.save()
