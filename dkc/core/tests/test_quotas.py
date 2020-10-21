from django.conf import settings
from django.core.exceptions import ValidationError
import pytest


@pytest.mark.django_db
def test_quota_default_allowed(quota):
    assert quota.allowed == settings.DKC_DEFAULT_QUOTA


@pytest.mark.django_db
def test_quota_increment(quota):
    quota.increment(10)
    assert quota.used == 10


@pytest.mark.django_db
def test_quota_increment_failure(quota):
    with pytest.raises(ValidationError, match=r'Root folder size quota would be exceeded'):
        quota.increment(quota.allowed + 1)
    assert quota.used == 0


@pytest.mark.django_db
def test_user_creation_creates_quota(user):
    assert user.quota
    assert user.quota.used == 0


@pytest.mark.django_db
def test_root_folder_assigned_quota(folder):
    assert folder.quota
    assert folder.quota.used == 0


@pytest.mark.django_db
def test_non_root_folder_not_assigned_quota(folder, folder_factory):
    child = folder_factory(parent=folder)
    assert child.quota is None


@pytest.mark.django_db
def test_root_folder_effective_quota(folder):
    assert folder.effective_quota
    assert folder.effective_quota is folder.quota


@pytest.mark.django_db
def test_non_root_folder_effective_quota(folder, folder_factory):
    child = folder_factory(parent=folder)
    assert child.effective_quota
    assert child.effective_quota is folder.effective_quota


@pytest.mark.django_db
def test_file_creation_increments_usage(file):
    assert file.size > 0
    assert file.folder.effective_quota.used == file.size
    assert file.folder.effective_quota.used == file.size


@pytest.mark.django_db
def test_file_deletion_decrements_usage(file):
    file.delete()
    assert file.folder.effective_quota.used == 0
    assert file.folder.effective_quota.used == 0
