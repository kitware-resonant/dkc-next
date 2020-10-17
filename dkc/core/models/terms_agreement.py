from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.fields import ModificationDateTimeField

from .terms import Terms


class TermsAgreement(models.Model):
    class Meta:
        indexes = [models.Index(fields=['terms', 'user'])]
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['terms', 'user'], name='terms_agreement_unique'
            ),
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='+')
    terms = models.ForeignKey(Terms, on_delete=models.CASCADE, related_name='+')
    checksum = models.CharField(max_length=32)
    when = ModificationDateTimeField()

    def clean(self) -> None:
        if self.checksum != self.terms.checksum:
            raise ValidationError({'checksum': 'The checksum does not match the latest terms.'})
