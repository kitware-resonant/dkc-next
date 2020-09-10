from __future__ import annotations

from typing import List

from django.core import validators
from django.db import models
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

    # TODO: What max_length?
    description = models.TextField(max_length=3000)

    # # TODO: owner on_delete policy?
    # owner = models.ForeignKey(User, on_delete=models.CASCADE)

    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True)

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
