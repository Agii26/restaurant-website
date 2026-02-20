from django import forms
from .models import Reservation
import datetime


class ReservationForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'min': str(datetime.date.today())}),
        label="Date"
    )
    time = forms.TimeField(
        widget=forms.TimeInput(attrs={'type': 'time'}),
        label="Time"
    )

    class Meta:
        model = Reservation
        fields = ['name', 'email', 'phone', 'date', 'time', 'number_of_guests', 'special_request']
        labels = {
            'name': 'Full Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'number_of_guests': 'Number of Guests',
            'special_request': 'Special Requests',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Juan dela Cruz'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+63 912 345 6789'}),
            'number_of_guests': forms.NumberInput(attrs={'min': 1, 'max': 50}),
            'special_request': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Allergies, occasion, seating preferences...'}),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date and date < datetime.date.today():
            raise forms.ValidationError("Reservation date cannot be in the past.")
        return date

    def clean_number_of_guests(self):
        guests = self.cleaned_data.get('number_of_guests')
        if guests and guests < 1:
            raise forms.ValidationError("Must have at least 1 guest.")
        if guests and guests > 50:
            raise forms.ValidationError("For groups over 50 please call us directly.")
        return guests