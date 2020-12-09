import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from . import factories


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def authenticated_api_client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


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
