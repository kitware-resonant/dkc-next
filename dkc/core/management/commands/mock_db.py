import djclick as click
from faker import Faker

from dkc.core.models.folder import Folder

# from dkc.core.tests.factories import FolderFactory

fake = Faker()


def _populate_subtree(folder: Folder, depth: int, branching: int) -> None:
    if depth == 0:
        return

    for _ in range(branching):
        child = folder.add_child(name=fake.word())
        _populate_subtree(child, depth - 1, branching)


@click.command()
@click.argument('depth', type=click.INT)
@click.argument('branching', type=click.INT)
def command(depth: int, branching: int):
    for _ in range(branching):
        root_folder: Folder = Folder.add_root(name=fake.word())
        _populate_subtree(root_folder, depth - 1, branching)
