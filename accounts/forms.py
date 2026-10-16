from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User, Address

INPUT_CLASS = ('w-full rounded-lg border border-gray-300 px-4 py-2 '
               'focus:border-orange-500 focus:ring-1 focus:ring-orange-500 outline-none')


class StyledFormMixin:
    """Adds Tailwind classes to every field so templates stay short."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.RadioSelect)):
                field.widget.attrs['class'] = INPUT_CLASS


class RegisterForm(StyledFormMixin, UserCreationForm):
    # Password rules come from AUTH_PASSWORD_VALIDATORS in settings.py
    class Meta:
        model = User
        fields = ('username', 'email', 'phone')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class LoginForm(StyledFormMixin, AuthenticationForm):
    pass


class ProfileForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('This email is used by another account.')
        return email


class AddressForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = Address
        fields = ('full_name', 'phone', 'line1', 'line2', 'city',
                  'state', 'pincode', 'is_default')
