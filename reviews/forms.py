from django import forms
from accounts.forms import INPUT_CLASS
from .models import Review


class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(choices=[(i, f'{i} ★') for i in range(5, 0, -1)],
                               widget=forms.Select(attrs={'class': INPUT_CLASS}))

    class Meta:
        model = Review
        fields = ('rating', 'title', 'comment')
        widgets = {
            'title': forms.TextInput(attrs={'class': INPUT_CLASS}),
            'comment': forms.Textarea(attrs={'class': INPUT_CLASS, 'rows': 3}),
        }
