# Generated by Django 4.2 on 2025-01-03 07:48

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0005_alter_totalplaytime_totaltime'),
    ]

    operations = [
        migrations.DeleteModel(
            name='DenyLog',
        ),
    ]
