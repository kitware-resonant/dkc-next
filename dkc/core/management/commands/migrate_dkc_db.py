from collections import defaultdict
from datetime import datetime, timezone
from typing import DefaultDict, List, Optional, Set, Tuple

from django.contrib.auth.models import User
from django.db import transaction
import djclick as click
from pymongo import MongoClient
from pymongo.database import Database

from dkc.core.models import File, Folder, Tree
from dkc.core.permissions import Permission, PermissionGrant

# BEFORE you run this script, set your default user quota to something very high e.g. 10<<40

# ssh -L 27017:0.0.0.0:27017 zach.mullen@data
# docker-compose run --rm django ./manage.py \
#  migrate_dkc_db mongodb://host.docker.internal:27017/ 2 >> checkpoint.txt

UserMap = DefaultDict[str, User]  # maps legacy user ObjectIDs to dkc-next users

PERM_MAP = {  # maps legacy permission enum to dkc-next enum
    0: Permission.read,
    1: Permission.write,
    2: Permission.admin,
}


def aware_date(dt: datetime) -> datetime:
    return dt.replace(tzinfo=timezone.utc)


def _sync_file(
    legacy_file: dict,
    parent: Folder,
    legacy_item: dict,
    user_map: UserMap,
) -> None:
    if 'size' not in legacy_file:
        return  # probably one of these weird "link files". Just throw it away

    try:
        file = File.objects.get(folder=parent, name=legacy_file['name'])
    except File.DoesNotExist:
        file = File(
            folder=parent,
            name=legacy_file['name'],
            description=legacy_item.get('description') or '',
            content_type=legacy_file.get('mimeType', 'application/octet-stream'),
            legacy_item_id=str(legacy_item['_id']),
            legacy_file_id=str(legacy_file['_id']),
            user_metadata=legacy_item.get('meta', {}),
            size=legacy_file['size'],
            creator=user_map[str(legacy_file['creatorId'])],
        )
        file.save()
        file.created = aware_date(legacy_file['created'])
        file.save(update_fields=['created'])


def _sync_item(db: Database, legacy_item: dict, parent: Folder, user_map: UserMap) -> None:
    legacy_files = list(db.file.find({'itemId': legacy_item['_id']}))
    if len(legacy_files) == 1:  # convert item to file
        _sync_file(legacy_files[0], parent, legacy_item, user_map)
    else:  # convert item to folder
        try:
            folder = Folder.objects.get(parent=parent, name=legacy_item['name'])
        except Folder.DoesNotExist:
            folder = Folder(
                parent=parent,
                tree=parent.tree,
                name=legacy_item['name'],
                description=legacy_item.get('description') or '',
                user_metadata=legacy_item.get('meta', {}),
                legacy_id=str(legacy_item['_id']),
                creator=user_map[str(legacy_item['creatorId'])],
            )
            folder.save()
            folder.created = aware_date(legacy_item['created'])
            folder.save(update_fields=['created'])

        for legacy_file in legacy_files:
            _sync_file(legacy_file, folder, legacy_item, user_map)


def _sync_folder(db: Database, legacy_folder: dict, parent: Folder, user_map: UserMap) -> None:
    try:
        folder = Folder.objects.get(parent=parent, name=legacy_folder['name'])
    except Folder.DoesNotExist:
        folder = Folder(
            parent=parent,
            tree=parent.tree,
            name=legacy_folder['name'],
            description=legacy_folder.get('description') or '',
            user_metadata=legacy_folder.get('meta', {}),
            legacy_id=str(legacy_folder['_id']),
            creator=user_map[str(legacy_folder['creatorId'])],
        )
        folder.save()
        folder.created = aware_date(legacy_folder['created'])
        folder.save(update_fields=['created'])

    legacy_folders = list(
        db.folder.find({'parentId': legacy_folder['_id'], 'parentCollection': 'folder'})
    )
    for legacy_subfolder in legacy_folders:
        _sync_folder(db, legacy_subfolder, folder, user_map)
    del legacy_folders

    legacy_items = list(db.item.find({'folderId': legacy_folder['_id']}))
    for legacy_item in legacy_items:
        _sync_item(db, legacy_item, folder, user_map)


def _set_tree_permissions(tree: Tree, collection: dict, user_map: UserMap) -> None:
    # Currently this just sets the ACL of the tree to be the ACL of the collection.
    # Any differing permissions in subfolders are ignored."""
    user_acl = collection.get('access', {}).get('users', [])
    grants: List[PermissionGrant] = []

    for user_entry in user_acl:
        oid = str(user_entry['id'])
        if oid in user_map:
            perm = PERM_MAP[user_entry['level']]
            grants.append(PermissionGrant(user_map[oid], perm))

    # TODO groups?
    tree.set_permission_list(grants)


