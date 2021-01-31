from __future__ import annotations

from typing import Type

from django.contrib.auth.models import User
from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel
from girder_utils.models import JSONObjectField

from ..permissions import Permission
from .tree import Tree

MAX_DEPTH = 30


class Folder(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['parent', 'name'])]
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['parent', 'name'], name='folder_siblings_name_unique'),
            models.UniqueConstraint(
                fields=['name'], condition=models.Q(parent=None), name='root_folder_name_unique'
            ),
            models.CheckConstraint(check=models.Q(depth__lte=MAX_DEPTH), name='folder_max_depth'),
            models.UniqueConstraint(
                fields=['tree'], condition=models.Q(parent=None), name='unique_root_folder_per_tree'
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
    # TODO: What max_length?
    description = models.TextField(max_length=3000, blank=True)
    size = models.PositiveBigIntegerField(default=0, editable=False)
    user_metadata = JSONObjectField()
    tree = models.ForeignKey(
        Tree, editable=False, on_delete=models.CASCADE, related_name='all_folders'
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_folders'
    )
    depth = models.PositiveSmallIntegerField(
        validators=[
            validators.MaxValueValidator(MAX_DEPTH, message='Maximum folder depth exceeded.'),
        ],
        editable=False,
    )
    # Prevent deletion of User if it has Folders referencing it
    creator = models.ForeignKey(User, on_delete=models.PROTECT)

    @property
    def is_root(self) -> bool:
        # Optimization when model is saved
        if self.pk:
            # Use "parent_id" instead of "parent", to avoid doing an automatic lookup
            return self.parent_id is None
        return self.parent is None

    @property
    def ancestors(self) -> models.query.RawQuerySet[Folder]:
        """
        Get the path from this folder to the root folder.

        Returns a RawQuerySet that provides the path up the tree, starting with this folder
        and going all the way to the root.
        """
        # Using LIMIT ensures this will terminate if a cycle erroneously exists
        return Folder.objects.raw(
            'WITH RECURSIVE ancestors AS ('
            'SELECT * FROM core_folder WHERE id=%s'
            ' UNION ALL'
            ' SELECT f.* FROM core_folder f JOIN ancestors a ON f.id=a.parent_id'
            ')'
            ' SELECT * FROM ancestors LIMIT %s',
            [self.pk, MAX_DEPTH + 1],
        )

    @property
    def abs_path(self) -> str:
        """
        Get a string representation of this Folder's absolute path.

        This ends in a trailing slash, indicating that the value is a Folder.
        """
        full_path = '/'.join(folder.name for folder in reversed(self.ancestors))
        return f'/{full_path}/'

    @property
    def public(self) -> bool:
        return self.tree.public

    def increment_size(self, amount: int) -> None:
        """
        Increment or decrement the Folder size.

        This Folder and all of its ancestors' sizes will be updated atomically. ``amount`` may be
        negative, but an operation resulting in a negative final size is illegal.
        """
        if amount == 0:
            return

        ancestor_pks = [folder.pk for folder in self.ancestors]
        Folder.objects.filter(pk__in=ancestor_pks).update(size=(models.F('size') + amount))

        # Update local model with the new size value
        # Also, discard potential local references to the parent model, as its size is also invalid
        self.refresh_from_db(fields=['size', 'parent'])

    def clean(self) -> None:
        if self.parent and self.parent.files.filter(name=self.name).exists():
            raise ValidationError({'name': 'A file with that name already exists here.'})
        super().clean()

    @classmethod
    def filter_by_permission(
        cls, user: User, permission: Permission, queryset: models.QuerySet['Folder']
    ) -> models.QuerySet['Folder']:
        """Filter a queryset according to a user's access.

        This method uses the tree's filter_by_permission method to create a queryset containing
        *all* trees with the appropriate permission level.  This queryset is used as a subquery
        to filter the provided queryset.
        """
        tree_query = Tree.filter_by_permission(user, permission, Tree.objects).values('pk')
        return queryset.filter(tree__in=models.Subquery(tree_query))

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Return whether the given user has a specific permission for the folder."""
        return self.tree.has_permission(user, permission)


@receiver(models.signals.post_init, sender=Folder)
def _folder_post_init(sender: Type[Folder], instance: Folder, **kwargs):
    # Only run on new object creation, as this also fires when existing models are loaded
    if instance.pk is None:
        if instance.depth is None:
            instance.depth = 0 if instance.is_root else instance.parent.depth + 1


@receiver(models.signals.post_delete, sender=Folder)
def _folder_post_delete(sender: Type[Folder], instance: Folder, **kwargs):
    if instance.is_root:
        instance.tree.delete()
