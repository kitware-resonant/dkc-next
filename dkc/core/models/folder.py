from django.db import models
from django_extensions.db.models import TimeStampedModel
from treebeard.mp_tree import MP_Node
from treebeard.numconv import BASE62


class Folder(TimeStampedModel, MP_Node):
    node_order_by = ['name']
    name = models.CharField(max_length=255)

    # Treebeard tuning, don't change these
    path = models.CharField(max_length=250, unique=True)
    steplen = 5
    alphabet = BASE62
    # End treebeard tuning

    # TODO: What max_length?
    description = models.TextField(max_length=3000)

    # # TODO: owner on_delete policy?
    # owner = models.ForeignKey(User, on_delete=models.CASCADE)

    # # Prevent deletion of quotas while a folder references them
    # quota = models.ForeignKey(Quota, on_delete=models.PROTECT)

    # TimeStampedModel also provides "created" and "modified" fields
