import pytest

from dkc.core.models.tree import Tree


@pytest.mark.django_db
def test_created_root_folder(folder):
    assert Tree.objects.count() == 1


@pytest.mark.django_db
def test_not_created_child_folder(folder, folder_factory):
    child = folder_factory(parent=folder)
    folder_factory(parent=child)
    assert Tree.objects.count() == 1


@pytest.mark.django_db
def test_created_multiple_roots(folder_factory):
    folder1 = folder_factory()
    folder2 = folder_factory()
    assert Tree.objects.count() == 2
    assert folder1.tree != folder2.tree


@pytest.mark.django_db
def test_deleted_root_folder(folder):
    folder.delete()
    assert Tree.objects.count() == 0


@pytest.mark.django_db
def test_not_deleted_child_folder(folder, folder_factory):
    child = folder_factory(parent=folder)
    child.delete()
    assert Tree.objects.count() == 1


@pytest.mark.django_db
def test_all_folders(folder, folder_factory):
    # Add another child folder, to make it slightly more challenging
    folder_factory(parent=folder)
    tree = folder.tree
    assert tree.all_folders.count() == 2


@pytest.mark.django_db
def test_root_folder(folder, folder_factory):
    # Add another child folder, to make it slightly more challenging
    folder_factory(parent=folder)
    tree = Tree.objects.first()
    assert tree.root_folder == folder
