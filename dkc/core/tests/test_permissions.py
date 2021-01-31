from guardian.shortcuts import assign_perm
import pytest

from dkc.core.models import File, Folder
from dkc.core.permissions import Permission, PermissionGrant


@pytest.fixture
def user(user_factory):
    return user_factory()


@pytest.fixture
def public_tree(tree_factory):
    return tree_factory(public=True)


@pytest.fixture
def no_access_tree(tree_factory):
    return tree_factory(public=False)


@pytest.fixture
def readable_tree(user, tree_factory):
    readable_tree = tree_factory(public=False)
    assign_perm(Permission.read.value, user, readable_tree)
    return readable_tree


@pytest.fixture
def writeable_tree(user, tree_factory):
    writeable_tree = tree_factory(public=False)
    assign_perm(Permission.write.value, user, writeable_tree)
    return writeable_tree


@pytest.fixture
def admin_tree(user, tree_factory):
    admin_tree = tree_factory(public=False)
    assign_perm(Permission.admin.value, user, admin_tree)
    return admin_tree


@pytest.fixture
def public_folder(public_tree, folder_factory):
    return folder_factory(name='public', tree=public_tree)


@pytest.fixture
def no_access_folder(no_access_tree, folder_factory):
    return folder_factory(name='no_access', tree=no_access_tree)


@pytest.fixture
def readable_folder(user, readable_tree, folder_factory):
    return folder_factory(name='readable', tree=readable_tree)


@pytest.fixture
def writeable_folder(user, writeable_tree, folder_factory):
    return folder_factory(name='writeable', tree=writeable_tree)


@pytest.fixture
def admin_folder(user, admin_tree, folder_factory):
    return folder_factory(name='admin', tree=admin_tree)


@pytest.fixture
def all_folders(public_folder, no_access_folder, readable_folder, writeable_folder, admin_folder):
    return {
        'public': public_folder,
        'no_access': no_access_folder,
        'readable': readable_folder,
        'writeable': writeable_folder,
        'admin': admin_folder,
    }


@pytest.fixture
def public_file(public_tree, file_factory):
    return file_factory(name='public', folder__tree=public_tree)


@pytest.fixture
def no_access_file(no_access_tree, file_factory):
    return file_factory(name='no_access', folder__tree=no_access_tree)


@pytest.fixture
def readable_file(user, readable_tree, file_factory):
    return file_factory(name='readable', folder__tree=readable_tree)


@pytest.fixture
def writeable_file(user, writeable_tree, file_factory):
    return file_factory(name='writeable', folder__tree=writeable_tree)


@pytest.fixture
def admin_file(user, admin_tree, file_factory):
    return file_factory(name='admin', folder__tree=admin_tree)


@pytest.fixture
def all_files(public_file, no_access_file, readable_file, writeable_file, admin_file):
    return {
        'public': public_file,
        'no_access': no_access_file,
        'readable': readable_file,
        'writeable': writeable_file,
        'admin': admin_file,
    }


@pytest.mark.django_db
@pytest.mark.parametrize(
    'permission,expected',
    [
        (Permission.read, {'public', 'readable', 'writeable', 'admin'}),
        (Permission.write, {'writeable', 'admin'}),
        (Permission.admin, {'admin'}),
    ],
)
def test_folder_permissions_filter(user, all_folders, permission, expected):
    folders = Folder.filter_by_permission(user, permission, Folder.objects).all()
    assert {folder.name for folder in folders} == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    'permission,expected',
    [
        (Permission.read, {'public', 'readable', 'writeable', 'admin'}),
        (Permission.write, {'writeable', 'admin'}),
        (Permission.admin, {'admin'}),
    ],
)
def test_file_permissions_filter(user, all_files, permission, expected):
    files = File.filter_by_permission(user, permission, File.objects).all()
    assert {file.name for file in files} == expected


@pytest.mark.django_db
@pytest.mark.parametrize(
    'name,status',
    [
        ('public', 200),
        ('no_access', 404),
        ('readable', 200),
        ('writeable', 200),
        ('admin', 200),
    ],
)
def test_folder_api_get(api_client, user, all_folders, name, status):
    folder = all_folders[name]
    api_client.force_authenticate(user=user)
    resp = api_client.get(f'/api/v2/folders/{folder.id}')
    assert resp.status_code == status


@pytest.mark.django_db
@pytest.mark.parametrize(
    'name,status',
    [
        ('public', 200),
        ('no_access', 404),
        ('readable', 200),
        ('writeable', 200),
        ('admin', 200),
    ],
)
def test_file_api_get(api_client, user, all_files, name, status):
    file = all_files[name]
    api_client.force_authenticate(user=user)
    resp = api_client.get(f'/api/v2/files/{file.id}')
    assert resp.status_code == status


