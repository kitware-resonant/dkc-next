from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
import pytest

from dkc.core.exceptions import MaxFolderDepthExceeded
from dkc.core.models.folder import Folder


@pytest.fixture
def limited_tree_height():
    original, Folder.MAX_TREE_HEIGHT = Folder.MAX_TREE_HEIGHT, 3
    yield Folder.MAX_TREE_HEIGHT
    Folder.MAX_TREE_HEIGHT = original


def test_folder_name_invalid(folder_factory):
    folder = folder_factory.build(name='name / withslash')

    # Since the folder is not saved and added to a tree, other validation errors are also present,
    # so it's critical to match the error by string content
    with pytest.raises(ValidationError, match='Name may not contain forward slashes'):
        folder.full_clean()


@pytest.mark.django_db
def test_root_folder_depth_is_zero(folder):
    assert folder.depth == 0


@pytest.mark.django_db
def test_child_folder_depth_computed(folder, folder_factory):
    child = folder_factory(parent=folder)
    assert child.depth == folder.depth + 1


@pytest.mark.django_db
def test_folder_max_depth_enforced(folder, folder_factory, limited_tree_height):
    for _ in range(limited_tree_height):
        folder = folder_factory(parent=folder)

    with pytest.raises(MaxFolderDepthExceeded):
        folder_factory(parent=folder)


@pytest.mark.django_db
def test_folder_root_self_reference(folder):
    assert folder.root_folder == folder


@pytest.mark.django_db
def test_root_folder_inherited(folder, folder_factory):
    child = folder_factory(parent=folder)
    grandchild = folder_factory(parent=child)
    assert child.root_folder == folder
    assert grandchild.root_folder == folder


@pytest.mark.django_db
def test_folder_sibling_names_unique(folder, folder_factory):
    child = folder_factory(parent=folder)
    with pytest.raises(IntegrityError):
        folder_factory(name=child.name, parent=folder)


@pytest.mark.django_db
def test_root_folder_names_unique(folder, folder_factory):
    with pytest.raises(IntegrityError):
        folder_factory(name=folder.name)


@pytest.mark.django_db
def test_folder_names_not_globally_unique(folder_factory):
    root = folder_factory()
    folder_factory(name=root.name, parent=root)
