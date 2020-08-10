import djclick as click
from faker import Faker

from dkc.core.models.folder import Folder

# from dkc.core.tests.factories import FolderFactory

fake = Faker()


@click.command()
@click.argument('depth', type=click.INT)
@click.argument('branching', type=click.INT)
def command(depth, branching):
    for _root_num in range(10):
        root_folder: Folder = Folder.add_root(name=fake.word())

        for _subfolder_num in range(5):
            root_folder.add_child(name=fake.word())
