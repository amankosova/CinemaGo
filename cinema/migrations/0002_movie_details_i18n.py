from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('cinema','0001_initial')]
    operations = [
        migrations.AddField(model_name='genre', name='name_kk', field=models.CharField(max_length=60, blank=True, default='')),
        migrations.AddField(model_name='movie', name='title_kk', field=models.CharField(max_length=150, blank=True, default='')),
        migrations.AddField(model_name='movie', name='description_kk', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='movie', name='director', field=models.CharField(max_length=250, blank=True, default='')),
        migrations.AddField(model_name='movie', name='main_cast', field=models.TextField(blank=True, default='')),
        migrations.AddField(model_name='movie', name='country', field=models.CharField(max_length=100, blank=True, default='')),
        migrations.AddField(model_name='movie', name='age_rating', field=models.CharField(max_length=10, blank=True, default='')),
        migrations.AddField(model_name='movie', name='genres', field=models.ManyToManyField(to='cinema.genre', related_name='movies', blank=True)),
    ]
