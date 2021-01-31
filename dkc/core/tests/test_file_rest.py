import pytest


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
