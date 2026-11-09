from django import forms

from cinema.models import Cinema, Genre, Hall, Movie, Showtime


class StyledForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "input")


class GenreForm(StyledForm):
    class Meta:
        model = Genre
        fields = ["name_en", "name_ru"]


class MovieForm(StyledForm):
    class Meta:
        model = Movie
        fields = [
            "title_en",
            "title_ru",
            "description_en",
            "description_ru",
            "genre",
            "duration",
            "year",
            "poster",
        ]
        widgets = {
            "description_en": forms.Textarea(attrs={"rows": 4}),
            "description_ru": forms.Textarea(attrs={"rows": 4}),
        }


class CinemaForm(StyledForm):
    class Meta:
        model = Cinema
        fields = ["name", "city_en", "city_ru", "address_en", "address_ru"]


class HallForm(StyledForm):
    class Meta:
        model = Hall
        fields = ["cinema", "name", "rows_count", "seats_per_row"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["rows_count"].disabled = True
            self.fields["seats_per_row"].disabled = True


class ShowtimeForm(StyledForm):
    class Meta:
        model = Showtime
        fields = ["movie", "hall", "starts_at", "price"]
        widgets = {
            "starts_at": forms.DateTimeInput(
                attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"
            ),
        }
