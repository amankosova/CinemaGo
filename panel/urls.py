from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="panel"),
    path("<str:key>/", views.object_list, name="panel_list"),
    path("<str:key>/new/", views.object_form, name="panel_create"),
    path("<str:key>/<int:pk>/edit/", views.object_form, name="panel_edit"),
    path("<str:key>/<int:pk>/delete/", views.object_delete, name="panel_delete"),
]
