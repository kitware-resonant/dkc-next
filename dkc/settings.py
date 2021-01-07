from __future__ import annotations

from pathlib import Path
import re

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)
from django.core.validators import MaxLengthValidator, RegexValidator

username_validators = [
    RegexValidator(
        r'^[a-z\d](?:[a-z\d]|-(?=[a-z\d]))*$',
        'Username may only contain alphanumeric characters and hyphens. It cannot begin or '
        'end with a hyphen, and may not have consecutive hyphens.',
        flags=re.IGNORECASE,
    ),
    MaxLengthValidator(50, 'Username may not be more than 50 characters.'),
]


class DkcMixin(ConfigMixin):
    WSGI_APPLICATION = 'dkc.wsgi.application'
    ROOT_URLCONF = 'dkc.urls'

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    # Enable usernames distinct from email addresses
    ACCOUNT_ADAPTER = 'allauth.account.adapter.DefaultAccountAdapter'
    ACCOUNT_USERNAME_VALIDATORS = 'dkc.settings.username_validators'
    ACCOUNT_USERNAME_REQUIRED = True
    ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
    ACCOUNT_AUTHENTICATION_METHOD = 'username_email'

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        configuration.INSTALLED_APPS += [
            'dkc.core.apps.CoreConfig',
            's3_file_field',
        ]


class DevelopmentConfiguration(DkcMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DkcMixin, TestingBaseConfiguration):
    pass


class ProductionConfiguration(DkcMixin, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DkcMixin, HerokuProductionBaseConfiguration):
    pass
