from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy

from cinema.models import Cinema, Genre, Hall, Movie, Showtime, Ticket

from .decorators import staff_required
from .forms import CinemaForm, GenreForm, HallForm, MovieForm, ShowtimeForm

SECTIONS = {
    "movies": {
        "title": gettext_lazy("Movies"),
        "model": Movie,
        "form": MovieForm,
        "columns": [
            (gettext_lazy("Title"), "title"),
            (gettext_lazy("Genre"), "genre"),
            (gettext_lazy("Duration (min)"), "duration"),
            (gettext_lazy("Year"), "year"),
        ],
    },
    "cinemas": {
        "title": gettext_lazy("Cinemas"),
        "model": Cinema,
        "form": CinemaForm,
        "columns": [
            (gettext_lazy("Name"), "name"),
            (gettext_lazy("City"), "city"),
            (gettext_lazy("Address"), "address"),
        ],
    },
    "halls": {
        "title": gettext_lazy("Halls"),
        "model": Hall,
        "form": HallForm,
        "columns": [
            (gettext_lazy("Cinema"), "cinema"),
            (gettext_lazy("Hall name"), "name"),
            (gettext_lazy("Rows"), "rows_count"),
            (gettext_lazy("Seats in a row"), "seats_per_row"),
        ],
    },
    "showtimes": {
        "title": gettext_lazy("Showtimes"),
        "model": Showtime,
        "form": ShowtimeForm,
        "columns": [
            (gettext_lazy("Movie"), "movie"),
            (gettext_lazy("Hall"), "hall"),
            (gettext_lazy("Starts at"), "starts_at"),
            (gettext_lazy("Price (KZT)"), "price"),
        ],
    },
    "genres": {
        "title": gettext_lazy("Genres"),
        "model": Genre,
        "form": GenreForm,
        "columns": [
            (gettext_lazy("Name (English)"), "name_en"),
            (gettext_lazy("Name (Russian)"), "name_ru"),
        ],
    },
}

BOOKED_LOOKUP = {
    "showtimes": "showtime",
    "movies": "showtime__movie",
    "halls": "showtime__hall",
    "cinemas": "showtime__hall__cinema",
}


def panel_render(request, template, context):
    context["nav"] = [(key, section["title"]) for key, section in SECTIONS.items()]
    return render(request, template, context)


def get_section(key):
    section = SECTIONS.get(key)
    if section is None:
        raise Http404
    return section


@staff_required
def dashboard(request):
    counts = [
        (key, section["title"], section["model"].objects.count())
        for key, section in SECTIONS.items()
    ]
    recent_tickets = Ticket.objects.select_related(
        "user", "seat", "showtime__movie", "showtime__hall__cinema"
    )[:8]
    context = {
        "counts": counts,
        "tickets_total": Ticket.objects.filter(status=Ticket.BOOKED).count(),
        "recent_tickets": recent_tickets,
    }
    return panel_render(request, "panel/dashboard.html", context)


@staff_required
def object_list(request, key):
    section = get_section(key)
    objects = section["model"].objects.all()
    page = Paginator(objects, 12).get_page(request.GET.get("page"))

    rows = []
    for obj in page:
        cells = [getattr(obj, field) for _label, field in section["columns"]]
        rows.append((obj, cells))

    context = {
        "key": key,
        "section": section,
        "page": page,
        "rows": rows,
        "headers": [label for label, _field in section["columns"]],
    }
    return panel_render(request, "panel/object_list.html", context)


@staff_required
def object_form(request, key, pk=None):
    section = get_section(key)
    instance = get_object_or_404(section["model"], pk=pk) if pk else None

    if request.method == "POST":
        form = section["form"](request.POST, request.FILES, instance=instance)
        if form.is_valid():
            form.save()
            messages.success(request, _("Saved."))
            return redirect("panel_list", key=key)
    else:
        form = section["form"](instance=instance)

    context = {"key": key, "section": section, "form": form, "instance": instance}
    return panel_render(request, "panel/object_form.html", context)


@staff_required
def object_delete(request, key, pk):
    section = get_section(key)
    obj = get_object_or_404(section["model"], pk=pk)

    if request.method == "POST":
        obj.delete()
        messages.success(request, _("Deleted."))
        return redirect("panel_list", key=key)

    lookup = BOOKED_LOOKUP.get(key)
    booked = Ticket.objects.filter(status=Ticket.BOOKED, **{lookup: obj}).count() if lookup else 0

    context = {"key": key, "section": section, "obj": obj, "booked": booked}
    return panel_render(request, "panel/object_delete.html", context)
