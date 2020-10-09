from django.conf import settings
from django.core.exceptions import ValidationError
import pytest

from dkc.core.models.folder import Folder


@pytest.mark.django_db
def test_user_creation_creates_quota(user):
    assert user.quota.used == 0
    assert user.quota.allowed == settings.DKC_DEFAULT_USER_QUOTA


@pytest.mark.django_db
def test_root_folder_assigned_quota(folder):
    assert folder.quota.used == 0
    assert folder.quota.allowed is None


@pytest.mark.django_db
def test_non_root_folder_not_assigned_quota(folder, folder_factory):
    child = folder_factory(parent=folder)
    with pytest.raises(Folder.quota.RelatedObjectDoesNotExist):
        child.quota


@pytest.mark.django_db
def test_root_folder_resolve_quota_user(folder):
    assert folder.resolve_quota() == (0, settings.DKC_DEFAULT_USER_QUOTA)


@pytest.mark.django_db
def test_root_folder_resolve_quota_custom(folder):
    folder.quota.allowed = 123
    folder.quota.save()
    assert folder.resolve_quota() == (0, 123)


@pytest.mark.django_db
def test_non_root_folder_resolve_quota(folder, folder_factory):
    child = folder_factory(parent=folder)
    assert child.resolve_quota() == (0, folder.owner.quota.allowed)


@pytest.mark.django_db
def test_file_creation_increments_usage(file):
    assert file.size > 0
    assert file.folder.root_folder.owner.quota.used == file.size
    assert file.folder.root_folder.quota.used == file.size


@pytest.mark.django_db
def test_file_deletion_decrements_usage(file):
    file.delete()
    assert file.folder.root_folder.owner.quota.used == 0
    assert file.folder.root_folder.quota.used == 0


@pytest.mark.django_db
def test_user_quota_increment_rollback(folder):
    used, allowed = folder.resolve_quota()
    with pytest.raises(ValidationError, match=r'User size quota would be exceeded'):
        folder.increment_quota(allowed + 1)
    folder.owner.quota.refresh_from_db()
    folder.quota.refresh_from_db()
    assert folder.owner.quota.used == used
    assert folder.quota.used == used


@pytest.mark.django_db
def test_folder_quota_increment_rollback(folder):
    folder.quota.allowed = 1
    folder.quota.save()
    with pytest.raises(ValidationError, match=r'Root folder size quota would be exceeded'):
        folder.increment_quota(2)
    folder.owner.quota.refresh_from_db()
    folder.quota.refresh_from_db()
    assert folder.owner.quota.used == 0
    assert folder.quota.used == 0


@pytest.mark.django_db
def test_folder_quota_doesnt_increment_owner_used_amount(folder):
    folder.quota.allowed = 2
    folder.quota.save()
    folder.increment_quota(1)
    assert folder.owner.quota.used == 0
    assert folder.quota.used == 1


@pytest.mark.django_db
def test_folder_ownership_transfer(file):
    root = file.folder.root_folder
    assert root.owner.quota.used > 0
    root.quota.allowed = 1 << 30
    root.quota.save()
    root.owner.quota.refresh_from_db()
    assert root.owner.quota.used == 0
