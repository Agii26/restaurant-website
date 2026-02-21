from django import forms
from .models import Order
from menu.models import AddOn
import datetime


class AddToCartForm(forms.Form):
    quantity = forms.IntegerField(min_value=1, max_value=20, initial=1)
    addon = forms.ModelChoiceField(queryset=AddOn.objects.none(), required=False, label="Add-on (optional)")

    def __init__(self, *args, **kwargs):
        menu_item = kwargs.pop('menu_item', None)
        super().__init__(*args, **kwargs)
        if menu_item:
            self.fields['addon'].queryset = menu_item.addons.all()
            if not menu_item.addons.exists():
                self.fields.pop('addon')


class CheckoutForm(forms.ModelForm):
    pickup_time = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        label="Preferred Pickup Time",
        input_formats=['%Y-%m-%dT%H:%M'],
    )

    class Meta:
        model = Order
        fields = ['name', 'email', 'phone', 'pickup_time', 'order_notes']
        labels = {
            'name': 'Full Name',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'order_notes': 'Special Instructions',
        }
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'Juan dela Cruz'}),
            'email': forms.EmailInput(attrs={'placeholder': 'you@example.com'}),
            'phone': forms.TextInput(attrs={'placeholder': '+63 912 345 6789'}),
            'order_notes': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Allergies, special prep requests...'}),
        }

    def clean_pickup_time(self):
        from django.utils import timezone
        pickup_time = self.cleaned_data.get('pickup_time')
        if pickup_time and pickup_time < timezone.now():
            raise forms.ValidationError("Pickup time cannot be in the past.")
        return pickup_time


class PromoCodeForm(forms.Form):
    promo_code = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={'placeholder': 'Enter promo code'}),
        label=""
    )