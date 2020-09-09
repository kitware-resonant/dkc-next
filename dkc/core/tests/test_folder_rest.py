import pytest

from dkc.core.models import Folder


@pytest.mark.django_db
def test_folder_rest_list(api_client, folder):
    resp = api_client.get('/api/v1/folders/')

    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['name'] == folder.name


@pytest.mark.django_db
def test_folder_rest_list_children(api_client, folder, folder_factory):
    child = folder_factory(parent=folder)
    resp = api_client.get(f'/api/v1/folders/?parent_id={folder.id}')

    assert resp.status_code == 200
    assert resp.data['count'] == 1
    child_resp = resp.data['results'][0]
    assert child_resp['id'] == child.id
    assert child_resp['parent'] == folder.id


@pytest.mark.django_db
def test_folder_rest_path(api_client, folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    resp = api_client.get(f'/api/v1/folders/{grandchild.id}/path/')
    assert resp.status_code == 200
    assert [f['name'] for f in resp.data] == [folder.name, child.name, grandchild.name]


@pytest.mark.skip
@pytest.mark.django_db
def test_folder_rest_create(api_client):
    resp = api_client.post('/api/v1/folders/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_folder_rest_retrieve(api_client, folder):
    resp = api_client.get(f'/api/v1/folders/{folder.id}/')

    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    assert resp.data['name'] == folder.name


@pytest.mark.skip
@pytest.mark.django_db
def test_folder_rest_update(api_client, folder):
    resp = api_client.put(f'/api/v1/folders/{folder.id}/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_folder_rest_destroy(api_client, folder):
    resp = api_client.delete(f'/api/v1/folders/{folder.id}/')

    assert resp.status_code == 204
    with pytest.raises(Folder.DoesNotExist):
        Folder.objects.get(id=folder.id)
