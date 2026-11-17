from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0004_emailsendconfig_subscriber_emailsendlog'),
    ]

    operations = [
        migrations.AddField(
            model_name='weeklydigest',
            name='quote',
            field=models.TextField(blank=True, help_text='AI从本周文章中提取的最具冲击力的一句话', null=True, verbose_name='本周金句'),
        ),
    ]
