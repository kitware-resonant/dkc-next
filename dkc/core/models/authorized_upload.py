from django.contrib.auth.models import User
from django.core import signing
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

    @property
    def signature(self):
        return signing.dumps({'scope': 'authorized_upload', 'id': self.id})

    def verify_signature(self, signature: str) -> None:
        """Verify the signature associated with this instance.

        Raises `BadSignature` if message tampering occurred, or if the scope
        of the signed message does not match this feature, or if the signed ID does
        not match the ID of this instance.
        """
        signed_obj = signing.loads(signature)
        if signed_obj.get('scope') != 'authorized_upload':
            raise signing.BadSignature('Invalid signed scope.')
        if signed_obj.get('id') != self.id:
            raise signing.BadSignature('Invalid signed ID.')
