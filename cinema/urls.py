from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('movies/', views.movie_list, name='movie_list'),
    path('movies/<int:pk>/', views.movie_detail, name='movie_detail'),
    path('showtimes/<int:pk>/seats/', views.seat_select, name='seat_select'),
    path('showtimes/<int:pk>/confirm/', views.booking_confirm, name='booking_confirm'),
    path('showtimes/<int:pk>/book/', views.booking_create, name='booking_create'),
    path('checkout/<uuid:order_id>/', views.checkout, name='checkout'),
    path('my-tickets/', views.my_tickets, name='my_tickets'),
    path('tickets/<int:pk>/qr/', views.ticket_qr, name='ticket_qr'),
    path('tickets/verify/', views.verify_ticket_qr, name='verify_ticket_qr'),
    path('tickets/<int:pk>/cancel/', views.ticket_cancel, name='ticket_cancel'),
    path('tickets/<int:pk>/refund/', views.ticket_refund, name='ticket_refund'),
]
