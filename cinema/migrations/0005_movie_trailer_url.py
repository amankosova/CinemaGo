from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("cinema", "0004_alter_genre_name_kk_alter_movie_age_rating_and_more"),
    ]
    operations = [
        migrations.AddField(
            model_name="movie",
            name="trailer_url",
            field=models.URLField("Official YouTube trailer", max_length=500, blank=True, default=""),
        ),
    ]
