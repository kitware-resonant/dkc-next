import pytest

from dkc.core.models import File


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
def test_file_rest_set_blob(admin_api_client, pending_file, s3ff_field_value):
    resp = admin_api_client.patch(
        f'/api/v2/files/{pending_file.id}', data={'blob': s3ff_field_value}
    )
    assert resp.status_code == 200
    assert resp.data['size'] == pending_file.size
    pending_file.refresh_from_db()
    assert pending_file.blob
