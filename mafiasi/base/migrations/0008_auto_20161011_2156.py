# -*- coding: utf-8 -*-
# Generated by Django 1.10.2 on 2016-10-11 19:56


from django.db import migrations, models
import mafiasi.base.validation


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_auto_20161005_1857'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mafiasi',
            name='account',
            field=models.CharField(max_length=40, validators=[mafiasi.base.validation.validate_ascii]),
        ),
    ]
