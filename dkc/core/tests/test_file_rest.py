from django.conf import settings
import pytest

from dkc.core.models import File
from dkc.core.tasks import file_compute_sha512


@pytest.mark.django_db
def test_file_rest_retrieve(admin_api_client, file):
    resp = admin_api_client.get(f'/api/v2/files/{file.id}')
    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    assert resp.data['name'] == file.name


@pytest.mark.django_db
def test_file_list_default_ordering(admin_api_client, folder, file_factory):
    for name in ('B', 'C', 'A'):
        file_factory(name=name, folder=folder)
    resp = admin_api_client.get('/api/v2/files', data={'folder': folder.id})
    assert resp.status_code == 200
    assert [f['name'] for f in resp.data['results']] == ['A', 'B', 'C']


@pytest.mark.django_db
def test_file_rest_create_process(admin_api_client, folder):
    """Test initialization of a file, without its blob."""
    resp = admin_api_client.post(
        '/api/v2/files',
        data={
            'folder': folder.id,
            'name': 'test.txt',
            'size': 42,
        },
    )
    assert resp.status_code == 201
    assert resp.data['size'] == 42
    folder.refresh_from_db()
    assert folder.size == 42
    saved_file = File.objects.get(id=resp.data['id'])
    assert bool(saved_file.blob) is False


@pytest.mark.django_db
def test_file_rest_download_pending_file(admin_api_client, pending_file):
    """Test downloading a file prior to its blob being set does something sane."""
    resp = admin_api_client.get(f'/api/v2/files/{pending_file.id}/download')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_file_rest_cannot_update_size(admin_api_client, file):
    resp = admin_api_client.patch(f'/api/v2/files/{file.id}', data={'size': file.size + 1})
    assert resp.data['size'] == file.size


@pytest.mark.django_db
def test_file_rest_update(admin_api_client, file):
    resp = admin_api_client.patch(f'/api/v2/files/{file.id}', data={'description': 'hello'})
    assert resp.status_code == 200


@pytest.mark.django_db
def test_file_rest_set_blob(admin_api_client, pending_file, s3ff_field_value, mocker):
    mocker.patch.object(file_compute_sha512, 'delay')
    resp = admin_api_client.patch(
        f'/api/v2/files/{pending_file.id}', data={'blob': s3ff_field_value}
    )
    assert resp.status_code == 200
    assert resp.data['size'] == pending_file.size
    pending_file.refresh_from_db()
    assert pending_file.blob

    file_compute_sha512.delay.assert_called_once_with(pending_file.id)


@pytest.mark.django_db
def test_file_rest_set_blob_only_once(admin_api_client, file, s3ff_field_value):
    resp = admin_api_client.patch(f'/api/v2/files/{file.id}', data={'blob': s3ff_field_value})
    assert resp.status_code == 400
    assert resp.data['blob'] == ["A file's blob may only be set once."]


@pytest.mark.django_db
def test_quota_enforcement(admin_api_client, folder):
    resp = admin_api_client.post(
        '/api/v2/files',
        data={
            'name': 'name.txt',
            'folder': folder.id,
            'size': settings.DKC_DEFAULT_QUOTA + 1,
        },
    )
    assert resp.status_code == 400
    assert resp.data == {'size': ['This file would exceed the size quota for this folder.']}


@pytest.mark.django_db
def test_hash_download_no_access(api_client, hashed_file):
    resp = api_client.get('/api/v2/files/hash_download', data={'sha512': hashed_file.sha512})
    assert resp.status_code == 404


@pytest.mark.django_db
def test_hash_download_public(api_client, hashed_file):
    hashed_file.folder.tree.public = True
    hashed_file.folder.tree.save()
    resp = api_client.get('/api/v2/files/hash_download', data={'sha512': hashed_file.sha512})
    assert resp.status_code == 302


@pytest.mark.django_db
def test_hash_download_case_insensitive(admin_api_client, hashed_file):
    sha512 = hashed_file.sha512.upper()
    resp = admin_api_client.get('/api/v2/files/hash_download', data={'sha512': sha512})
    assert resp.status_code == 302
