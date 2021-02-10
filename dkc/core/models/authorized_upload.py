from django.contrib.auth.models import User
from django.db import models
from django_extensions.db.models import CreationDateTimeField

from .folder import Folder


class AuthorizedUpload(models.Model):
    folder = models.ForeignKey(
        Folder, on_delete=models.CASCADE, related_name='authorized_uploads', editable=False
    )
    creator = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='authorized_uploads', editable=False
    )
    created = CreationDateTimeField()
    expires = models.DateTimeField(editable=False)
