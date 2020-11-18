# data.kitware.com Roadmap: Folders, Files, Quotas, and Metadata

DKC's primary use case is mirroring a filesystem hierarchy on the web, for sharing. DKC will not be optimized for efficient access to the hierarchical representation, such as would be desired for running analysis on the stored file data.

Important domain objects are `Folders` and `Files`, which are similar to their filesystem notions. All folders will have an ultimate anscetor called a root folder, and any user can create one or more root folders. Files live within a single folder.

All users have a storage quota, tied to the space taken up by their files. Only root folders have quotas, and a user's quota is shared among all of the user's root folders. User quotas are set to a system-wide default value.Files count against the storage quota of the root folder, regardless of who the uploading user is, i.e. if user A uploads files into a root folder owned by user B, the files count against user B's quota. Quotas are oblivious to any deduplication that happens within the storage layer. Admin users can grant an individual root folder its own quota, to satisfy a desire to make a root folder a shared space, such as a Collection in Girder 3.

Folders and files can have arbitrary JSON metadata attached to them. A file a container that has a name, a parent folder, a URL to binary contents, and JSON metadata.
