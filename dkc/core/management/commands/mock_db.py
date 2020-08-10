import djclick as click

from dkc.core.models.folder import Folder
from dkc.core.tests.factories import FolderFactory


def _populate_subtree(folder: Folder, depth: int, branching: int) -> None:
    if depth == 0:
        return

    for _ in range(branching):
        child: Folder = FolderFactory()
        folder.add_child(instance=child)  # equivalent to .save()
        _populate_subtree(child, depth - 1, branching)


@click.command()
@click.argument('depth', type=click.INT)
@click.argument('branching', type=click.INT)
def command(depth: int, branching: int):
    for _ in range(branching):
        root_folder: Folder = FolderFactory()
        Folder.add_root(instance=root_folder)  # equivalent to .save()
        _populate_subtree(root_folder, depth - 1, branching)
