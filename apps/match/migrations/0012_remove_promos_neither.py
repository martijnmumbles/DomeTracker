# Generated by Django 3.2.16 on 2023-03-12 17:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("match", "0011_promos_neither"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="promos",
            name="neither",
        ),
    ]
