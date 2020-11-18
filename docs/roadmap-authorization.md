# data.kitware.com Roadmap: Authorization, Permissions, User Groups

Authorization settings, also called access control, for DKCN refers to both permissions and a public/private setting.

DKCN will provide a permission system, and permissions will apply at a root folder level. DKCN will allow objects to have a public/private setting in addition to permissions. All folders and files descended from a root folder will have the same authorization settings as the root folder. If you want separate authorization settings, create a separate root folder.

Authorizations are granted on an object to individual users or user groups, and the permission levels are: `read`, `write`, and `admin`. Read permission allows a user/group to read the object (including object properties, object metadata, and binary contents), write permission allows a user/group to mutate an object's properties except for permissions, admin permissions allow a user/group to see all the permissions on an object and to mutate the permissions on the object. Admin access implies write access, write access implies read access. If you do not have admin access to the object, you can see your own permissions and whether the object is public, but not the full permission set of the object.

Users can have individual authorization to an object, or can have authorization to an object by virtue of being in a user group that has authorization to an object.

Objects have a public/private setting. If an object is public, it acts as if it has read permission by the entire world, regardless of whether a user is even logged into the system. If an object is private, the object is not visible to a user unless the user has authorization to read the object via user or user group permissions.

Currently the following design decisions exist:

* User objects are private, but user names are public. Only that user or an admin user can see a user object.
* TODO(correct these because this is likely wrong, as it hasn't been fully implemented) User group objects are private, but user group names are public. Only users in the group or an admin user can see the user group object.
* There is no difference between a public object and having read access to that object.
* There is no separate permission for having read access to a file object or having access to download the binary contents of a file object.
