# Generated by Django 4.1.2 on 2022-11-19 17:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("Student", "0012_student_faceencoding"),
    ]

    operations = [
        migrations.RemoveField(model_name="student", name="faceEncoding",),
    ]