# Generated by Django 2.2.23 on 2021-09-23 22:01

from django.db import migrations, models
import django.db.models.deletion
from django.db.models import F


def copy_defc_column(apps, _):
    """
        Used in the migration below to copy over the disaster_emergecny_fund_code column below so that
        it can be converted to a Foreign Key. This approach minimizes any downtime.
    """
    GTASSF133Balances = apps.get_model("references", "GTASSF133Balances")
    GTASSF133Balances.objects.all().update(disaster_emergency_fund=F("disaster_emergency_fund_code"))


class Migration(migrations.Migration):

    dependencies = [
        ('references', '0053_office'),
    ]

    operations = [
        migrations.AddField(
            model_name='gtassf133balances',
            name='disaster_emergency_fund',
            field=models.ForeignKey(blank=True, db_column='disaster_emergency_fund_code_temp', null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='references.DisasterEmergencyFundCode'),
        ),
        migrations.RunPython(copy_defc_column, reverse_code=migrations.RunPython.noop),
        migrations.RenameField(
            model_name='gtassf133balances',
            old_name='disaster_emergency_fund_code',
            new_name='disaster_emergency_fund_code_old',
        ),
        migrations.AlterField(
            model_name='gtassf133balances',
            name='disaster_emergency_fund',
            field=models.ForeignKey(blank=True, db_column='disaster_emergency_fund_code', null=True,
                                    on_delete=django.db.models.deletion.DO_NOTHING,
                                    to='references.DisasterEmergencyFundCode'),
        ),
        migrations.AlterUniqueTogether(
            name='gtassf133balances',
            unique_together={('fiscal_year', 'fiscal_period', 'disaster_emergency_fund', 'tas_rendering_label')},
        ),
        migrations.RemoveField(
            model_name='gtassf133balances',
            name='disaster_emergency_fund_code_old',
        ),
    ]
