# Generated by Django 4.0.3 on 2022-05-09 18:54

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_user_city'),
    ]

    operations = [
        migrations.AlterField(
            model_name='stop',
            name='schedule',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.CharField(blank=True, max_length=5, null=True), blank=True, null=True, size=None),
        ),
    ]