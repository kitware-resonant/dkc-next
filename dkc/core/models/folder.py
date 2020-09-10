from __future__ import annotations

from typing import List

from django.core import validators
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from dkc.core.exceptions import MaxFolderDepthExceeded


class Folder(TimeStampedModel, models.Model):
    MAX_TREE_HEIGHT = 30

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
    description = models.TextField(max_length=3000)

    # # TODO: owner on_delete policy?
    # owner = models.ForeignKey(User, on_delete=models.CASCADE)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True)

    @property
    def child_folders(self):
        """Provide a QuerySet of the child folders of this folder."""
        return Folder.objects.filter(parent=self)

    # # Prevent deletion of quotas while a folder references them
    # quota = models.ForeignKey(Quota, on_delete=models.PROTECT)

    # TimeStampedModel also provides "created" and "modified" fields

    def path_to_root(self) -> List[Folder]:
        folder = self
        path = [folder]
        while folder.parent is not None:
            folder = folder.parent
            path.append(folder)
            if len(path) > self.MAX_TREE_HEIGHT:
                raise MaxFolderDepthExceeded()

        return path[::-1]


@receiver(models.signals.pre_save, sender=Folder)
def _folder_pre_save(sender, instance, *args, **kwargs):
    if instance.depth is None:
        if instance.parent is None:
            instance.depth = 0
        else:
            instance.depth = instance.parent.depth + 1
            if instance.depth > Folder.MAX_TREE_HEIGHT:
                raise MaxFolderDepthExceeded()
