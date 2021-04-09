from datetime import datetime, timezone

import pytest

from dkc.core.models import AuthorizedUpload
from dkc.core.permissions import Permission, PermissionGrant


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
            'folder': authorized_upload.folder.id,
            'authorization': f'1{authorized_upload.signature}',
        },
    )
    assert resp.status_code == 403
    assert resp.data == {'detail': 'Invalid authorization signature.'}


@pytest.mark.django_db
def test_authorized_upload_folder_check(authorized_upload, api_client, folder_factory):
    folder = folder_factory()
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': folder.id,
            'authorization': authorized_upload.signature,
        },
    )
    assert resp.status_code == 403
    assert resp.data == {'detail': 'This upload was authorized to a different folder.'}


@pytest.mark.django_db
def test_authorized_upload_expired(api_client, authorized_upload):
    authorized_upload.created = datetime(2020, 1, 1, tzinfo=timezone.utc)
    authorized_upload.save()  # we can't override auto_now_add field at creation time

    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': authorized_upload.folder.id,
            'authorization': authorized_upload.signature,
        },
    )
    assert resp.status_code == 403
    assert resp.data == {
        'detail': 'This upload authorization has expired. Please request a new link.'
    }


@pytest.mark.django_db
def test_authorized_upload_deleted(api_client, authorized_upload, folder):
    authorized_upload.delete()
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': folder.id,
            'authorization': authorized_upload.signature,
        },
    )
    assert resp.status_code == 403
    assert resp.data == {'detail': 'This upload authorization has been revoked.'}


@pytest.mark.django_db
def test_authorized_upload_checks_write_access(api_client, authorized_upload):
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': authorized_upload.folder.id,
            'authorization': authorized_upload.signature,
        },
    )
    assert resp.status_code == 403
    assert resp.data == {'detail': 'You are not allowed to create files in this folder.'}


@pytest.mark.django_db
def test_authorized_upload_success(api_client, authorized_upload):
    authorized_upload.folder.tree.grant_permission(
        PermissionGrant(authorized_upload.creator, Permission.write)
    )
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'foo.txt',
            'size': 123,
            'folder': authorized_upload.folder.id,
            'authorization': authorized_upload.signature,
        },
    )
    assert resp.status_code == 201
    assert resp.data['creator'] == authorized_upload.creator.id


@pytest.mark.django_db
def test_authorized_upload_delete_permission(api_client, authorized_upload, user_factory):
    api_client.force_authenticate(user_factory())
    resp = api_client.delete(f'/api/v2/authorized_uploads/{authorized_upload.id}')
    assert resp.status_code == 403
    assert resp.data == {'detail': 'Only the creator of an authorized upload may delete it.'}


@pytest.mark.django_db
def test_authorized_upload_delete_as_superuser(admin_api_client, authorized_upload):
    resp = admin_api_client.delete(f'/api/v2/authorized_uploads/{authorized_upload.id}')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_authorized_upload_delete_as_creator(api_client, authorized_upload):
    api_client.force_authenticate(authorized_upload.creator)
    resp = api_client.delete(f'/api/v2/authorized_uploads/{authorized_upload.id}')
    assert resp.status_code == 204


@pytest.mark.django_db
def test_authorized_upload_completion_bad_signature(api_client, authorized_upload):
    resp = api_client.post(
        f'/api/v2/authorized_uploads/{authorized_upload.id}/completion',
        data={'authorization': f'1{authorized_upload.signature}'},
    )
    assert resp.status_code == 403
    assert resp.data == {'detail': 'Invalid authorization signature.'}


@pytest.mark.django_db
def test_authorized_upload_completion_id_mismatch(api_client, authorized_upload_factory):
    upload1, upload2 = authorized_upload_factory(), authorized_upload_factory()
    resp = api_client.post(
        f'/api/v2/authorized_uploads/{upload1.id}/completion',
        data={'authorization': upload2.signature},
    )
    assert resp.status_code == 403
    assert resp.data == {'detail': 'Invalid authorization signature.'}


@pytest.mark.django_db
def test_authorized_upload_completion(api_client, authorized_upload, mailoutbox):
    resp = api_client.post(
        f'/api/v2/authorized_uploads/{authorized_upload.id}/completion',
        data={'authorization': authorized_upload.signature},
    )
    assert resp.status_code == 204
    assert not AuthorizedUpload.objects.filter(pk=authorized_upload.id).exists()

    assert len(mailoutbox) == 1
    assert mailoutbox[0].subject == 'Authorized upload complete'
