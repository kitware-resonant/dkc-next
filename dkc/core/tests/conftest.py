import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from . import factories


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def child_folder(folder, folder_factory):
    return folder_factory(parent=folder)


register(factories.FileFactory)
register(factories.FolderFactory)
register(factories.TermsFactory)
register(factories.TermsAgreementFactory, 'terms_agreement')
register(factories.TreeFactory)
register(factories.TreeWithRootFactory)
register(factories.UserFactory)
