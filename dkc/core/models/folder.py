from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import TimeStampedModel

from dkc.core.models import Quota


class Folder(TimeStampedModel, models.Model):
    name = models.CharField(max_length=255)
    # TODO: What max_length?
    description = models.TextField(max_length=3000)

    # TODO: owner on_delete policy?
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    # Prevent deletion of quotas while a folder references them
    quota = models.ForeignKey(Quota, on_delete=models.PROTECT)

    # TimeStampedModel also provides "created" and "modified" fields
