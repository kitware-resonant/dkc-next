from __future__ import annotations

from pathlib import Path
import re

from composed_configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HttpsMixin,
    MinioStorageMixin,
    SentryMixin,
    SmtpEmailMixin,
    TestingBaseConfiguration,
)
from composed_configuration._configuration import _BaseConfiguration, _HerokuMixin
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

    DKC_DEFAULT_QUOTA = 3 << 30  # 3 GB

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        # Install local apps first, to ensure any overridden resources are found first
        configuration.INSTALLED_APPS = [
            'dkc.core.apps.CoreConfig',
        ] + configuration.INSTALLED_APPS

        # Install additional apps
        configuration.INSTALLED_APPS += [
            's3_file_field',
            'guardian',
        ]

        configuration.AUTHENTICATION_BACKENDS += [
            'guardian.backends.ObjectPermissionBackend',
        ]


class DevelopmentConfiguration(DkcMixin, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DkcMixin, TestingBaseConfiguration):
    pass


# Don't define a generic ProductionConfiguration, since this only targets Heroku deployment

# Similar to composed_configuration.HerokuProductionConfiguration, with MinioStorageMixin instead
class HerokuProductionConfiguration(
    DkcMixin,
    _HerokuMixin,
    SentryMixin,
    SmtpEmailMixin,
    MinioStorageMixin,
    HttpsMixin,
    _BaseConfiguration,
):
    pass
