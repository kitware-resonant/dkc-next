from __future__ import annotations

from typing import TYPE_CHECKING

from django.db import models

if TYPE_CHECKING:
    # Prevent circular import
    from .folder import Folder


class Tree(models.Model):
    @property
    def root_folder(self) -> Folder:
        from .folder import Folder

        return Folder.objects.get(tree=self, parent=None)
