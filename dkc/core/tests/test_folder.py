from django.core.exceptions import ValidationError
import pytest


def test_folder_name_invalid(folder_factory):
    folder = folder_factory(name='name / withslash')

    # Since the folder is not saved and added to a tree, other validation errors are also present,
    # so it's critical to match the error by string content
    with pytest.raises(ValidationError, match='Name may not contain forward slashes'):
        folder.full_clean()
