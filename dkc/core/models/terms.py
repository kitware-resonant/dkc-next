import hashlib
from typing import Type

from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django_extensions.db.models import TimeStampedModel

from .tree import Tree


class Terms(TimeStampedModel, models.Model):
    class Meta:
        verbose_name = 'terms of use'
        verbose_name_plural = 'terms of use'

    tree = models.OneToOneField(
        Tree,
        primary_key=True,
        on_delete=models.CASCADE,
        related_name='terms',
    )
    text = models.TextField(blank=False)
    checksum = models.CharField(max_length=32, editable=False, blank=False)

    def clean(self) -> None:
        self.text = self.text.strip()


@receiver(pre_save, sender=Terms)
def _compute_checksum(sender: Type[Terms], instance: Terms, **kwargs):
    # MD5 is sufficient since this isn't a cryptographic use case
    instance.checksum = hashlib.md5(instance.text.encode('utf8')).hexdigest()
