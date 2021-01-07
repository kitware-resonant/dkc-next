from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_extensions.db.fields
import girder_utils.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0001_default_site'),
    ]

    operations = [
        migrations.CreateModel(
            name='Tree',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Quota',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                ('allocation', models.BigIntegerField(default=0)),
                (
                    'user',
                    models.OneToOneField(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name='Folder',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                inverse_match=True,
                                message='Name may not contain forward slashes.',
                                regex='/',
                            )
                        ],
                    ),
                ),
                (
                    'depth',
                    models.PositiveSmallIntegerField(
                        editable=False,
                        validators=[
                            django.core.validators.MaxValueValidator(
                                30, message='Maximum folder depth exceeded.'
                            )
                        ],
                    ),
                ),
                ('size', models.PositiveBigIntegerField(default=0, editable=False)),
                ('description', models.TextField(blank=True, max_length=3000)),
                (
                    'user_metadata',
                    girder_utils.models.JSONObjectField(),
                ),
                (
                    'parent',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='child_folders',
                        to='core.folder',
                    ),
                ),
                (
                    'tree',
                    models.ForeignKey(
                        editable=False,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='all_folders',
                        to='core.tree',
                    ),
                ),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='File',
            fields=[
                (
                    'id',
                    models.AutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name='ID'
                    ),
                ),
                (
                    'created',
                    django_extensions.db.fields.CreationDateTimeField(
                        auto_now_add=True, verbose_name='created'
                    ),
                ),
                (
                    'modified',
                    django_extensions.db.fields.ModificationDateTimeField(
                        auto_now=True, verbose_name='modified'
                    ),
                ),
                (
                    'name',
                    models.CharField(
                        max_length=255,
                        validators=[
                            django.core.validators.RegexValidator(
                                inverse_match=True,
                                message='Name may not contain forward slashes.',
                                regex='/',
                            )
                        ],
                    ),
                ),
                ('description', models.TextField(blank=True, max_length=3000)),
                (
                    'content_type',
                    models.CharField(default='application/octet-stream', max_length=255),
                ),
                ('blob', models.FileField(upload_to='')),
                ('size', models.PositiveBigIntegerField(editable=False)),
                (
                    'sha512',
                    models.CharField(
                        blank=True, db_index=True, default='', editable=False, max_length=128
                    ),
                ),
                (
                    'user_metadata',
                    girder_utils.models.JSONObjectField(),
                ),
                (
                    'creator',
                    models.ForeignKey(
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    'folder',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='files',
                        to='core.folder',
                    ),
                ),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddIndex(
            model_name='folder',
            index=models.Index(fields=['parent', 'name'], name='core_folder_parent__50a462_idx'),
        ),
        migrations.AddConstraint(
            model_name='folder',
            constraint=models.UniqueConstraint(
                fields=('parent', 'name'), name='folder_siblings_name_unique'
            ),
        ),
        migrations.AddConstraint(
            model_name='folder',
            constraint=models.UniqueConstraint(
                condition=models.Q(parent=None), fields=('name',), name='root_folder_name_unique'
            ),
        ),
        migrations.AddConstraint(
            model_name='folder',
            constraint=models.CheckConstraint(
                check=models.Q(depth__lte=30), name='folder_max_depth'
            ),
        ),
        migrations.AddConstraint(
            model_name='folder',
            constraint=models.UniqueConstraint(
                condition=models.Q(parent=None),
                fields=('tree',),
                name='unique_root_folder_per_tree',
            ),
        ),
        migrations.AddIndex(
            model_name='file',
            index=models.Index(fields=['folder', 'name'], name='core_file_folder__f8cfaa_idx'),
        ),
        migrations.AddConstraint(
            model_name='file',
            constraint=models.UniqueConstraint(
                fields=('folder', 'name'), name='file_siblings_name_unique'
            ),
        ),
    ]
