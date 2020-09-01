from typing import Optional

from django.contrib.auth.models import User
import factory.django

from dkc.core.models import File, Folder


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Faker('user_name')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = File

    name = factory.Faker('file_name')
    blob = factory.django.FileField(data=b'fakefilebytes', filename='fake.txt')
    owner = factory.SubFactory(UserFactory)


class FolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Folder

    class Params:
        parent: Optional[Folder] = None

    name = factory.Faker('word')
    description = factory.Faker('paragraph')
    parent_id = factory.LazyAttribute(lambda params: params.parent.id if params.parent else None)
