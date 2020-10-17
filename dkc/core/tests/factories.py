from django.contrib.auth.models import User
import factory
import factory.django

from dkc.core.models import File, Folder, Terms, TermsAgreement, Tree

_metadata_faker = factory.Faker('pydict', nb_elements=5, value_types=[str, int, float, bool])


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.SelfAttribute('email')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')


class TreeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tree


class FolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Folder

    name = factory.Faker('word')
    description = factory.Faker('paragraph')
    parent = None
    tree = factory.Maybe(
        'parent', factory.SelfAttribute('parent.tree'), factory.SubFactory(TreeFactory)
    )
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


class TreeWithRootFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tree

    @factory.post_generation
    def root_folder(self, create, *args, **kwargs):
        return FolderFactory(tree=self)


class TermsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Terms

    tree = factory.SubFactory(TreeWithRootFactory)
    text = factory.Faker('paragraph')


class TermsAgreementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TermsAgreement

    terms = factory.SubFactory(TermsFactory)
    user = factory.SubFactory(UserFactory)
    checksum = factory.SelfAttribute('terms.checksum')
