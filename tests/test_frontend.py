
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path

import pytest
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parent.parent

QA_USER = "qa_user"
QA_PASS = "QaPass!2026x9"

MOVIES = json.loads(
    (ROOT / "cinema" / "data" / "movies_15_i18n.json").read_text(encoding="utf-8")
)
TOTAL_MOVIES = len(MOVIES)


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url(tmp_path_factory):
    db_file = tmp_path_factory.mktemp("db") / "frontend_test.sqlite3"
    settings_dir = tmp_path_factory.mktemp("settings")
    (settings_dir / "cinemago_browser_settings.py").write_text(
        "from config.settings import *\n"
        "import os\n"
        "DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', "
        "'NAME': os.environ['CINEMAGO_TEST_DB']}}\n"
        "MEDIA_ROOT = os.environ['CINEMAGO_TEST_MEDIA']\n",
        encoding="utf-8",
    )
    env = {
        **os.environ,
        "PYTHONPATH": str(settings_dir) + os.pathsep + str(ROOT) + os.pathsep + os.environ.get("PYTHONPATH", ""),
        "CINEMAGO_TEST_MEDIA": str(tmp_path_factory.mktemp("media")),
        "DJANGO_SETTINGS_MODULE": "cinemago_browser_settings",
        "CINEMAGO_TEST_DB": str(db_file),
        "PYTHONIOENCODING": "utf-8",
    }

    def manage(*args):
        subprocess.run(
            [sys.executable, "manage.py", *args],
            cwd=ROOT, env=env, check=True, capture_output=True,
        )

    manage("migrate", "--noinput")
    manage("seed_cinemago")
    manage(
        "shell", "-c",
        "from django.contrib.auth.models import User;"
        f"User.objects.create_user('{QA_USER}', 'qa@example.com', '{QA_PASS}')",
    )

    port = _free_port()
    log = open(tmp_path_factory.mktemp("log") / "server.log", "w+", encoding="utf-8")
    server = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", f"127.0.0.1:{port}", "--noreload"],
        cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(120):
        try:
            urllib.request.urlopen(url + "/", timeout=2)
            break
        except Exception:
            if server.poll() is not None:
                log.seek(0)
                raise RuntimeError("Django server did not start:\n" + log.read())
            time.sleep(0.5)
    else:
        server.kill()
        raise RuntimeError("Django server start timeout")

    yield url
    server.terminate()
    try:
        server.wait(timeout=10)
    except subprocess.TimeoutExpired:
        server.kill()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as p:
        b = p.chromium.launch(
            headless=os.environ.get("HEADED") != "1",
            slow_mo=int(os.environ.get("SLOWMO", "0")),
        )
        yield b
        b.close()


@pytest.fixture()
def page(browser, base_url):
    context = browser.new_context(
        base_url=base_url, locale="en-US", viewport={"width": 1280, "height": 900}
    )
    context.set_default_timeout(10_000)
    pg = context.new_page()
    yield pg
    context.close()


def cards(page):
    return page.locator(".poster-grid .movie-card")


def apply_filters(page):
    page.get_by_role("button", name="Apply").click()


def login(page, username=QA_USER, password=QA_PASS):
    page.goto("/accounts/login/")
    page.locator("input[name=username]").fill(username)
    page.locator("input[name=password]").fill(password)
    page.locator("main form button[type=submit]").first.click()


def open_movie(page, title_en):
    page.goto("/movies/")
    page.locator(".poster-tile", has=page.locator(".poster-title", has_text=title_en)).first.click()
    expect(page.locator("h1")).to_have_text(title_en)


def open_seat_map(page, title_en):
    open_movie(page, title_en)
    page.locator("a.time-btn").first.click()
    expect(page).to_have_url(re.compile(r"/showtimes/\d+/seats/"))
    expect(page.locator("label.seat").first).to_be_visible()


def showtime_url(page, title_en):
    open_movie(page, title_en)
    return page.locator("a.time-btn").first.get_attribute("href")


