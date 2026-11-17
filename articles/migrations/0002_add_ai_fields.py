# Generated migration file for AI fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('articles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='article',
            name='ai_summary',
            field=models.TextField(blank=True, null=True, verbose_name='AI摘要(300字)'),
        ),
        migrations.AddField(
            model_name='article',
            name='ai_key_point',
            field=models.CharField(blank=True, max_length=500, null=True, verbose_name='AI核心观点'),
        ),
    ]