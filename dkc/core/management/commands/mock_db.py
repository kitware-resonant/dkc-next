import typing

from django.contrib.auth.models import User
import djclick as click

from dkc.core.models import Tree
from dkc.core.models.folder import Folder
from dkc.core.permissions import Permission, PermissionGrant
from dkc.core.tests.factories import FileFactory, FolderFactory


def _populate_subtree(
    folder: typing.Optional[Folder], depth: int, user: User, branching: int, files: int
) -> None:
    if depth == 0:
        for _ in range(files):
            FileFactory(folder=folder, creator=user)
        return

    for _ in range(branching):
        child: Folder = FolderFactory(parent=folder, creator=user)
        _populate_subtree(child, depth - 1, user, branching, files)


@click.command()
@click.argument('depth', type=click.INT)
@click.argument('branching', type=click.INT)
@click.argument('files', type=click.INT, default=0)
@click.argument('user_id', type=click.INT, default=None)
def command(depth: int, branching: int, files: int, user_id: int):
    user = User.objects.get(id=user_id) if user_id else User.objects.first()
    _populate_subtree(None, depth, user, branching, files)
    for tree in Tree.objects.all():
        tree.grant_permission(PermissionGrant(user_or_group=user, permission=Permission.admin))