def _sync_root_folders(
    db: Database, user_map: UserMap, skip_collections: Set[str], skip_users: Set[str]
) -> None:
    collections = list(db.collection.find())
    for collection in collections:
        if str(collection['_id']) in skip_collections:
            continue

        try:
            folder = Folder.objects.get(parent=None, name=collection['name'])
        except Folder.DoesNotExist:
            with transaction.atomic():
                creator = user_map[str(collection.get('creatorId'))]
                tree: Tree = Tree.objects.create(
                    quota=creator.quota, public=collection.get('public', False)
                )
                folder = Folder(
                    parent=None,
                    tree=tree,
                    name=collection['name'],
                    description=collection.get('description') or '',
                    user_metadata=collection.get('meta', {}),
                    legacy_id=str(collection['_id']),
                    creator=creator,
                )
                folder.save()
                folder.created = aware_date(collection['created'])
                folder.save(update_fields=['created'])

        _set_tree_permissions(folder.tree, collection, user_map)

        legacy_folders = list(
            db.folder.find({'parentId': collection['_id'], 'parentCollection': 'collection'})
        )
        for legacy_folder in legacy_folders:
            _sync_folder(db, legacy_folder, folder, user_map)

        print(f'CHECKPOINT collection {str(collection["_id"])}')

    del collections

    legacy_users = list(db.user.find())
    for legacy_user in legacy_users:
        if str(legacy_user['_id']) in skip_users:
            continue

        folder_name = f'@{legacy_user["login"]}'
        user = user_map[str(legacy_user['login'])]
        try:
            folder = Folder.objects.get(parent=None, name=folder_name)
        except Folder.DoesNotExist:
            with transaction.atomic():
                tree: Tree = Tree.objects.create(quota=user.quota, public=False)
                tree.grant_permission(PermissionGrant(user, Permission.admin))
                folder = Folder(
                    parent=None,
                    tree=tree,
                    name=folder_name,
                    description=f'Migrated user data for {legacy_user["login"]}',
                    creator=user,
                )
                folder.save()
                folder.created = aware_date(legacy_user['created'])
                folder.save(update_fields=['created'])

        legacy_folders = list(
            db.folder.find({'parentId': legacy_user['_id'], 'parentCollection': 'user'})
        )
        for legacy_folder in legacy_folders:
            _sync_folder(db, legacy_folder, folder, user_map)

        print(f'CHECKPOINT user {str(legacy_user["_id"])}')


def _sync_users(db: Database, default_user: User) -> UserMap:
    user_map: UserMap = defaultdict(lambda: default_user)
    for legacy_user in db.user.find():
        try:
            user = User.objects.get(email=legacy_user['email'])
        except User.DoesNotExist:
            user = User(
                username=legacy_user['login'],
                email=legacy_user['email'],
                first_name=legacy_user['firstName'],
                last_name=legacy_user['lastName'],
                date_joined=aware_date(legacy_user['created']),
                password='',  # TODO migrate passwords?
            )
            user.save()
            # TODO groups?
        user_map[str(legacy_user['_id'])] = user
    return user_map


def _read_checkpoint_file(checkpoint_file: Optional[str]) -> Tuple[Set[str], Set[str]]:
    colls, users = set(), set()
    if checkpoint_file:
        with open(checkpoint_file) as fd:
            for line in fd.readlines():
                if line.startswith('CHECKPOINT'):
                    _, type_, oid = line.split()
                    if type_ == 'collection':
                        colls.add(oid)
                    elif type_ == 'user':
                        users.add(oid)
    return colls, users


@click.command()
@click.argument('mongo_uri', type=click.STRING)
@click.argument('user_id', type=click.INT)
@click.option('--checkpoint-file', type=click.Path(dir_okay=False, exists=True))
def command(mongo_uri: str, user_id: int, checkpoint_file: Optional[str]) -> None:
    skip_colls, skip_users = _read_checkpoint_file(checkpoint_file)
    default_user: User = User.objects.get(id=user_id)
    assert not default_user.is_anonymous
    db = MongoClient(mongo_uri).girder

    user_map = _sync_users(db, default_user)
    _sync_root_folders(db, user_map, skip_colls, skip_users)
