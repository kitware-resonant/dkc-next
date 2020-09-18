from __future__ import annotations

from pathlib import Path

from django_girders.configuration import (
    ComposedConfiguration,
    ConfigMixin,
    DevelopmentBaseConfiguration,
    HerokuProductionBaseConfiguration,
    ProductionBaseConfiguration,
    TestingBaseConfiguration,
)


class DkcConfig(ConfigMixin):
    WSGI_APPLICATION = 'dkc.wsgi.application'
    ROOT_URLCONF = 'dkc.urls'

    BASE_DIR = str(Path(__file__).absolute().parent.parent)

    REST_FRAMEWORK = {
        'DEFAULT_PAGINATION_CLASS': 'dkc.core.rest.pagination.BoundedLimitOffsetPagination',
    }

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        configuration.INSTALLED_APPS += ['dkc.core.apps.CoreConfig']


class DevelopmentConfiguration(DkcConfig, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DkcConfig, TestingBaseConfiguration):
    pass


class ProductionConfiguration(DkcConfig, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DkcConfig, HerokuProductionBaseConfiguration):
    pass
    DEBUG = True
