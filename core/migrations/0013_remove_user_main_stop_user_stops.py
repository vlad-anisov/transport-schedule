# Generated by Django 4.0.3 on 2022-05-09 21:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_alter_stop_schedule'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='user',
            name='main_stop',
        ),
        migrations.AddField(
            model_name='user',
            name='stops',
            field=models.ManyToManyField(to='core.stop'),
        ),
    ]
