from django.conf import settings
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
