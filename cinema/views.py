from collections import defaultdict
from datetime import timedelta
from io import BytesIO
import base64
import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Cinema, Genre, Movie, Seat, Showtime, Ticket, Reservation, expire_reservations


MAX_SEATS = 6


# Each image refers to the actual cinema, with attribution shown on the homepage.
# Remote photos require network access; the CSS fallback still works offline.
CINEMA_PHOTOS = {
    'cinemax': ('https://avatars.mds.yandex.net/get-altay/374295/2a0000015b16ad40c0c4dbf43b8231505766/XXXL',
    'Yandex Images',
    ''),
    'halyk': ('https://img.inform.kz/kazinform-photobank/media/2023-10-21/c22e125a-43d9-446e-b5a5-40812920c929.webp', 'Kazinform', 'https://kaz.inform.kz/news/almatida-halyk-imax-kinopark-16-zhana-kinoteatri-ashiladi-7c9127/'),
    'kinoforum': ('https://static.tildacdn.pro/tild3436-6533-4230-a663-666164346236/_2021-07-13_222104.png', 'YESSET', 'https://yesset.kz/works/kt_forum'),
    'lumiera': ('https://lofficiel.kz/media/blog/entries/photos/2016/10/05/ec/5d/ec/ca/ec5decca5ed3d6b8079e2e7e7bacc9f2_1.jpg', "L'Officiel", 'https://lofficiel.kz/blog/2016/10/05/lumiera-novaya-razvlekatelnaya-tochka-na-karte-almaty/'),
}


def home(request):
    # Show a compact selection of four films, not their full descriptions.
    movies = Movie.objects.select_related('genre').prefetch_related('genres').order_by('title_ru')[:4]
    cinemas = []
    for cinema in Cinema.objects.all()[:4]:
        key = cinema.name.lower()
        photo = next((record for name, record in CINEMA_PHOTOS.items() if name in key), None)
        cinemas.append({'cinema': cinema, 'photo': photo})
    return render(request, 'cinema/home.html', {'movies': movies, 'cinemas': cinemas})


def movie_list(request):
    # All filters are read-only. They do not change records in SQLite.
    movies = Movie.objects.select_related('genre').prefetch_related('genres').all()
    query = request.GET.get('q', '').strip()
    genre_id = request.GET.get('genre', '').strip()
    cinema_id = request.GET.get('cinema', '').strip()
    sort = request.GET.get('sort', 'title_asc').strip()

    if query:
        movies = movies.filter(Q(title_ru__icontains=query) | Q(title_en__icontains=query) | Q(title_kk__icontains=query))
    if cinema_id.isdecimal():
        movies = movies.filter(showtimes__hall__cinema_id=int(cinema_id)).distinct()
    else:
        cinema_id = ''
    if genre_id.isdecimal():
        movies = movies.filter(Q(genres__id=int(genre_id)) | Q(genre_id=int(genre_id))).distinct()
    else:
        genre_id = ''

    sort_options = {
        'title_asc': ('title_ru', 'pk'),
        'title_desc': ('-title_ru', 'pk'),
        'year_new': ('-year', 'title_ru'),
        'year_old': ('year', 'title_ru'),
        'duration_short': ('duration', 'title_ru'),
        'duration_long': ('-duration', 'title_ru'),
    }
    if sort not in sort_options:
        sort = 'title_asc'
    movies = movies.order_by(*sort_options[sort])
    return render(request, 'cinema/movie_list.html', {
        'movies': movies,
        'genres': Genre.objects.all().order_by('name_ru'),
        'cinemas': Cinema.objects.all().order_by('name'),
        'selected_cinema': cinema_id,
        'selected_genre': genre_id,
        'selected_sort': sort,
        'search_query': query,
    })


def movie_detail(request, pk):
    movie = get_object_or_404(Movie, pk=pk)
    upcoming = list(Showtime.objects.filter(movie=movie, starts_at__gt=timezone.now())
                    .select_related('hall__cinema').order_by('starts_at'))
    cinema_id = request.GET.get('cinema', '')
    if cinema_id and not cinema_id.isdigit():
        cinema_id = ''
    if cinema_id:
        upcoming = [s for s in upcoming if s.hall.cinema_id == int(cinema_id)]
    cinemas_by_id = {s.hall.cinema_id: s.hall.cinema for s in upcoming}
    dates = sorted({timezone.localtime(s.starts_at).date() for s in upcoming})
    date_param = request.GET.get('date')
    selected_date = next((d for d in dates if d.isoformat() == date_param), dates[0] if dates else None)
    by_cinema = defaultdict(list)
    for show in upcoming:
        if timezone.localtime(show.starts_at).date() == selected_date:
            by_cinema[show.hall.cinema].append(show)
    return render(request, 'cinema/movie_detail.html', {
        'movie': movie, 'cinemas': list(cinemas_by_id.values()),
        'cinema_id': cinema_id, 'dates': dates, 'selected_date': selected_date,
        'by_cinema': dict(by_cinema),
    })


