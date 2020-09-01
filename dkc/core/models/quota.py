from typing import Type

from django_girders.models import SelectRelatedManager

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Quota(models.Model):
    allocation = models.BigIntegerField(default=0)
    user = models.OneToOneField(User, null=True, on_delete=models.CASCADE)
    # root_set

    # The user is needed to stringify, so join it when directly querying for a quota
    objects = SelectRelatedManager('user')

    def __str__(self):
        return f'Quota for <{self.user}>; {self.allocation} bytes'


@receiver(post_save, sender=User)
def create_user_quota(sender: Type[User], instance: User, created: bool, **kwargs):
    if created:
        quota = Quota(user=instance)
        quota.save()
