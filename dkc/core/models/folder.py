from __future__ import annotations

from typing import Type

from django.core import validators
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from dkc.core.models.metadata import UserMetadataField

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

    depth = models.PositiveSmallIntegerField(
        validators=[
            validators.MaxValueValidator(MAX_DEPTH, message='Maximum folder depth exceeded.'),
        ],
        editable=False,
    )

    size = models.PositiveBigIntegerField(default=0, editable=False)

    # TODO: What max_length?
    description = models.TextField(max_length=3000, blank=True)
    user_metadata = UserMetadataField()

    # # TODO: owner on_delete policy?
    # owner = models.ForeignKey(User, on_delete=models.CASCADE)

    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, blank=True, null=True, related_name='child_folders'
    )

    tree = models.ForeignKey(
        Tree, editable=False, on_delete=models.CASCADE, related_name='all_folders'
    )

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
            raise ValidationError(
                {'name': f'There is already a file here with the name "{self.name}".'}
            )
        super().clean()

    @classmethod
    @transaction.atomic
    def create_and_attach_to_tree(cls, parent: Folder = None, **kwargs) -> Folder:
        tree = parent.tree if parent else Tree.objects.create()
        return Folder.objects.create(tree=tree, parent=parent, **kwargs)


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
