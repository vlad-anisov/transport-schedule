# Generated by Django 4.0.3 on 2022-05-12 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_remove_user_main_stop_user_stops'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='user_id',
        ),
        migrations.AddField(
            model_name='user',
            name='access_token',
            field=models.CharField(default=0, max_length=1000),
            preserve_default=False,
        ),
    ]