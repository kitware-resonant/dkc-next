from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import pytest


@pytest.mark.django_db
def test_quota_default_allowed(tree):
    assert tree.quota.allowed == settings.DKC_DEFAULT_QUOTA


@pytest.mark.django_db
def test_quota_increment(tree):
    tree.quota.increment(10)
    assert tree.quota.used == 10


@pytest.mark.django_db
def test_quota_increment_failure(tree):
    with pytest.raises(ValidationError, match=r'Tree size quota would be exceeded'):
        tree.quota.increment(tree.quota.allowed + 1)
    assert tree.quota.used == 0


@pytest.mark.django_db
def test_quota_increment_negative(tree):
    with pytest.raises(IntegrityError, match=r'quota_used'):
        tree.quota.increment(-10)
    assert tree.quota.used == 0


@pytest.mark.django_db
def test_user_creation_creates_quota(user):
    assert user.quota
    assert user.quota.used == 0


@pytest.mark.django_db
def test_file_creation_increments_usage(file):
    assert file.size > 0
    assert file.folder.tree.quota.used == file.size
    assert file.folder.tree.quota.used == file.size


@pytest.mark.django_db
def test_file_deletion_decrements_usage(file):
    file.delete()
    assert file.folder.tree.quota.used == 0
    assert file.folder.tree.quota.used == 0
