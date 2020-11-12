from __future__ import annotations

from pathlib import Path

from composed_configuration import (
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

    BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

    @staticmethod
    def before_binding(configuration: ComposedConfiguration) -> None:
        configuration.INSTALLED_APPS += ['dkc.core.apps.CoreConfig']
        configuration.REST_FRAMEWORK.update(
            {
                'DEFAULT_PAGINATION_CLASS': 'dkc.core.rest.pagination.BoundedLimitOffsetPagination',
            }
        )


class DevelopmentConfiguration(DkcConfig, DevelopmentBaseConfiguration):
    pass


class TestingConfiguration(DkcConfig, TestingBaseConfiguration):
    pass


class ProductionConfiguration(DkcConfig, ProductionBaseConfiguration):
    pass


class HerokuProductionConfiguration(DkcConfig, HerokuProductionBaseConfiguration):
    pass