def test_tc01_home_page_content(page):
    page.goto("/")
    expect(page).to_have_title(re.compile("CinemaGo"))
    expect(page.locator("h1")).to_have_text("Your seat is waiting.")
    expect(page.get_by_role("link", name="Explore movies")).to_be_visible()
    expect(page.locator(".home-poster-grid .movie-card")).to_have_count(4)
    expect(page.locator(".cinema-home-card")).to_have_count(4)
    expect(page.locator(".step-home")).to_have_count(3)
    expect(page.get_by_role("link", name="Log in")).to_be_visible()
    expect(page.get_by_role("link", name="Sign up")).to_be_visible()


def test_tc02_header_navigation_and_explore_button(page):
    page.goto("/")
    nav = page.locator(".main-nav")
    expect(nav.get_by_role("link", name="Home")).to_have_class(re.compile("active"))
    nav.get_by_role("link", name="Movies").click()
    expect(page).to_have_url(re.compile(r"/movies/$"))
    expect(page.locator("h1")).to_have_text("Movies")
    expect(page.locator(".main-nav").get_by_role("link", name="Movies")).to_have_class(re.compile("active"))
    page.locator(".brand").click()
    expect(page).to_have_url(re.compile(r"/$"))
    page.get_by_role("link", name="Explore movies").click()
    expect(page).to_have_url(re.compile(r"/movies/$"))


def test_tc03_catalogue_lists_all_movies(page):
    page.goto("/movies/")
    expect(cards(page)).to_have_count(TOTAL_MOVIES)
    expect(page.locator(".movie-filter-count")).to_contain_text(str(TOTAL_MOVIES))
    expect(page.locator(".poster-grid .poster-tile img")).to_have_count(TOTAL_MOVIES)
    for title in page.locator(".poster-title").all_inner_texts():
        assert title.strip()


def test_tc04_search_by_title(page):
    page.goto("/movies/")
    page.get_by_label("Search movies").fill("Dune")
    apply_filters(page)
    expect(page).to_have_url(re.compile(r"q=Dune"))
    expect(cards(page)).to_have_count(1)
    expect(page.locator(".poster-title")).to_have_text("Dune: Part Three")
    expect(page.locator(".movie-filter-count")).to_contain_text("1")


def test_tc05_filter_by_genre(page):
    expected = sum(
        1 for m in MOVIES if "Comedy" in [g["en"] for g in m["genres_localized"]]
    )
    page.goto("/movies/")
    page.get_by_label("Genre").select_option(label="Comedy")
    apply_filters(page)
    expect(page).to_have_url(re.compile(r"genre=\d+"))
    expect(cards(page)).to_have_count(expected)
    assert 0 < expected < TOTAL_MOVIES
    expect(page.get_by_label("Genre").locator("option:checked")).to_have_text("Comedy")
    for meta in page.locator(".poster-meta span:first-child").all_inner_texts():
        assert "Comedy" in meta


def test_tc06_sort_by_duration(page):
    def durations():
        texts = page.locator(".poster-meta span:last-child").all_inner_texts()
        return [int(re.search(r"\d+", t).group()) for t in texts]

    page.goto("/movies/")
    page.get_by_label("Sort by").select_option("duration_short")
    apply_filters(page)
    expect(cards(page)).to_have_count(TOTAL_MOVIES)
    asc = durations()
    assert asc == sorted(asc)
    assert asc[0] == min(m["duration_minutes"] for m in MOVIES)

    page.get_by_label("Sort by").select_option("duration_long")
    apply_filters(page)
    expect(cards(page)).to_have_count(TOTAL_MOVIES)
    desc = durations()
    assert desc == sorted(desc, reverse=True)
    assert desc[0] == max(m["duration_minutes"] for m in MOVIES)


