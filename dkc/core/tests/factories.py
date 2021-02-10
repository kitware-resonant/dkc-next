from django.contrib.auth.models import User
import factory
import factory.django

from dkc.core.models import File, Folder, Terms, TermsAgreement, Tree

_metadata_faker = factory.Faker('pydict', nb_elements=5, value_types=[str, int, float, bool])


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    class Params:
        username_base = factory.Faker('user_name')

    username = factory.LazyAttributeSequence(lambda o, n: f'{o.username_base}{n}')
    email = factory.Faker('safe_email')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_superuser = False


class TreeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Tree

    class Params:
        creator = factory.SubFactory(UserFactory)

    public = False
    # No need to instantiate a quota, just fetch from the user creating this
    quota = factory.SelfAttribute('creator.quota')


class FolderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Folder

    class Params:
        name_base = factory.Faker('word')

    name = factory.LazyAttributeSequence(lambda o, n: f'{o.name_base}-{n}')
    description = factory.Faker('paragraph')
    user_metadata = _metadata_faker
    parent = None
    tree = factory.Maybe(
        'parent',
        factory.SelfAttribute('parent.tree'),
        # Make the new tree be created by (and use the quota of) this folder's creator
        factory.SubFactory(TreeFactory, creator=factory.SelfAttribute('..creator')),
    )
    creator = factory.SubFactory(UserFactory)


class FileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = File

    class Params:
        name_base = factory.Faker('word')
        name_ext = factory.Faker('file_extension')

    name = factory.LazyAttributeSequence(lambda o, n: f'{o.name_base}-{n}.{o.name_ext}')
    description = factory.Faker('paragraph')
    blob = factory.django.FileField(data=b'fakefilebytes', filename='fake.txt')
    size = factory.SelfAttribute('blob.size')
    user_metadata = _metadata_faker
    folder = factory.SubFactory(FolderFactory)
    creator = factory.SubFactory(UserFactory)


class TreeWithRootFactory(TreeFactory):
    @factory.post_generation
    def root_folder(self, create, *args, **kwargs):
        # Make the new folder be created by the same user as it's tree's quota
        return FolderFactory(tree=self, creator=self.quota.user)


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
