from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, Set, Type

from django.contrib.auth.models import Group, User
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.dispatch import receiver
from guardian.models import GroupObjectPermission, UserObjectPermission
from guardian.shortcuts import (
    assign_perm,
    get_group_perms,
    get_groups_with_perms,
    get_objects_for_user,
    get_user_perms,
    get_users_with_perms,
    remove_perm,
)
from guardian.utils import get_identity

from dkc.core.permissions import Permission, PermissionGrant

from .quota import Quota

if TYPE_CHECKING:
    # Prevent circular import
    from .folder import Folder


class Tree(models.Model):
    public: bool = models.BooleanField(default=False)
    # Prevent deletion of a Quota if it has Trees referencing it
    quota = models.ForeignKey(Quota, on_delete=models.PROTECT, related_name='trees')

    @property
    def root_folder(self) -> Folder:
        from .folder import Folder

        return Folder.objects.get(tree=self, parent=None)

    @classmethod
    def filter_by_permission(
        cls, user: User, permission: Permission, queryset: models.QuerySet['Tree']
    ) -> models.QuerySet['Tree']:
        """Filter a queryset according to a user's access.

        This method is called by the access control filter backend to limit the
        root folders returned to those the logged in user has read access to.
        """
        perms = permission.associated_permissions
        query = get_objects_for_user(user, perms, klass=queryset, any_perm=True)
        if permission == Permission.read:
            query = query.union(queryset.filter(public=True))
        return query

    def list_granted_permissions(self) -> List[PermissionGrant]:
        """Return a list of all permission grants associated with a tree."""
        grants: List[PermissionGrant] = []
        permission_strings = {p.value for p in Permission}

        for user, perms in get_users_with_perms(
            self, attach_perms=True, with_group_users=False, only_with_perms_in=permission_strings
        ).items():
            for perm in perms:
                grants.append(PermissionGrant(user_or_group=user, permission=Permission(perm)))

        for group, perms in get_groups_with_perms(self, attach_perms=True).items():
            for perm in perms:
                if perm in permission_strings:
                    grants.append(PermissionGrant(user_or_group=group, permission=Permission(perm)))
        return grants

    def has_permission(self, user: User, permission: Permission) -> bool:
        """Return whether the given user has a specific permission for the tree."""
        if permission == Permission.read and self.public:
            return True
        return any(user.has_perm(perm, self) for perm in permission.associated_permissions)

    def _get_group_permissions(self, group: Group) -> Set[Permission]:
        permission_strings = {p.value for p in Permission}
        group_perms = get_group_perms(group, self)
        return {Permission(p) for p in group_perms if p in permission_strings}

    def _get_user_permissions(self, user: User) -> Set[Permission]:
        permission_strings = {p.value for p in Permission}
        user_perms = get_user_perms(user, self)
        return {Permission(p) for p in user_perms if p in permission_strings}

    @transaction.atomic
    def grant_permission(self, grant: PermissionGrant) -> None:
        """Activate a specific permission grant.

        Applies a user or group permission to the current entity.  This
        is a wrapper around the django-guardian shortcut "assign_perm", but also contains
        logic to remove other permissions that had previously existed on the entity.
        """
        # Get a list of prior existing permissions.
        user, group = get_identity(grant.user_or_group)
        if user:
            existing_permissions = self._get_user_permissions(grant.user_or_group)
        else:
            existing_permissions = self._get_group_permissions(grant.user_or_group)

        # Assign the permission if it doesn't already exist.
        if grant.permission in existing_permissions:
            existing_permissions.remove(grant.permission)
        else:
            assign_perm(grant.permission.value, grant.user_or_group, self)

        # Remove any extra permissions on the object that existed prior.
        # In the case where the permission already existed, this is
        # expected to be a no-op, but it will clean up any inconsistencies
        # that happen to exist.
        for permission in existing_permissions:
            remove_perm(permission.value, grant.user_or_group, self)

    def remove_permission(self, grant: PermissionGrant) -> None:
        remove_perm(grant.permission.value, grant.user_or_group, self)

    @transaction.atomic
    def grant_permission_list(self, grants: List[PermissionGrant]):
        """Apply a list of permission grants in a transaction."""
        for grant in grants:
            self.grant_permission(grant)

    @transaction.atomic
    def remove_permission_list(self, grants: List[PermissionGrant]):
        """Remove a list of permission grants in a transaction."""
        for grant in grants:
            self.remove_permission(grant)

    @transaction.atomic
    def set_permission_list(self, grants: List[PermissionGrant]):
        """Set the full access control list in a transaction."""
        self.grant_permission_list(grants)

        grant_set = set(grants)
        existing_grant_set = set(self.list_granted_permissions())
        self.remove_permission_list(list(existing_grant_set - grant_set))

    def get_access(self, user: Optional[User]) -> Dict[str, bool]:
        """Return the permissions that the given user has on this entity."""
        if user is None:
            # This is a special case for the anonymous user.  Access can only
            # be 'read', and only for public trees.
            access = {p.name: False for p in Permission}
            access['read'] = self.public
            return access
        # This could be optimized to reduce multiple queries... e.g.
        # admin access implies read access.
        return {p.name: self.has_permission(user, p) for p in Permission}

    class Meta:
        permissions = (
            (Permission.read.value, 'Read access to a tree'),
            (Permission.write.value, 'Write access to a tree'),
            (Permission.admin.value, 'Admin access to a tree'),
        )


@receiver(models.signals.post_delete, sender=Tree)
def _tree_post_delete(sender: Type[Tree], instance: Tree, **kwargs):
    """Remove all permissions pointing at a deleted tree."""
    filters = models.Q(
        content_type=ContentType.objects.get_for_model(instance),
        object_pk=instance.pk,
    )
    UserObjectPermission.objects.filter(filters).delete()
    GroupObjectPermission.objects.filter(filters).delete()
