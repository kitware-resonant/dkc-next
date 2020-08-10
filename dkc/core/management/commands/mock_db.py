from django.core.management.base import BaseCommand
from faker import Faker

from dkc.core.models.folder import Folder

# from dkc.core.tests.factories import FolderFactory

fake = Faker()


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('depth', nargs='+', type=int)
        parser.add_argument('branching', nargs='+', type=int)

    def handle(self, *args, **options):
        for _root_num in range(10):
            root_folder: Folder = Folder.add_root(name=fake.word())

            for _subfolder_num in range(5):
                root_folder.add_child(name=fake.word())
