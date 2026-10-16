from django import forms
from accounts.forms import INPUT_CLASS
from .models import ContactMessage


class ContactForm(forms.ModelForm):
    class Meta:
        model = ContactMessage
        fields = ('name', 'email', 'subject', 'message')
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'subject': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'email': forms.EmailInput(attrs={'class': INPUT_CLASS}),
            'message': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 5}),
        }
