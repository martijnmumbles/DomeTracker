# Generated by Django 3.2.16 on 2023-01-17 16:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("match", "0010_auto_20220716_1124"),
    ]

    operations = [
        migrations.AddField(
            model_name="promos",
            name="neither",
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]