@login_required
def seat_select(request, pk):
    showtime = get_object_or_404(Showtime.objects.select_related('movie', 'hall__cinema'), pk=pk)
    if showtime.is_past:
        messages.error(request, 'This showtime has already started.')
        return redirect('movie_detail', pk=showtime.movie_id)
    taken = showtime.taken_seat_ids()
    rows = []
    for row_num in range(1, showtime.hall.rows_count + 1):
        seats = list(showtime.hall.seats.filter(row=row_num).order_by('number'))
        rows.append({'letter': chr(64 + row_num),
                     'seats': [{'seat': s, 'taken': s.pk in taken} for s in seats]})
    return render(request, 'cinema/seat_select.html', {
        'showtime': showtime, 'rows': rows, 'max_seats': MAX_SEATS,
    })


def _valid_seats(request, showtime):
    ids = request.POST.getlist('seats')
    if not ids or len(ids) > MAX_SEATS or len(ids) != len(set(ids)):
        return None
    if any(not x.isdigit() for x in ids):
        return None
    seats = list(Seat.objects.filter(pk__in=ids, hall=showtime.hall).order_by('row', 'number'))
    if len(seats) != len(ids):
        return None
    return seats


@login_required
def booking_confirm(request, pk):
    """Reserve seats now and redirect to ten-minute checkout; POST-only."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    showtime = get_object_or_404(Showtime.objects.select_related('movie', 'hall__cinema'), pk=pk)
    seats = _valid_seats(request, showtime)
    if showtime.is_past or not seats:
        messages.error(request, 'Choose valid seats for an upcoming showtime.')
        return redirect('seat_select', pk=pk)
    expire_reservations()
    try:
        with transaction.atomic():
            if Ticket.objects.filter(showtime=showtime, seat__in=seats,
                                     status__in=[Ticket.BOOKED, Ticket.PENDING]).exists():
                raise IntegrityError('Already reserved')
            order = Reservation.objects.create(
                user=request.user, showtime=showtime,
                expires_at=timezone.now() + timedelta(minutes=10))
            Ticket.objects.bulk_create([
                Ticket(user=request.user, reservation=order, showtime=showtime,
                       seat=seat, price=showtime.price, status=Ticket.PENDING)
                for seat in seats
            ])
    except IntegrityError:
        messages.error(request, 'One of the seats is no longer free. Choose again.')
        return redirect('seat_select', pk=pk)
    return redirect('checkout', order_id=order.pk)


def _payment_qr(order):
    """QR contains only a demo order reference, not a real banking payment URL."""
    import qrcode
    from qrcode.image.svg import SvgImage
    img = qrcode.make(f'CINEMAGO DEMO PAYMENT | ORDER {order.pk} | {order.total} KZT',
                      image_factory=SvgImage, box_size=8, border=2)
    buffer = BytesIO()
    img.save(buffer)
    return 'data:image/svg+xml;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


@login_required
def checkout(request, order_id):
    expire_reservations()
    order = get_object_or_404(Reservation.objects.select_related('showtime__movie', 'showtime__hall__cinema'),
                              pk=order_id, user=request.user)
    if order.status == 'paid':
        return redirect('my_tickets')
    if order.status != 'pending':
        return render(request, 'cinema/checkout_expired.html', {'order': order})
    return render(request, 'cinema/booking_confirm.html', {
        'order': order, 'showtime': order.showtime,
        'seats': [t.seat for t in order.tickets.select_related('seat').all()],
        'total': order.total, 'qr_data': _payment_qr(order),
        'expires_iso': order.expires_at.isoformat(),
    })


@login_required
def booking_create(request, pk):
    """Complete demo payment for an owned, unexpired reservation."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    order_id = request.POST.get('reservation', '')
    try:
        order_id = uuid.UUID(order_id)
    except (ValueError, TypeError, AttributeError):
        messages.error(request, 'Invalid reservation.')
        return redirect('my_tickets')
    method = request.POST.get('payment_method', '')
    if method not in ('card', 'qr'):
        messages.error(request, 'Select a demo payment method.')
        return redirect('seat_select', pk=pk)
    # An order token alone never authorizes payment; ownership is checked in SQL.
    try:
        with transaction.atomic():
            expire_reservations()
            order = get_object_or_404(Reservation.objects.select_for_update(),
                                      pk=order_id, user=request.user, showtime_id=pk)
            if order.status != 'pending' or order.expires_at <= timezone.now() or order.showtime.is_past:
                messages.error(request, 'The ten-minute reservation has expired.')
                return redirect('my_tickets')
            order.status = 'paid'
            order.payment_method = method
            order.paid_at = timezone.now()
            order.save(update_fields=['status','payment_method','paid_at'])
            Ticket.objects.filter(reservation=order, status=Ticket.PENDING).update(status=Ticket.BOOKED)
    except (ValueError, TypeError):
        messages.error(request, 'Invalid reservation.')
        return redirect('my_tickets')
    messages.success(request, 'Demo payment confirmed! Your tickets are in My Tickets.')
    return redirect('my_tickets')


