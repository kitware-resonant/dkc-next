from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django_extensions.db.models import TimeStampedModel

from .terms import Terms


class TermsAgreement(TimeStampedModel, models.Model):
    class Meta:
        indexes = [models.Index(fields=['terms', 'user'])]
        constraints = [
            models.constraints.UniqueConstraint(
                fields=['terms', 'user'], name='terms_agreement_unique'
            ),
        ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='terms_agreements')
    terms = models.ForeignKey(Terms, on_delete=models.CASCADE, related_name='agreements')
    checksum = models.CharField(max_length=32)

    def clean(self) -> None:
        if self.checksum != self.terms.checksum:
            raise ValidationError({'checksum': 'The checksum does not match the latest terms.'})
