from django.shortcuts import render


def home(request):
    return render(request, "cinema/home.html")


def movie_list(request):
    return render(request, "cinema/movie_list.html")
