# Generated by Django 4.2 on 2024-11-20 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('games', '0002_playlog_totalplaytime_delete_playtime'),
    ]

    operations = [
        migrations.AlterField(
            model_name='playlog',
            name='end_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='playlog',
            name='start_at',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='totalplaytime',
            name='latest_at',
            field=models.DateTimeField(null=True),
        ),
    ]
