from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import pytest


def test_file_checksum(file_factory):
    # Use "build" strategy, so database is not required
    file = file_factory.build()
    file.compute_sha512()
    assert len(file.sha512) == 128


@pytest.mark.django_db
def test_file_rest_retrieve(admin_api_client, file):
    resp = admin_api_client.get(f'/api/v2/files/{file.id}')
    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    assert resp.data['name'] == file.name


@pytest.mark.django_db
def test_file_sibling_names_unique(file, file_factory):
    sibling = file_factory.build(folder=file.folder, name=file.name, creator=None)
    with pytest.raises(IntegrityError, match=r'Key .* already exists\.'):
        sibling.save()


@pytest.mark.django_db
def test_file_sibling_names_unique_folders(folder, folder_factory, file_factory):
    folder_factory(parent=folder, name='unique')
    sibling_file = file_factory.build(folder=folder, name='unique')
    with pytest.raises(
        ValidationError, match=r'There is already a folder here with the name "unique"\.'
    ):
        sibling_file.full_clean()


@pytest.mark.django_db
def test_file_size_computed(file):
    assert file.size == file.blob.size


@pytest.mark.django_db
def test_file_list_default_ordering(admin_api_client, folder, file_factory):
    for name in ('B', 'C', 'A'):
        file_factory(name=name, folder=folder)
    resp = admin_api_client.get('/api/v2/files', data={'folder': folder.id})
    assert resp.status_code == 200
    assert [f['name'] for f in resp.data['results']] == ['A', 'B', 'C']
