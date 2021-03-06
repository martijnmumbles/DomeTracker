# Generated by Django 3.2.13 on 2022-06-27 19:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("summoner", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="summoner",
            name="account_id",
            field=models.CharField(default=1, max_length=46),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="summoner",
            name="last_match_id",
            field=models.CharField(default=1, max_length=15),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="summoner",
            name="puu_id",
            field=models.CharField(default=1, max_length=78, unique=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="summoner",
            name="summoner_id",
            field=models.CharField(default=1, max_length=47),
            preserve_default=False,
        ),
    ]
