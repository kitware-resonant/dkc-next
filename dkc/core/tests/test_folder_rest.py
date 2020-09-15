import pytest

from dkc.core.models import Folder


@pytest.mark.django_db
def test_folder_rest_list_children(api_client, folder, folder_factory):
    child = folder_factory(parent=folder)
    resp = api_client.get(f'/api/v2/folders?parent={folder.id}')

    assert resp.status_code == 200
    assert resp.data['count'] == 1
    child_resp = resp.data['results'][0]
    assert child_resp['id'] == child.id
    assert child_resp['parent'] == folder.id


@pytest.mark.django_db
def test_folder_rest_path(api_client, folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    resp = api_client.get(f'/api/v2/folders/{grandchild.id}/path')
    assert resp.status_code == 200
    assert [f['name'] for f in resp.data] == [folder.name, child.name, grandchild.name]


@pytest.mark.skip
@pytest.mark.django_db
def test_folder_rest_create(api_client):
    resp = api_client.post('/api/v2/folders')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_folder_rest_retrieve(api_client, folder):
    resp = api_client.get(f'/api/v2/folders/{folder.id}')

    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    assert resp.data['name'] == folder.name


@pytest.mark.skip
@pytest.mark.django_db
def test_folder_rest_update(api_client, folder):
    resp = api_client.put(f'/api/v2/folders/{folder.id}')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_folder_rest_destroy(api_client, folder):
    resp = api_client.delete(f'/api/v2/folders/{folder.id}')
    assert resp.status_code == 204
    with pytest.raises(Folder.DoesNotExist):
        Folder.objects.get(id=folder.id)


@pytest.mark.django_db
def test_folder_list_roots_parent_required(api_client):
    resp = api_client.get('/api/v2/folders')
    assert resp.status_code == 400
    assert resp.data == {'parent': ['This field is required.']}


@pytest.mark.django_db
def test_folder_list_roots_invalid_parent(api_client):
    resp = api_client.get('/api/v2/folders', data={'parent': 'x'})
    assert resp.status_code == 400
    assert resp.data == {'parent': ['May only be an integer or "null".']}


@pytest.mark.django_db
def test_folder_list_roots(api_client, folder, folder_factory):
    folder_factory(parent=folder)  # Make child folder to test that we only get roots
    resp = api_client.get('/api/v2/folders', data={'parent': 'null'})
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['name'] == folder.name
