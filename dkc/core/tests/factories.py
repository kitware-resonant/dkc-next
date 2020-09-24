from django.contrib.auth.models import User
import factory.django

from dkc.core.models import File, Folder

_metadata_faker = factory.Faker('pydict', nb_elements=5, value_types=[str, int, float, bool])


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class FolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Folder

    name = factory.Faker('word')
    description = factory.Faker('paragraph')
    parent = None
    user_metadata = _metadata_faker


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = File

    name = factory.Faker('file_name')
    description = factory.Faker('paragraph')
    blob = factory.django.FileField(data=b'fakefilebytes', filename='fake.txt')
    creator = factory.SubFactory(UserFactory)
    folder = factory.SubFactory(FolderFactory)
    user_metadata = _metadata_faker
