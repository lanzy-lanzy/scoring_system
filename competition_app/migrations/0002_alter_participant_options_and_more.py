# Generated by Django 5.1.2 on 2024-12-16 22:46

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('competition_app', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='participant',
            options={},
        ),
        migrations.AlterUniqueTogether(
            name='participant',
            unique_together=set(),
        ),
        migrations.RemoveField(
            model_name='criterion',
            name='weight_percentage',
        ),
        migrations.AddField(
            model_name='competition',
            name='show_results',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='judge',
            name='bio',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='judge',
            name='expertise',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='judge',
            name='profile_image',
            field=models.ImageField(blank=True, default='defaults/people.svg', null=True, upload_to='judge_profiles/'),
        ),
        migrations.CreateModel(
            name='ParticipantCompetition',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.PositiveIntegerField()),
                ('registration_date', models.DateTimeField(auto_now_add=True)),
                ('competition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='competition_app.competition')),
                ('participant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='competition_app.participant')),
            ],
            options={
                'ordering': ['number'],
                'unique_together': {('competition', 'number')},
            },
        ),
        migrations.AddField(
            model_name='participant',
            name='competitions',
            field=models.ManyToManyField(related_name='participants', through='competition_app.ParticipantCompetition', to='competition_app.competition'),
        ),
        migrations.RemoveField(
            model_name='participant',
            name='competition',
        ),
        migrations.RemoveField(
            model_name='participant',
            name='number',
        ),
        migrations.CreateModel(
            name='JudgeAssignment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_at', models.DateTimeField(auto_now_add=True)),
                ('status', models.CharField(choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive')], default='ACTIVE', max_length=20)),
                ('competition', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='judge_assignments', to='competition_app.competition')),
                ('judge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='assignments', to='competition_app.judge')),
                ('rounds', models.ManyToManyField(related_name='judge_assignments', to='competition_app.round')),
            ],
            options={
                'unique_together': {('judge', 'competition')},
            },
        ),
    ]
