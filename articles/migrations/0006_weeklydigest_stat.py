from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0005_weeklydigest_quote'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklydigest',
            name='stat_number',
            field=models.CharField(blank=True, max_length=50, null=True, verbose_name='本周数字'),
        ),
        migrations.AddField(
            model_name='weeklydigest',
            name='stat_context',
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name='数字背景'),
        ),
    ]
