from datetime import timedelta

from django.core.signing import Signer
from django.utils import timezone
import pytest

from dkc.core.models import AuthorizedUpload


@pytest.fixture
def authorized_upload(admin_api_client, folder):
    return admin_api_client.post('/api/v2/authorized_uploads', data={'folder': folder.id})


@pytest.mark.django_db
def test_create_authorized_upload(admin_api_client, folder):
    resp = admin_api_client.post('/api/v2/authorized_uploads', data={'folder': folder.id})
    assert resp.status_code == 201
    assert resp.data['folder'] == folder.id
    assert resp.data['creator'] == admin_api_client.handler._force_user.id
    assert 'signature' in resp.data


@pytest.mark.django_db
def test_authorized_upload_requires_write_access(api_client, public_folder, user):
    api_client.force_authenticate(user)
    resp = api_client.post('/api/v2/authorized_uploads', data={'folder': public_folder.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_authorized_upload_signature_check(authorized_upload, api_client):
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': authorized_upload.data['folder'],
            'authorization': f'1{authorized_upload.data["signature"]}',
        },
    )
    assert resp.status_code == 403
    assert resp.json() == {'detail': 'Invalid authorization signature.'}


@pytest.mark.django_db
def test_authorized_upload_folder_check(authorized_upload, api_client, folder_factory):
    folder2 = folder_factory()
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': folder2.id,
            'authorization': authorized_upload.data['signature'],
        },
    )
    assert resp.status_code == 403
    assert resp.json() == {'detail': 'This upload was authorized to a different folder.'}


@pytest.mark.django_db
def test_authorized_upload_expired(api_client, folder, user_factory):
    admin = user_factory(is_superuser=True)
    authorized_upload = AuthorizedUpload.objects.create(
        creator=admin,
        folder=folder,
        expires=timezone.now() - timedelta(hours=1),
    )
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': folder.id,
            'authorization': Signer().sign(authorized_upload.id),
        },
    )
    assert resp.status_code == 403
    assert resp.json() == {
        'detail': 'This upload authorization has expired. Please request a new link.'
    }


@pytest.mark.django_db
def test_authorized_upload_deleted(api_client, authorized_upload, folder):
    AuthorizedUpload.objects.get(pk=authorized_upload.data['id']).delete()
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': folder.id,
            'authorization': authorized_upload.data['signature'],
        },
    )
    assert resp.status_code == 403
    assert resp.json() == {'detail': 'This upload authorization has been revoked.'}


@pytest.mark.django_db
def test_authorized_upload_success(api_client, authorized_upload):
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': authorized_upload.data['folder'],
            'authorization': authorized_upload.data['signature'],
        },
    )
    assert resp.status_code == 201
    assert resp.data['creator'] == authorized_upload.data['creator']


@pytest.mark.django_db
def test_authorized_upload_delete_permission(api_client, user, authorized_upload):
    api_client.force_authenticate(user)
    resp = api_client.delete(f'/api/v2/authorized_uploads/{authorized_upload.data["id"]}')
    assert resp.status_code == 403
    assert resp.json() == {'detail': 'Only the creator of an authorized upload may delete it.'}


@pytest.mark.django_db
def test_authorized_upload_delete_as_superuser(api_client, authorized_upload, user_factory):
    admin = user_factory(is_superuser=True)
    api_client.force_authenticate(admin)
    resp = api_client.delete(f'/api/v2/authorized_uploads/{authorized_upload.data["id"]}')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_authorized_upload_delete_as_creator(user, api_client, folder):
    authorized_upload = AuthorizedUpload.objects.create(
        creator=user,
        folder=folder,
        expires=timezone.now() + timedelta(days=1),
    )
    api_client.force_authenticate(user)
    resp = api_client.delete(f'/api/v2/authorized_uploads/{authorized_upload.id}')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_authorized_upload_completion_bad_signature(api_client, authorized_upload):
    resp = api_client.post(
        f'/api/v2/authorized_uploads/{authorized_upload.data["id"]}/completion',
        data={'authorization': f'1{authorized_upload.data["signature"]}'},
    )
    assert resp.status_code == 403
    assert resp.json() == {'detail': 'Invalid authorization signature.'}


@pytest.mark.django_db
def test_authorized_upload_completion_id_mismatch(api_client, authorized_upload):
    resp = api_client.post(
        f'/api/v2/authorized_uploads/{authorized_upload.data["id"] + 1}/completion',
        data={'authorization': authorized_upload.data['signature']},
    )
    assert resp.status_code == 403
    assert resp.json() == {'detail': 'Mismatched authorized upload ID.'}


@pytest.mark.django_db
def test_authorized_upload_completion(api_client, authorized_upload, mailoutbox):
    resp = api_client.post(
        f'/api/v2/authorized_uploads/{authorized_upload.data["id"]}/completion',
        data={'authorization': authorized_upload.data['signature']},
    )
    assert resp.status_code == 204
    with pytest.raises(AuthorizedUpload.DoesNotExist):
        AuthorizedUpload.objects.get(pk=authorized_upload.data['id'])

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == 'Authorized upload complete'
