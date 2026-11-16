"""BUG-002 (reservations): a confirmation page is only for the person who booked."""
import datetime

from django.test import Client, TestCase
from django.urls import reverse

from reservations.models import Reservation


def valid_booking(**overrides):
    data = {"name": "Rita Reyes", "email": "rita@example.com", "phone": "+639171112222",
            "date": (datetime.date.today() + datetime.timedelta(days=3)).isoformat(),
            "time": "19:00", "number_of_guests": 4, "special_request": "", "occasion": ""}
    data.update(overrides)
    return data


class ReservationConfirmationAccessTests(TestCase):
    def book(self, client):
        response = client.post(reverse("reservations:reservation"), valid_booking())
        return Reservation.objects.latest("id"), response

    def test_the_person_who_booked_sees_the_confirmation(self):
        reservation, response = self.book(self.client)
        self.assertRedirects(response, reverse("reservations:confirmation", args=[reservation.pk]),
                             fetch_redirect_response=False)
        self.assertEqual(self.client.get(response["Location"]).status_code, 200)

    def test_a_stranger_cannot_open_someone_elses_confirmation(self):
        reservation, _ = self.book(self.client)
        response = Client().get(reverse("reservations:confirmation", args=[reservation.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertNotContains(response, "rita@example.com", status_code=404)

    def test_counting_up_from_your_own_booking_reveals_nothing(self):
        mine, _ = self.book(self.client)
        other = Reservation.objects.create(name="Other Person", email="other@example.com",
                                           phone="+639170001111", date=datetime.date.today(),
                                           time=datetime.time(18, 0), number_of_guests=2)
        self.assertEqual(self.client.get(reverse("reservations:confirmation", args=[other.pk])).status_code, 404)
