import pytest
from pytest_factoryboy import register
from rest_framework.test import APIClient

from .factories import FileFactory, UserFactory


@pytest.fixture
def api_client():
    return APIClient()


register(FileFactory)
register(UserFactory)