@login_required
def my_tickets(request):
    expire_reservations()
    qs = Ticket.objects.filter(user=request.user).select_related(
        'reservation','showtime__movie','showtime__hall__cinema','seat')
    now = timezone.now()
    return render(request, 'cinema/my_tickets.html', {
        'upcoming': [t for t in qs if t.status == Ticket.BOOKED and t.showtime.starts_at > now],
        'past': [t for t in qs if t.status == Ticket.BOOKED and t.showtime.starts_at <= now],
        'pending': [t for t in qs if t.status == Ticket.PENDING],
        'cancelled': [t for t in qs if t.status == Ticket.CANCELLED],
        'refunded': [t for t in qs if t.status == Ticket.REFUNDED],
    })


@login_required
def ticket_cancel(request, pk):
    """Cancel an unpaid seat hold; paid tickets are not cancellable here."""
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    expire_reservations()
    with transaction.atomic():
        ticket = get_object_or_404(Ticket.objects.select_for_update(), pk=pk, user=request.user)
        if ticket.status == Ticket.PENDING and ticket.reservation_id:
            order = Reservation.objects.select_for_update().get(pk=ticket.reservation_id)
            if order.status == 'pending' and order.expires_at > timezone.now():
                ticket.status = Ticket.CANCELLED
                ticket.save(update_fields=['status'])
                if not order.tickets.filter(status=Ticket.PENDING).exists():
                    order.status = 'cancelled'
                    order.save(update_fields=['status'])
                messages.success(request, 'Unpaid booking cancelled.')
        elif ticket.status == Ticket.BOOKED:
            messages.info(request, 'Paid tickets cannot be cancelled as unpaid bookings.')
    return redirect('my_tickets')

@login_required
def ticket_refund(request, pk):
    """Demo refund for a paid ticket before the showtime."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    with transaction.atomic():
        ticket = get_object_or_404(
            Ticket.objects.select_for_update().select_related(
                "reservation", "showtime"
            ),
            pk=pk,
            user=request.user,
        )

        if (
            ticket.status != Ticket.BOOKED
            or ticket.reservation is None
            or ticket.reservation.status != "paid"
            or ticket.showtime.starts_at <= timezone.now()
        ):
            messages.error(request, "This ticket cannot be refunded.")
            return redirect("my_tickets")

        ticket.status = Ticket.REFUNDED
        ticket.save(update_fields=["status"])

    messages.success(request, "Ticket refunded successfully (demo).")
    return redirect("my_tickets")
@login_required
def ticket_qr(request, pk):
    """Owner-only PNG. The QR carries a signed, limited ticket reference."""
    import qrcode
    from django.core import signing
    from django.http import HttpResponse
    from django.urls import reverse
    from urllib.parse import urlencode

    ticket = get_object_or_404(Ticket, pk=pk, user=request.user, status=Ticket.BOOKED)
    token = signing.dumps({'pk': ticket.pk, 'code': ticket.code}, salt='cinemago-ticket-v1')
    verify_url = request.build_absolute_uri(reverse('verify_ticket_qr')) + '?' + urlencode({'token':token})
    buffer = BytesIO()
    qrcode.make(verify_url, box_size=7, border=3).save(buffer, format='PNG')
    response = HttpResponse(buffer.getvalue(), content_type='image/png')
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


def verify_ticket_qr(request):
    """Demo ticket validation: no customer identity or private booking data leaked."""
    from django.core import signing
    token = request.GET.get('token', '')
    try:
        data = signing.loads(token, salt='cinemago-ticket-v1')
        ticket = Ticket.objects.filter(pk=data.get('pk'), code=data.get('code'), status=Ticket.BOOKED).first()
    except (signing.BadSignature, TypeError, ValueError, AttributeError):
        ticket = None
    valid = ticket is not None
    return render(request, 'cinema/ticket_verify.html', {'valid': valid}, status=200 if valid else 404)