@pytest.mark.django_db
@pytest.mark.parametrize(
    'name,status',
    [
        ('public', 403),
        ('no_access', 404),
        ('readable', 403),
        ('writeable', 200),
        ('admin', 200),
    ],
)
def test_folder_api_patch(api_client, user, all_folders, name, status):
    folder = all_folders[name]
    api_client.force_authenticate(user=user)
    resp = api_client.patch(f'/api/v2/folders/{folder.id}', data={'name': 'foo'})
    assert resp.status_code == status


@pytest.mark.django_db
@pytest.mark.parametrize(
    'name,status',
    [
        ('public', 403),
        ('no_access', 404),
        ('readable', 403),
        ('writeable', 200),
        ('admin', 200),
    ],
)
def test_file_api_patch(api_client, user, all_files, name, status):
    file = all_files[name]
    api_client.force_authenticate(user=user)
    resp = api_client.patch(f'/api/v2/files/{file.id}', data={'name': 'foo'})
    assert resp.status_code == status


@pytest.mark.django_db
def test_put_permissions(api_client, user, user_factory, admin_folder):
    user2 = user_factory()
    api_client.force_authenticate(user=user)

    data = [
        {
            'name': user2.username,
            'model': 'user',
            'permission': 'read',
        }
    ]
    resp = api_client.put(
        f'/api/v2/folders/{admin_folder.id}/permissions', data=data, format='json'
    )
    assert resp.status_code == 200
    assert admin_folder.tree.has_permission(user2, Permission.read)
    assert not admin_folder.tree.has_permission(user, Permission.read)


@pytest.mark.django_db
def test_patch_permissions(api_client, user, user_factory, admin_folder):
    user2 = user_factory()
    api_client.force_authenticate(user=user)

    data = [
        {
            'name': user2.username,
            'model': 'user',
            'permission': 'read',
        }
    ]
    resp = api_client.patch(
        f'/api/v2/folders/{admin_folder.id}/permissions', data=data, format='json'
    )
    assert resp.status_code == 200
    assert admin_folder.tree.has_permission(user2, Permission.read)


@pytest.mark.django_db
def test_delete_permissions(api_client, user, user_factory, admin_folder):
    user2 = user_factory()
    api_client.force_authenticate(user=user)
    admin_folder.tree.grant_permission(
        PermissionGrant(user_or_group=user2, permission=Permission.read),
    )
    assert admin_folder.tree.has_permission(user2, Permission.read)

    data = [
        {
            'name': user2.username,
            'model': 'user',
            'permission': 'read',
        }
    ]
    resp = api_client.delete(
        f'/api/v2/folders/{admin_folder.id}/permissions', data=data, format='json'
    )
    assert resp.status_code == 200
    assert not admin_folder.tree.has_permission(user2, Permission.read)


@pytest.mark.django_db
def test_root_folder_create_sets_permissions(api_client, user):
    api_client.force_authenticate(user=user)
    resp = api_client.post('/api/v2/folders', data={'name': 'test', 'parent': None})
    assert resp.status_code == 201
    assert resp.data['public'] is False
    assert resp.data['access'] == {'read': True, 'write': True, 'admin': True}
    folder = Folder.objects.get(pk=resp.data['id'])
    assert folder.has_permission(user, Permission.admin) is True


@pytest.mark.django_db
def test_anonymous_user_cannot_create_root_folder(api_client):
    resp = api_client.post('/api/v2/folders', data={'name': 'test'})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_anonymous_user_cannot_create_files(api_client, folder, s3ff_field_value):
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'test.txt',
            'folder': folder.id,
            'blob': s3ff_field_value,
        },
    )
    assert resp.status_code == 401


@pytest.mark.django_db
def test_folder_create_permission_enforcement(api_client, folder, user):
    api_client.force_authenticate(user=user)
    resp = api_client.post('/api/v2/folders', data={'name': 'test', 'parent': folder.id})
    assert resp.status_code == 403


@pytest.mark.django_db
def test_file_create_permission_enforcement(api_client, folder, user, s3ff_field_value):
    api_client.force_authenticate(user=user)
    resp = api_client.post(
        '/api/v2/files',
        data={
            'name': 'test.txt',
            'folder': folder.id,
            'blob': s3ff_field_value,
        },
    )
    assert resp.status_code == 403


@pytest.mark.django_db
def test_set_admin_permission(user_factory, folder):
    admin = user_factory(is_superuser=True)
    grant = PermissionGrant(user_or_group=admin, permission=Permission.read)
    tree = folder.tree

    tree.grant_permission(grant)
    assert grant in tree.list_granted_permissions()
