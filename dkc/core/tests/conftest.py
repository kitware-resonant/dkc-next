import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from . import factories


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def admin_api_client(user_factory) -> APIClient:
    user = user_factory(is_superuser=True)
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def child_folder(folder, folder_factory):
    return folder_factory(parent=folder)


@pytest.fixture
def public_folder(folder_factory):
    return folder_factory(tree__public=True)


register(factories.FileFactory)
register(factories.FolderFactory)
register(factories.TermsFactory)
register(factories.TermsAgreementFactory, 'terms_agreement')
register(factories.TreeFactory)
register(factories.TreeWithRootFactory)
register(factories.UserFactory)
