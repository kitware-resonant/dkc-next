from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import pytest


@pytest.mark.django_db
def test_file_abs_path(folder, folder_factory, file_factory):
    child = folder_factory(parent=folder)
    grandchild = file_factory(folder=child)
    assert grandchild.abs_path == f'/{folder.name}/{child.name}/{grandchild.name}'


def test_file_checksum(file_factory):
    # Use "build" strategy, so database is not required
    file = file_factory.build()
    file.compute_sha512()
    assert len(file.sha512) == 128


@pytest.mark.django_db
def test_file_sibling_names_unique(file, file_factory):
    sibling = file_factory.build(folder=file.folder, name=file.name)
    # Make sure foreign key references exist in database first
    sibling.creator.save()
    with pytest.raises(IntegrityError, match=r'Key .* already exists\.'):
        sibling.save()


@pytest.mark.django_db
def test_file_sibling_names_unique_folders(folder, folder_factory, file_factory):
    folder_factory(parent=folder, name='unique')
    sibling_file = file_factory.build(folder=folder, name='unique')
    with pytest.raises(ValidationError, match='A folder with that name already exists here.'):
        sibling_file.full_clean()


@pytest.mark.django_db
def test_file_size_computed(file):
    assert file.size == file.blob.size
