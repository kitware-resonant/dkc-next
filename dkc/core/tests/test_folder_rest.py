from django.conf import settings
import pytest

from dkc.core.models import Folder
from dkc.core.tasks import delete_folder


@pytest.mark.django_db
def test_folder_rest_list_children(admin_api_client, folder, folder_factory):
    child = folder_factory(parent=folder)
    resp = admin_api_client.get(f'/api/v2/folders?parent={folder.id}')

    assert resp.status_code == 200
    assert resp.data['count'] == 1
    child_resp = resp.data['results'][0]
    assert child_resp['id'] == child.id
    assert child_resp['parent'] == folder.id


@pytest.mark.django_db
def test_folder_rest_path(admin_api_client, folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    resp = admin_api_client.get(f'/api/v2/folders/{grandchild.id}/path')
    assert resp.status_code == 200
    assert [f['name'] for f in resp.data] == [folder.name, child.name, grandchild.name]


@pytest.mark.django_db
@pytest.mark.parametrize(
    'name', ['', 'ten_chars_' * 30, 'foo/bar'], ids=['empty', 'too_long', 'forward_slash']
)
def test_folder_rest_create_invalid_name(admin_api_client, name):
    resp = admin_api_client.post('/api/v2/folders', data={'name': name})
    assert resp.status_code == 400
    assert 'name' in resp.data


@pytest.mark.django_db
@pytest.mark.parametrize('description', ['ten_chars_' * 301], ids=['too_long'])
def test_folder_rest_create_invalid_description(admin_api_client, description):
    resp = admin_api_client.post(
        '/api/v2/folders', data={'name': 'test folder', 'description': description}
    )
    assert resp.status_code == 400
    assert 'description' in resp.data


@pytest.mark.django_db
@pytest.mark.parametrize('parent', ['foo', -1, 9000], ids=['non_int', 'negative', 'nonexistent'])
def test_folder_rest_create_invalid_parent(admin_api_client, parent):
    resp = admin_api_client.post('/api/v2/folders', data={'name': 'test folder', 'parent': parent})
    assert resp.status_code == 400
    assert 'parent' in resp.data


@pytest.mark.django_db
def test_folder_rest_create_invalid_duplicate_root(admin_api_client, folder):
    resp = admin_api_client.post('/api/v2/folders', data={'name': folder.name, 'parent': None})
    assert resp.status_code == 400
    assert 'name' in resp.data


@pytest.mark.django_db
def test_folder_rest_create_name_validation_local_only(admin_api_client, folder):
    # Ensure a sub-folder can have the same name as a root folder
    resp = admin_api_client.post('/api/v2/folders', data={'parent': folder.id, 'name': folder.name})
    assert resp.status_code == 201


@pytest.mark.django_db
def test_folder_rest_create_invalid_duplicate_sibling_folder(admin_api_client, child_folder):
    resp = admin_api_client.post(
        '/api/v2/folders', data={'name': child_folder.name, 'parent': child_folder.parent.id}
    )
    assert resp.status_code == 400
    assert 'name' in resp.data


@pytest.mark.django_db
def test_folder_rest_create_invalid_duplicate_sibling_file(admin_api_client, folder, file_factory):
    child_file = file_factory(folder=folder)
    resp = admin_api_client.post(
        '/api/v2/folders', data={'name': child_file.name, 'parent': folder.id}
    )
    assert resp.status_code == 400
    assert 'name' in resp.data


@pytest.mark.django_db
def test_folder_rest_create_invalid_duplicate_sibling_file_update(
    admin_api_client, folder, file_factory, folder_factory
):
    # Since this is implemented with an explicitly separate code path, it deserves its own test
    child_file = file_factory(folder=folder)
    child_folder = folder_factory(parent=folder)
    resp = admin_api_client.patch(
        f'/api/v2/folders/{child_folder.id}', data={'name': child_file.name}
    )
    assert resp.status_code == 400
    assert 'name' in resp.data


@pytest.mark.django_db
def test_folder_rest_create_root(admin_api_client):
    resp = admin_api_client.post('/api/v2/folders', data={'name': 'test folder', 'parent': None})
    assert resp.status_code == 201
    assert Folder.objects.count() == 1


@pytest.mark.django_db
def test_folder_rest_create_child(admin_api_client, folder):
    resp = admin_api_client.post(
        '/api/v2/folders', data={'name': 'test folder', 'parent': folder.pk}
    )
    assert resp.status_code == 201
    assert Folder.objects.count() == 2


@pytest.mark.django_db
def test_folder_rest_retrieve(admin_api_client, folder):
    resp = admin_api_client.get(f'/api/v2/folders/{folder.id}')

    assert resp.status_code == 200
    # Inspect .data to avoid parsing the response content
    assert resp.data['name'] == folder.name


@pytest.mark.django_db
def test_folder_rest_update(admin_api_client, folder):
    resp = admin_api_client.patch(
        f'/api/v2/folders/{folder.id}', data={'name': 'New name', 'description': 'New description'}
    )
    assert resp.status_code == 200
    folder.refresh_from_db()
    assert folder.name == 'New name'
    assert folder.description == 'New description'


@pytest.mark.django_db
def test_folder_rest_update_parent_disallowed(admin_api_client, folder, folder_factory):
    other_root = folder_factory()
    child = folder_factory(parent=folder)
    resp = admin_api_client.patch(f'/api/v2/folders/{child.id}', data={'parent': other_root.id})
    assert resp.status_code == 200
    child.refresh_from_db()
    assert child.parent_id == folder.id


@pytest.mark.django_db
def test_folder_rest_destroy_async(admin_api_client, folder, mocker):
    mocker.patch.object(delete_folder, 'delay')
    resp = admin_api_client.delete(f'/api/v2/folders/{folder.id}')
    assert resp.status_code == 202
    delete_folder.delay.assert_called_once_with(folder.id)


@pytest.mark.django_db
def test_folder_list_roots_parent_required(admin_api_client):
    resp = admin_api_client.get('/api/v2/folders')
    assert resp.status_code == 400
    assert resp.data == {'parent': ['This field is required.']}


@pytest.mark.django_db
def test_folder_list_roots_invalid_parent(admin_api_client):
    resp = admin_api_client.get('/api/v2/folders', data={'parent': 'x'})
    assert resp.status_code == 400
    assert resp.data == {'parent': ['May only be an integer or "null".']}


@pytest.mark.django_db
def test_folder_list_roots(admin_api_client, folder, folder_factory):
    folder_factory(parent=folder)  # Make child folder to test that we only get roots
    resp = admin_api_client.get('/api/v2/folders', data={'parent': 'null'})
    assert resp.status_code == 200
    assert resp.data['count'] == 1
    assert resp.data['results'][0]['name'] == folder.name


@pytest.mark.django_db
def test_folder_default_ordering(admin_api_client, folder_factory):
    for name in ('B', 'C', 'A'):
        folder_factory(name=name)
    resp = admin_api_client.get('/api/v2/folders', data={'parent': 'null'})
    assert resp.status_code == 200
    assert [f['name'] for f in resp.data['results']] == ['A', 'B', 'C']


@pytest.mark.django_db
def test_folder_rest_get_quota(admin_api_client, folder):
    resp = admin_api_client.get(f'/api/v2/folders/{folder.id}/quota')
    assert resp.status_code == 200
    assert resp.data == {
        'used': 0,
        'allowed': settings.DKC_DEFAULT_QUOTA,
    }