def test_tc07_reset_clears_filters(page):
    page.goto("/movies/")
    page.get_by_label("Search movies").fill("Dune")
    apply_filters(page)
    expect(cards(page)).to_have_count(1)
    page.get_by_role("link", name="Reset").click()
    expect(page).to_have_url(re.compile(r"/movies/$"))
    expect(cards(page)).to_have_count(TOTAL_MOVIES)
    expect(page.get_by_label("Search movies")).to_have_value("")


def test_tc08_empty_search_result(page):
    page.goto("/movies/")
    page.get_by_label("Search movies").fill("zzzz-no-such-movie")
    apply_filters(page)
    expect(cards(page)).to_have_count(0)
    expect(page.locator(".movie-filter-count")).to_contain_text("0")
    expect(page.get_by_text("No movies found. Try other filters.")).to_be_visible()


def test_tc09_movie_details_page(page):
    open_movie(page, "Qudiret")
    expect(page).to_have_url(re.compile(r"/movies/\d+/$"))
    facts = page.locator(".facts")
    expect(facts).to_contain_text("76 min")
    expect(facts).to_contain_text("2026")
    expect(page.locator(".movie-head img").first).to_be_visible()
    expect(page.locator(".movie-desc")).not_to_be_empty()
    expect(page.get_by_role("heading", name="Choose a showtime")).to_be_visible()
    assert page.locator(".date-chip").count() >= 1
    first_time = page.locator("a.time-btn").first
    expect(first_time).to_be_visible()
    expect(first_time).to_contain_text("₸")
    expect(first_time).to_have_attribute("href", re.compile(r"/showtimes/\d+/seats/"))


def test_tc10_language_switcher_ru(page):
    page.goto("/movies/")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.locator(".lang-menu summary").click()
    page.get_by_role("button", name="Русский").click()
    expect(page.locator("html")).to_have_attribute("lang", "ru")
    expect(page.locator("h1")).to_have_text("Фильмы")
    expect(page.locator(".main-nav").get_by_role("link", name="Главная")).to_be_visible()
    expect(page.get_by_role("link", name="Войти")).to_be_visible()
    expect(page).to_have_url(re.compile(r"/movies/$"))
    expect(page.locator(".poster-title", has_text="Дюна")).to_have_count(1)


def test_tc11_guest_is_redirected_to_login(page):
    seats_url = showtime_url(page, "Dune: Part Three")
    page.goto(seats_url)
    expect(page).to_have_url(re.compile(r"/accounts/login/\?next=.*seats"))
    expect(page.locator("h1")).to_have_text("Welcome back")
    page.goto("/my-tickets/")
    expect(page).to_have_url(re.compile(r"/accounts/login/\?next=.*my-tickets"))


def test_tc12_registration_validation_and_success(page):
    username = "user_" + uuid.uuid4().hex[:8]
    password = "Zq9!vT4#rLm2"

    page.goto("/accounts/register/")
    page.locator("#id_username").fill(username)
    page.locator("#id_email").fill(f"{username}@example.com")
    page.locator("#id_password1").fill(password)
    page.locator("#id_password2").fill("Different!Pass-1")
    page.locator("main form button[type=submit]").first.click()
    expect(page).to_have_url(re.compile(r"/accounts/register/$"))
    expect(page.locator(".errorlist").first).to_be_visible()

    page.locator("#id_password1").fill(password)
    page.locator("#id_password2").fill(password)
    page.locator("main form button[type=submit]").first.click()
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.locator("body")).to_contain_text("Account created successfully.")
    expect(page.get_by_role("button", name="Log out")).to_be_visible()

    page.goto("/accounts/profile/")
    expect(page.locator(".profile-details")).to_contain_text(username)
    expect(page.locator(".profile-details")).to_contain_text(f"{username}@example.com")


def test_tc13_login_error_success_and_logout(page):
    login(page, "nobody_" + uuid.uuid4().hex[:6], "WrongPass!123")
    expect(page).to_have_url(re.compile(r"/accounts/login/"))
    expect(page.locator(".login-error")).to_contain_text("Incorrect username or password")
    expect(page.get_by_role("button", name="Log out")).to_have_count(0)

    login(page)
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page.get_by_role("link", name="My Tickets")).to_be_visible()
    expect(page.get_by_role("link", name="Profile")).to_be_visible()
    expect(page.get_by_role("link", name="Log in")).to_have_count(0)

    page.get_by_role("button", name="Log out").click()
    expect(page.get_by_role("link", name="Log in")).to_be_visible()
    expect(page.get_by_role("link", name="My Tickets")).to_have_count(0)


