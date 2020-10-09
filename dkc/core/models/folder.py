from __future__ import annotations

from typing import List, Tuple

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models, transaction
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

    description = models.TextField(max_length=3000, blank=True)
    user_metadata = UserMetadataField()

    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_folders'
    )
    root_folder = models.ForeignKey(
        'self', on_delete=models.DO_NOTHING, blank=True, null=True, related_name='+'
    )

    def resolve_quota(self) -> Tuple[int, int]:
        """
        Resolve the quota for a given folder.

        Returns the value as a tuple of the form (bytes_used, bytes_allowed).
        """
        folder_quota = self.root_folder.quota
        if folder_quota.allowed is None:
            # This indicates that this folder's quota is its owning user's quota
            owner_quota = self.root_folder.owner.quota
            return owner_quota.used, owner_quota.allowed
        return folder_quota.used, folder_quota.allowed

    @transaction.atomic
    def increment_quota(self, amount: int) -> None:
        """
        Increments the quota(s) associated with this folder.

        This function increments (or decrements, if ``amount`` is negative) the usage
        values associated with this folder. The used amount tracked on the folder itself is
        incremented. Additionally, if this folder has a user-assigned quota, that quota
        usage value is also incremented. If either of these increments would exceed the max
        allotment for this folder, a ``ValidationError`` is raised and the transaction
        is rolled back.
        """
        if amount == 0:
            return

        folder_quota = self.root_folder.quota
        folder_quota.used = models.F('used') + amount
        folder_quota.save(update_fields=['used'])

        if folder_quota.allowed is None:
            user_quota = self.root_folder.owner.quota
            user_quota.used = models.F('used') + amount
            user_quota.save(update_fields=['used'])
            if amount > 0:
                user_quota.refresh_from_db()
                if user_quota.used > user_quota.allowed:
                    raise ValidationError(
                        'User size quota would be exceeded: '
                        f'{user_quota.used}B > {user_quota.allowed}B.'
                    )
        elif amount > 0:
            folder_quota.refresh_from_db()
            if folder_quota.used > folder_quota.allowed:
                raise ValidationError(
                    'Root folder size quota would be exceeded: '
                    f'{folder_quota.used}B > {folder_quota.allowed}B.'
                )

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
