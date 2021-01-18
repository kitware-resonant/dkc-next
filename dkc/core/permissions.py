from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, List, Union

from django.contrib.auth.models import Group, User
from django.db import models
from rest_framework.filters import BaseFilterBackend
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.views import View

if TYPE_CHECKING:
    from dkc.core.models import File, Folder

    Model = Union[File, Folder]


class Permission(Enum):
    """
    A list of tree access permissions.

    The enum represents the list of permission types that are managed by the permission
    related methods attached to the models in this app.  These permissions differ from
    normal django permissions in that one permission can *imply* the existence of another
    permission.

    The permissions methods on the models take care to ensure that only one permission
    of these kinds is associated to a single (row, user) pair.  As a result, you should
    not directly manipulate these permissions outside of those methods.
    """

    read = 'read_tree'
    write = 'write_tree'
    admin = 'admin_tree'

    @property
    def associated_permissions(self) -> List[str]:
        """Return a list of permission labels that also provide the requested access.

        For example, a user with admin access to a tree will automatically have write
        access as well.  When we want to look up if a user has write access to a tree,
        we have to look up *both* the `write_tree` and `admin_tree` permission labels.
        Therefore,

            Permission.write.associated_permissions == ['admin_tree', 'write_tree']
        """
        perms = [self.value]

        if self == Permission.read:
            perms += [
                Permission.write.value,
                Permission.admin.value,
            ]
        elif self == Permission.write:
            perms += [Permission.admin.value]
        return perms


@dataclass(frozen=True)
class PermissionGrant:
    """A container class representing a single granted permission."""

    user_or_group: Union[User, Group]
    permission: Permission


# These are permissions classes that integrate with the access control API implemented in models.
# They assume a "has_permission" method that decides if the user has the required access for the
# entity.
class IsReadOnlyEndpoint(BasePermission):
    def has_object_permission(self, request: Request, view: View, obj) -> bool:
        return request.method in SAFE_METHODS

    def has_permission(self, request: Request, view: View) -> bool:
        return request.method in SAFE_METHODS


class IsReadable(BasePermission):
    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        return obj.has_permission(request.user, Permission.read)


class IsWriteable(BasePermission):
    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        return obj.has_permission(request.user, Permission.write)


class IsAdmin(BasePermission):
    def has_object_permission(self, request: Request, view: View, obj: Model) -> bool:
        return obj.has_permission(request.user, Permission.admin)


HasAccess = (IsReadOnlyEndpoint & IsReadable) | (IsAuthenticated & IsWriteable)  # type: ignore


# A filter backend that integrates with the access control API implemented in the models.  It
# assumes a "filter_by_permission" class method that filters a queryset by read access to the given
# user.
class PermissionFilterBackend(BaseFilterBackend):
    def filter_queryset(
        self, request: Request, queryset: models.QuerySet[Model], view: View
    ) -> models.QuerySet[Model]:
        model = queryset.model
        return model.filter_by_permission(request.user, Permission.read, queryset)
