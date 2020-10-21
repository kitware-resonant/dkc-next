from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models.expressions

import dkc.core.models.quota


def _default_folder_owner():
    # This will only be used on legacy databases, and should eventually be elided in a squash
    from django.contrib.auth.models import User

    return User.objects.first()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0009_merge_default_site'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='quota',
            name='allocation',
        ),
        migrations.AddField(
            model_name='folder',
            name='owner',
            field=models.ForeignKey(
                default=_default_folder_owner,
                on_delete=django.db.models.deletion.PROTECT,
                to='auth.user',
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='folder',
            name='quota',
            field=models.ForeignKey(
                null=True, on_delete=django.db.models.deletion.RESTRICT, to='core.quota'
            ),
        ),
        migrations.AddField(
            model_name='folder',
            name='used',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='quota',
            name='allowed',
            field=models.PositiveBigIntegerField(default=dkc.core.models.quota._default_user_quota),
        ),
        migrations.AddField(
            model_name='quota',
            name='used',
            field=models.PositiveBigIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='file',
            name='creator',
            field=models.ForeignKey(
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AlterField(
            model_name='quota',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='quota',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddConstraint(
            model_name='folder',
            constraint=models.CheckConstraint(
                check=models.Q(
                    models.Q(('parent__isnull', True), ('quota__isnull', False)),
                    models.Q(('parent__isnull', False), ('quota__isnull', True)),
                    _connector='OR',
                ),
                name='root_quota_not_null',
            ),
        ),
        migrations.AddConstraint(
            model_name='quota',
            constraint=models.CheckConstraint(
                check=models.Q(used__lte=django.db.models.expressions.F('allowed')),
                name='used_lte_allowed',
            ),
        ),
    ]
