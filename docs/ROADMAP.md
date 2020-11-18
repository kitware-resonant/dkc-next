# data.kitware.com Roadmap

data.kitware.com (DKC) is a public hosted web service at domain name data.kitware.com used to share data within Kitware and between Kitware and collaborators. Currently data.kitware.com hosts a live Girder 3 instance used by Kitware, and the application being built in this repo (called dkc-next, or DKCN) is hosted at https://dkc-next.girderops.net/. 

The current swagger API for DKCN is hosted at https://dkc-next.girderops.net/api/docs/swagger.

## Tech Stack

The tech stack is the same as the Girder 4.0 [cookiecutter-django-girder](https://github.com/girder/cookiecutter-django-girder) tech stack, namely:

* Django
* Postgres
* Minio

This tech stack also uses:

* [django-composed-configuration](https://github.com/girder/django-composed-configuration) Turnkey Django settings for data management applications
* [django-s3-file-filed](https://github.com/girder/django-s3-file-field) A Django widget library for uploading files directly to S3 (or MinIO) through the browser. This means that bytes for binary objects are not proxied through the Django app server.
* [terraform-heroku-django](https://github.com/girder/terraform-heroku-django) A Terraform module to provision Django-Girder infrastructure on Heroku + AWS

Much of the admin UI is provided by built in Django server rendered components. There is a VueJs [client](https://github.com/girder/girder_web_components/tree/dkc-next) being built, descended from girder_web_components, the exact scope of which is open.

## Deployment

DKCN is deployed on Heroku with a MinIO instance on prem at Kitware (KHQ in Clifton Park, NY). The deployment is managed through [Terraform](https://github.com/girder/dkc-next/tree/master/terraform) and CI/CD to the extent possible.

This deployment setup was chosen to maximize developer and deployment velocity (Heroku with its excellent tooling) while also providing a fixed cost for outgoing bandwidth (MinIO on prem, compared to e.g. S3).

## Feature Roadmap and Design Decisions

### Exists

### Decided upon, and being implemented

1. [Folders, Files, Quotas, and Metadata](FILES-FOLDERS-ROADMAP.md)
2. [Authentication](AUTHENTICATION-ROADMAP.md)
3. [Authorization, Permissions, User Groups](AUTHORIZATION-ROADMAP.md)
4. [User Agreement](AGREEMENT-ROADMAP.md) 

### Desired future feature additions, not yet decided upon

1. Hashsum download/EXTERNAL_DATA support
2. CLI with upload and download capabilities
3. Web client hierarchy browser
4. Construction of large zip files for downloading hierarchies
5. Authorized upload by anonymous users
6. Share a private file via a link
