import typing

import djclick as click

from dkc.core.models.folder import Folder
from dkc.core.tests.factories import FolderFactory


def _populate_subtree(folder: typing.Optional[Folder], depth: int, branching: int) -> None:
    if depth == 0:
        return

    for _ in range(branching):
        child: Folder = FolderFactory(parent=folder)
        child.save()
        _populate_subtree(child, depth - 1, branching)


@click.command()
@click.argument('depth', type=click.INT)
@click.argument('branching', type=click.INT)
def command(depth: int, branching: int):
    _populate_subtree(None, depth, branching)
