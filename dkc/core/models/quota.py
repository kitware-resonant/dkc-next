from typing import Type

from django.conf import settings
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models.signals import post_save
from django.dispatch import receiver


def _default_user_quota() -> int:
    return settings.DKC_DEFAULT_QUOTA


class Quota(models.Model):
    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(used__lte=models.F('allowed')),
                name='used_lte_allowed',
            )
        ]

    used = models.PositiveBigIntegerField(default=0)
    allowed = models.PositiveBigIntegerField(default=_default_user_quota)

    # Nullable OneToOneField ensures that only one Quota per User exists
    user = models.OneToOneField(
        User, null=True, blank=True, on_delete=models.CASCADE, related_name='quota'
    )

    @transaction.atomic
    def increment(self, amount: int) -> None:
        """
        Increment or decrement the quota.

        This function increments (or decrements, if ``amount`` is negative) the usage
        values associated with this quota. If this increment would exceed the max
        allotment for this quota, a ``ValidationError`` is raised and the transaction
        is rolled back.
        """
        if amount == 0:
            return

        try:
            # Use an .update query instead of a .save, to avoid assigning an F-expression on the
            # local instance, which might need to be rolled back on a failure
            Quota.objects.filter(pk=self.pk).update(used=(models.F('used') + amount))
        except IntegrityError as e:
            if '"used_lte_allowed"' in str(e):
                raise ValidationError(
                    'Root folder size quota would be exceeded: ' f'{self.used}B > {self.allowed}B.'
                )
            else:
                raise

        # Update with the new value
        self.refresh_from_db(fields=['used'])


@receiver(post_save, sender=User)
def _create_user_quota(sender: Type[User], instance: User, created: bool, **kwargs):
    if created:
        Quota.objects.create(user=instance)
