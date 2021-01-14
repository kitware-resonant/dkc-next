from copy import deepcopy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers


class FullCleanModelSerializer(serializers.ModelSerializer):
    def validate(self, data):
        if self.partial:  # partial update
            instance = deepcopy(self.instance)
            for k, v in data.items():
                setattr(instance, k, v)
            try:
                instance.full_clean()
            except DjangoValidationError as exc:
                raise serializers.ValidationError(serializers.as_serializer_error(exc))
        else:  # create or full update
            try:
                self.Meta.model(**data).full_clean()
            except DjangoValidationError as exc:
                raise serializers.ValidationError(serializers.as_serializer_error(exc))
        return data
