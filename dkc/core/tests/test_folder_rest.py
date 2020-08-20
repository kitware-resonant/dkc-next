import pytest

from dkc.core.models import Folder


@pytest.mark.django_db
def test_folder_rest_list(api_client, folder):
    Folder.add_root(instance=folder)  # equivalent to .save()

    resp = api_client.get('/api/v1/folders/')

    assert resp.status_code == 200
    assert resp.data[0]['name'] == folder.name


@pytest.mark.skip
@pytest.mark.django_db
def test_folder_rest_create(api_client):
    resp = api_client.post('/api/v1/folders/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_folder_rest_retrieve(api_client, folder):
    Folder.add_root(instance=folder)  # equivalent to .save()

    resp = api_client.get(f'/api/v1/folders/{folder.id}/')

    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    print(resp.data)
    assert resp.data['name'] == folder.name


@pytest.mark.skip
@pytest.mark.django_db
def test_folder_rest_update(api_client, folder):
    resp = api_client.put(f'/api/v1/folders/{folder.id}/')
    assert resp.status_code == 200


@pytest.mark.django_db
def test_folder_rest_destroy(api_client, folder):
    Folder.add_root(instance=folder)  # equivalent to .save()

    resp = api_client.delete(f'/api/v1/folders/{folder.id}/')

    assert resp.status_code == 204
    with pytest.raises(Folder.DoesNotExist):
        Folder.objects.get(id=folder.id)
