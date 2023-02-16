# Generated by Django 3.2.5 on 2023-02-14 13:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dqa', '0010_dqaworkplan_percent_completed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dataverification',
            name='indicator',
            field=models.CharField(choices=[('', 'Select indicator'), ('PrEP_New', 'PrEP_New'), ('Starting_TPT', 'Starting TPT'), ('GBV_Sexual violence', 'GBV_Sexual violence'), ('GBV_Emotional and /Physical Violence', 'GBV_Emotional and /Physical Violence'), ('Cervical Cancer Screening (Women on ART)', 'Cervical Cancer Screening (Women on ART)'), ('Total tested ', 'Total tested '), ('Number tested Positive aged <15 years', 'Number tested Positive aged <15 years'), ('Number tested Positive aged 15+ years', 'Number tested Positive aged 15+ years'), ('Known Positive at 1st ANC', 'Known Positive at 1st ANC'), ('Positive Results_ANC', 'Positive Results_ANC'), ('On HAART at 1st ANC', 'On HAART at 1st ANC'), ('Start HAART ANC', 'Start HAART ANC'), ('Infant ARV Prophyl_ANC', 'Infant ARV Prophyl_ANC'), ('Positive Results_L&D', 'Positive Results_L&D'), ('Start HAART_L&D', 'Start HAART_L&D'), ('Infant ARV Prophyl_L&D', 'Infant ARV Prophyl_L&D'), ('Positive Results_PNC<=6 weeks', 'Positive Results_PNC<=6 weeks'), ('Start HAART_PNC<= 6 weeks', 'Start HAART_PNC<= 6 weeks'), ('Infant ARV Prophyl_PNC<= 6 weeks', 'Infant ARV Prophyl_PNC<= 6 weeks'), ('Under 15yrs Starting on ART', 'Under 15yrs Starting on ART'), ('Above 15yrs Starting on ART ', 'Above 15yrs Starting on ART '), ('New & Relapse TB_Cases', 'New & Relapse TB_Cases'), ('Currently on ART <15Years', 'Currently on ART <15Years'), ('Currently on ART 15+ years', 'Currently on ART 15+ years')], max_length=250),
        ),
    ]