def test_tc14_seat_map_selection_total_and_limit(page):
    login(page)
    open_seat_map(page, "Bauyr")

    form = page.locator("[data-seat-form]")
    price = int(form.get_attribute("data-price"))
    max_seats = int(form.get_attribute("data-max"))
    assert max_seats == 6

    seats = page.locator("label.seat")
    chosen, total = page.locator("#chosen"), page.locator("#total")
    button, limit = page.locator("#continue"), page.locator("#limit-note")

    expect(button).to_be_disabled()
    expect(chosen).to_have_text("—")
    expect(total).to_have_text("0 ₸")

    seats.nth(0).click()
    expect(chosen).to_have_text("A1")
    expect(total).to_have_text(f"{price} ₸")
    expect(button).to_be_enabled()
    seats.nth(1).click()
    expect(chosen).to_have_text("A1, A2")
    expect(total).to_have_text(f"{2 * price} ₸")

    seats.nth(0).click()
    expect(chosen).to_have_text("A2")
    expect(total).to_have_text(f"{price} ₸")

    seats.nth(1).click()
    expect(button).to_be_disabled()

    for i in range(max_seats):
        seats.nth(i).click()
    expect(page.locator("[data-seat-form] input[type=checkbox]:checked")).to_have_count(max_seats)
    expect(limit).to_be_hidden()
    seats.nth(max_seats).click()
    expect(limit).to_be_visible()
    expect(limit).to_contain_text("up to 6 seats")
    expect(page.locator("[data-seat-form] input[type=checkbox]:checked")).to_have_count(max_seats)
    expect(total).to_have_text(f"{max_seats * price} ₸")


def test_tc15_checkout_payment_and_ticket(page):
    login(page)
    open_seat_map(page, "Shymyr")
    price = int(page.locator("[data-seat-form]").get_attribute("data-price"))

    seats = page.locator("label.seat")
    seats.nth(0).click()
    seats.nth(1).click()
    page.locator("#continue").click()

    expect(page).to_have_url(re.compile(r"/checkout/[0-9a-f-]{36}/$"))
    expect(page.locator("#checkout-clock")).to_have_text(re.compile(r"^(0\d|10):\d\d$"))
    expect(page.locator(".checkout-summary-total")).to_contain_text(f"{2 * price} ₸")
    seat_text = page.locator(".checkout-summary").inner_text()
    assert "A1" in seat_text
    assert "A2" in seat_text

    expect(page.locator("#card-panel")).to_be_visible()
    expect(page.locator("#qr-panel")).to_be_hidden()
    page.locator("label[data-method=qr]").click()
    expect(page.locator("#qr-panel")).to_be_visible()
    expect(page.locator("#qr-panel img")).to_be_visible()
    expect(page.locator("#card-panel")).to_be_hidden()
    page.locator("label[data-method=card]").click()
    expect(page.locator("#card-panel")).to_be_visible()

    page.locator("#pay-submit").click()
    expect(page).to_have_url(re.compile(r"/my-tickets/$"))
    expect(page.locator("body")).to_contain_text("Demo payment confirmed")
    expect(page.get_by_role("heading", name="Upcoming")).to_be_visible()
    tickets = page.locator("article.ticket")
    expect(tickets).to_have_count(2)
    expect(tickets.first).to_contain_text("Shymyr")
    expect(tickets.first.locator(".tag.ok")).to_have_text("Paid")
    expect(tickets.locator(".tag.ok")).to_have_count(2)
    labels = sorted(page.locator(".seat-big").all_inner_texts())
    assert labels == ["A1", "A2"]
