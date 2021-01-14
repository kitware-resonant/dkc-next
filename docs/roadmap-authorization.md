# data.kitware.com Roadmap: Authorization, Permissions, User Groups

## Policy Decisions

Authorization settings, also called access control, for DKCN refers to both permissions and a `public/private` setting.

DKCN will provide a permission system, and permissions will apply at a root folder level. DKCN will allow objects to have a `public/private` setting in addition to permissions. All folders and files descended from a root folder will have the same authorization settings as the root folder. If you want separate authorization settings, create a separate root folder.

Authorizations are granted on an object to individual users or user groups, and the permission levels are: `read`, `write`, and `admin`. Read permission allows a user/group to read the object (including object properties, object metadata, and binary contents), write permission allows a user/group to mutate an object's properties except for permissions, admin permissions allow a user/group to see all the permissions on an object and to mutate the permissions on the object. `admin` access implies `write` access, `write` access implies `read` access. If you do not have `admin` access to the object, you can see your own permissions and whether the object is public, but not the full permission set of the object.

Users can have individual authorization to an object, or can have authorization to an object by virtue of being in a user group that has authorization to an object.

Objects have a `public/private` setting. If an object is public, it acts as if it has read permission by the entire world, regardless of whether a user is even logged into the system. If an object is private, the object is not visible to a user unless the user has authorization to read the object via user or user group permissions.

Currently the following design decisions exist:

* User objects are private, but user names are public. Only that user or an admin user can see a user object.
* TODO(correct these because this is likely wrong, as it hasn't been fully implemented) User group objects are private, but user group names are public. Only users in the group or an admin user can see the user group object.
* There is no difference between a public object and having read access to that object.
* There is no separate permission for having read access to a file object or having access to download the binary contents of a file object.

## How These Policy Decisions Affect The Code Design

Much of this was implemented in https://github.com/girder/dkc-next/pull/66, and some explanation is in order.

Django assumes that permissions are orthogonal, i.e. `admin` and `write` and `read` are disjoint from each other. DKCN assumes that `admin` implies `write` and `write` implies `read`. We make these assumptions because a generation of users was trained to expect this in the previous data.kitware.com, which took its permissions from Girder 3 and prior. This divergence of assumptions explains some of the implementation complexity.

In order to have compact (and therefore simpler) policies on objects in DKCN, whenever a permission is set on an object, any implied permission is removed. E.g., if an object currently is `read` for some user/group, when it is set to `write`, the `read` permission will be removed.

When access to an object is checked for a user, the user may have access via `public/private` settings, via permissions attached to a group that the user is a member of, or via the user's specific permissions on the object. Further, `read` access could exist by virtue of `write` or `admin`, and `write` access could exist by virtue of `admin`.

All of these decisions may lead to surprising implementation in the `Tree` model. The `Tree` model uses standard Django Guardian methods, but needs to wrap those in more complex logic due to the above policy choices.

We have created an API on our models with methods `has_permission` and `filter_by_permission`, that are needed to work with the `Permission` class. We have three different models that each need to provide their own implementation of these methods: `Tree`, `Folder`, and `File`. `File`s delegate their permission checks to their containing `Folder`, and `Folder`s delegate their permission checks to their root `Folder`, which is attached to a `Tree`. This is because root `Folder`s determine the permissions for all child `Folder`s, and there is a one-to-one mapping of root `Folder`s to `Trees`. Note that `Tree`s are an internal implementation detail and are not exposed publicly. Any new models would need to implement `has_permission` and `filter_by_permission` to participate in this permission scheme.
