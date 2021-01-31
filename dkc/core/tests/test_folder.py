from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import pytest

from dkc.core.models.folder import MAX_DEPTH


def test_folder_name_invalid(folder_factory):
    folder = folder_factory.build(name='name / withslash')

    # Since the folder is not saved and added to a tree, other validation errors are also present,
    # so it's critical to match the error by string content
    with pytest.raises(ValidationError, match='Name may not contain forward slashes'):
        folder.full_clean()


def test_is_root_root(folder_factory):
    folder = folder_factory.build()
    assert folder.is_root is True


def test_is_root_child(folder_factory):
    folder = folder_factory.build()
    child = folder_factory.build(parent=folder)
    assert child.is_root is False


@pytest.mark.django_db
def test_ancestors(folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    assert list(grandchild.ancestors) == [grandchild, child, folder]


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
    other_root = folder_factory.build(name=folder.name)
    # Make sure foreign key references exist in database first
    other_root.creator.save()
    other_root.tree.save()
    with pytest.raises(IntegrityError):
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
    child = folder_factory(parent=root, size=initial_size)
    grandchild = folder_factory(parent=child, size=initial_size)

    grandchild.increment_size(amount)

    # Local references to other objects "root", "child" are stale
    # We can only guarantee integrity from the mutated object
    new_size = initial_size + amount
    assert grandchild.size == new_size
    assert grandchild.parent.size == new_size
    assert grandchild.parent.parent.size == new_size


@pytest.mark.django_db
def test_increment_size_negative(folder_factory):
    # Make the root too small
    root = folder_factory(size=5)
    child = folder_factory(parent=root, size=10)

    # Increment the child, which tests enforcement across propagation
    with pytest.raises(IntegrityError, match=r'size'):
        child.increment_size(-10)
