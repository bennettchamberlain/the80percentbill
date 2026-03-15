# Generated manually for campaign model replacement

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('email_management', '0004_segment'),
    ]

    operations = [
        # Drop old campaign tables
        migrations.RunSQL(
            "DROP TABLE IF EXISTS email_management_emailcampaign_contact_lists",
            reverse_sql=migrations.RunSQL.noop
        ),
        migrations.RunSQL(
            "DROP TABLE IF EXISTS email_management_emailcampaign",
            reverse_sql=migrations.RunSQL.noop
        ),
        
        # Create new campaign model
        migrations.CreateModel(
            name='EmailCampaign',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Campaign Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('scheduled', 'Scheduled'), ('sending', 'Sending'), ('paused', 'Paused'), ('completed', 'Completed'), ('cancelled', 'Cancelled')], db_index=True, default='draft', max_length=20, verbose_name='Status')),
                ('daily_send_limit', models.IntegerField(default=1000, help_text='Maximum emails to send per day (0 = unlimited)', verbose_name='Daily Send Limit')),
                ('batch_size', models.IntegerField(default=50, help_text='Number of emails to send in each batch', verbose_name='Batch Size')),
                ('start_date', models.DateTimeField(blank=True, help_text='When to begin sending (null = send immediately when started)', null=True, verbose_name='Start Date')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('contact_list', models.ForeignKey(blank=True, help_text='Target recipients via contact list', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns', to='email_management.contactlist', verbose_name='Contact List')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_campaigns', to='email_management.emailuser', verbose_name='Created By')),
                ('segment', models.ForeignKey(blank=True, help_text='Target recipients via segment filters', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='campaigns', to='email_management.segment', verbose_name='Segment')),
                ('template', models.ForeignKey(help_text='Template is referenced, not copied. Changes to template do not affect sent emails.', on_delete=django.db.models.deletion.PROTECT, related_name='campaigns', to='email_management.emailtemplate', verbose_name='Email Template')),
            ],
            options={
                'verbose_name': 'Email Campaign',
                'verbose_name_plural': 'Email Campaigns',
                'db_table': 'email_campaigns',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='emailcampaign',
            index=models.Index(fields=['status'], name='email_campa_status_0fd52f_idx'),
        ),
        migrations.AddIndex(
            model_name='emailcampaign',
            index=models.Index(fields=['start_date'], name='email_campa_start_d_c6e9cf_idx'),
        ),
        migrations.AddIndex(
            model_name='emailcampaign',
            index=models.Index(fields=['-created_at'], name='email_campa_created_5d9286_idx'),
        ),
    ]
