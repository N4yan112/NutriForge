from django import forms
from accounts.forms import INPUT_CLASS
from products.models import Goal, Product


class RecommendForm(forms.Form):
    LEVELS = [('beginner', 'Beginner'), ('intermediate', 'Intermediate'), ('advanced', 'Advanced')]
    DIETS = [('any', 'No preference'), ('vegetarian', 'Vegetarian'), ('vegan', 'Vegan')]
    TYPES = [('any', 'Any type')] + [t for t in Product.TYPE_CHOICES if t[0] != 'accessory']

    goal = forms.ModelChoiceField(queryset=Goal.objects.all(), empty_label=None,
                                  label='Fitness goal')
    budget = forms.IntegerField(min_value=100, max_value=100000, label='Budget (₹)',
                                widget=forms.NumberInput(attrs={'placeholder': 'e.g. 2000'}))
    level = forms.ChoiceField(choices=LEVELS, label='Experience level')
    diet = forms.ChoiceField(choices=DIETS, label='Dietary preference')
    supplement_type = forms.ChoiceField(choices=TYPES, label='Preferred supplement type')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs['class'] = INPUT_CLASS
