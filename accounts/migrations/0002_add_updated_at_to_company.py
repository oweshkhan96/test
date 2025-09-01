from django.db import migrations, models
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='updated_at',
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
    ]
