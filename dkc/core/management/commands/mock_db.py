import typing

from django.contrib.auth.models import User
import djclick as click

from dkc.core.models.folder import Folder
from dkc.core.tests.factories import FileFactory, FolderFactory


def _populate_subtree(
    folder: typing.Optional[Folder], depth: int, branching: int, files: int, user: User
) -> None:
    if depth == 0:
        for _ in range(files):
            FileFactory(folder=folder, creator=user)
        return

    for _ in range(branching):
        child: Folder = FolderFactory(parent=folder, owner=user)
        _populate_subtree(child, depth - 1, branching, files, user)


@click.command()
@click.argument('depth', type=click.INT)
@click.argument('branching', type=click.INT)
@click.argument('files', type=click.INT, default=0)
def command(depth: int, branching: int, files: int):
    user = User.objects.first()
    _populate_subtree(None, depth, branching, files, user)
