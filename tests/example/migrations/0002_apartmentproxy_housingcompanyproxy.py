# Generated by Django 4.2.4 on 2023-08-25 20:55

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("example", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApartmentProxy",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("example.apartment",),
        ),
        migrations.CreateModel(
            name="HousingCompanyProxy",
            fields=[],
            options={
                "proxy": True,
                "indexes": [],
                "constraints": [],
            },
            bases=("example.housingcompany",),
        ),
    ]
