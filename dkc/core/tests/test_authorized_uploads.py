import pytest


@pytest.mark.django_db
def test_create_authorized_upload(admin_api_client, folder):
    resp = admin_api_client.post(f'/api/v2/folders/{folder.id}/authorized_upload')
    assert resp.status_code == 201
    assert resp.data['folder'] == folder.id
    assert resp.data['creator'] == admin_api_client.handler._force_user.id
    assert 'signature' in resp.data


@pytest.mark.django_db
def test_authorized_upload_requires_write_access(api_client, public_folder, user):
    api_client.force_authenticate(user)
    resp = api_client.post(f'/api/v2/folders/{public_folder.id}/authorized_upload')
    assert resp.status_code == 403
