from django.core.exceptions import ValidationError
from django.db.models import JSONField


def validate_metadata(val) -> None:
    if not isinstance(val, dict):
        raise ValidationError('Must be a JSON Object.')
    # TODO enforce max size of metadata document here?


class UserMetadataField(JSONField):
    empty_values = [{}]

    def __init__(self, *args, **kwargs):
        kwargs['default'] = dict
        kwargs['blank'] = True
        super().__init__(*args, **kwargs)
        self.validators.append(validate_metadata)
