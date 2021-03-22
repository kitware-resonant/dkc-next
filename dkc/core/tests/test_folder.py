from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import pytest

from dkc.core.models import File, Folder, Tree
from dkc.core.models.folder import MAX_DEPTH


@pytest.mark.django_db
def test_folder_name_invalid(folder_factory):
    folder = folder_factory(name='name / withslash')

    with pytest.raises(ValidationError, match='Name may not contain forward slashes'):
        folder.full_clean()


@pytest.mark.django_db
def test_is_root_root(folder):
    assert folder.is_root is True


@pytest.mark.django_db
def test_is_root_child(child_folder):
    assert child_folder.is_root is False


@pytest.mark.django_db
def test_ancestors(folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    assert list(grandchild.ancestors) == [grandchild, child, folder]


@pytest.mark.django_db
def test_folder_abs_path(folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    assert grandchild.abs_path == f'/{folder.name}/{child.name}/{grandchild.name}/'


@pytest.mark.django_db
def test_root_folder_depth_is_zero(folder):
    assert folder.depth == 0


@pytest.mark.django_db
def test_child_folder_depth_computed(folder, folder_factory):
    child = folder_factory(parent=folder)
    assert child.depth == folder.depth + 1


@pytest.mark.django_db
def test_folder_max_depth(folder_factory):
    folder = folder_factory(depth=MAX_DEPTH)
    child = folder_factory.build(parent=folder)

    with pytest.raises(ValidationError, match=r'Maximum folder depth exceeded.'):
        child.full_clean()


@pytest.mark.django_db
def test_folder_max_depth_constraint(folder_factory):
    folder = folder_factory(depth=MAX_DEPTH)
    child = folder_factory.build(parent=folder)
    # Make sure foreign key references exist in database first
    child.creator.save()

    with pytest.raises(IntegrityError, match=r'folder_max_depth'):
        # save without validation
        child.save()


@pytest.mark.django_db
def test_folder_sibling_names_unique(folder, folder_factory):
    child = folder_factory(parent=folder)
    with pytest.raises(IntegrityError):
        folder_factory(name=child.name, parent=folder)


@pytest.mark.django_db
def test_folder_sibling_names_unique_files(file, folder_factory):
    sibling_folder = folder_factory.build(parent=file.folder, name=file.name)
    with pytest.raises(ValidationError, match='A file with that name already exists here.'):
        sibling_folder.full_clean()


@pytest.mark.django_db
def test_root_folder_names_unique(folder, folder_factory):
    other_root = folder_factory()
    other_root.name = folder.name
    with pytest.raises(IntegrityError, match=r'folder_name'):
        other_root.save()


@pytest.mark.django_db
def test_folder_names_not_globally_unique(folder_factory):
    root = folder_factory()
    child = folder_factory(name=root.name, parent=root)
    assert child


@pytest.mark.parametrize('amount', [-10, 0, 10])
@pytest.mark.django_db
def test_increment_size(folder_factory, amount):
    initial_size = 100
    root = folder_factory(size=initial_size)
    root.tree.quota.used = initial_size
    root.tree.quota.save()
    child = folder_factory(parent=root, size=initial_size)
    grandchild = folder_factory(parent=child, size=initial_size)

    grandchild.increment_size(amount)

    # Local references to other objects "root", "child" are stale
    # We can only guarantee integrity from the mutated object
    new_size = initial_size + amount
    assert grandchild.size == new_size
    assert grandchild.parent.size == new_size
    assert grandchild.parent.parent.size == new_size
    assert grandchild.parent.parent.tree.quota.used == new_size


@pytest.mark.django_db
def test_increment_size_negative(folder_factory):
    # Make the root too small
    root = folder_factory(size=5)
    root.tree.quota.used = 10
    root.tree.quota.save()
    child = folder_factory(parent=root, size=10)

    # Increment the child, which tests enforcement across propagation
    # An IntegrityError is expected, since this should cause a 500 if it actually happens
    with pytest.raises(IntegrityError, match=r'folder_size'):
        child.increment_size(-10)


@pytest.mark.django_db
def test_folder_delete(folder):
    folder.delete()

    with pytest.raises(Folder.DoesNotExist):
        Folder.objects.get(id=folder.id)

    with pytest.raises(Tree.DoesNotExist):
        Tree.objects.get(pk=folder.tree_id)


@pytest.mark.django_db
def test_folder_delete_recursive(folder, folder_factory, file_factory):
    child = folder_factory(parent=folder)
    file = file_factory(folder=folder)
    folder.delete()

    with pytest.raises(Folder.DoesNotExist):
        Folder.objects.get(id=child.id)

    with pytest.raises(File.DoesNotExist):
        File.objects.get(id=file.id)
