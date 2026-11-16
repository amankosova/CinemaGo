from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.db.models
import uuid

class Migration(migrations.Migration):
    dependencies = [('cinema', '0002_movie_details_i18n'), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name='Reservation',
            fields=[
                ('id', models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, serialize=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('status', models.CharField(max_length=12, default='pending', choices=[('pending','Pending payment'),('paid','Paid (demo)'),('expired','Expired'),('cancelled','Cancelled')])),
                ('payment_method', models.CharField(max_length=12, blank=True, choices=[('card','Demo card'),('qr','Demo QR')])),
                ('paid_at', models.DateTimeField(null=True, blank=True)),
                ('showtime', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to='cinema.showtime')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reservations', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(model_name='ticket', name='reservation',
            field=models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tickets', to='cinema.reservation')),
        migrations.AlterField(model_name='ticket', name='status',
            field=models.CharField(max_length=10, choices=[('pending','Pending payment'),('booked','Booked'),('cancelled','Cancelled')], default='booked')),
        migrations.RemoveConstraint(model_name='ticket', name='one_active_ticket_per_seat'),
        migrations.AddConstraint(model_name='ticket', constraint=models.UniqueConstraint(
            fields=('showtime','seat'), condition=django.db.models.Q(status__in=['booked','pending']), name='one_active_ticket_per_seat')),
    ]
