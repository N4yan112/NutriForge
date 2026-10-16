from django.shortcuts import render

from products.models import Product
from .forms import RecommendForm


def recommend(request):
    """Rule-based recommendation: plain database filters + a simple score. No AI/ML."""
    form = RecommendForm(request.GET or None)
    results = None

    if request.GET and form.is_valid():
        d = form.cleaned_data
        products = Product.objects.filter(is_active=True, stock__gt=0,
                                          sale_price__lte=d['budget']).exclude(product_type='accessory')

        # Rule 1: diet.  Vegan -> vegan only.  Vegetarian -> vegan + vegetarian.
        if d['diet'] == 'vegan':
            products = products.filter(dietary_preference='vegan')
        elif d['diet'] == 'vegetarian':
            products = products.filter(dietary_preference__in=['vegan', 'vegetarian'])

        # Rule 2: experience level (products marked "all levels" suit everyone)
        products = products.filter(suitable_level__in=['all', d['level']])

        # Rule 3: must support the chosen goal
        products = products.filter(goals=d['goal'])

        # Rule 4: preferred type
        if d['supplement_type'] != 'any':
            products = products.filter(product_type=d['supplement_type'])

        # Simple scoring: best sellers and higher ratings come first
        scored = []
        for p in products.select_related('brand', 'category').distinct():
            score = float(p.avg_rating) + (2 if p.is_best_seller else 0) + min(p.sold_count / 100, 2)
            scored.append((score, p))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        results = [p for _, p in scored[:8]]

    return render(request, 'recommendations/recommend.html', {'form': form, 'results': results})
