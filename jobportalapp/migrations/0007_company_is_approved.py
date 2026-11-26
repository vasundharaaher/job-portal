from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jobportalapp', '0006_contactmessage_admin_reply_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='is_approved',
            field=models.BooleanField(default=False),
        ),
    ]
