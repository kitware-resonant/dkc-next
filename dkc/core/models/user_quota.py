from typing import Type

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


def _default_user_quota() -> int:
    return settings.DKC_DEFAULT_USER_QUOTA


class UserQuota(models.Model):
    user = models.OneToOneField(
        User, primary_key=True, on_delete=models.CASCADE, related_name='quota'
    )
    used = models.PositiveBigIntegerField(default=0)
    allowed = models.PositiveBigIntegerField(default=_default_user_quota)

    def clean(self) -> None:
        if self.used > self.allowed:
            raise ValidationError({'allowed': 'Must not be less than used amount.'})


@receiver(post_save, sender=User)
def _create_user_quota(sender: Type[User], instance: User, created: bool, **kwargs):
    if created:
        UserQuota.objects.create(user=instance)
