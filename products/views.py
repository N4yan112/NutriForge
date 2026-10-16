from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render

from reviews.forms import ReviewForm
from wishlist.models import Wishlist
from .models import Brand, Category, Product

SORT_OPTIONS = {
    'price_asc': ('Price: Low to High', 'sale_price'),
    'price_desc': ('Price: High to Low', '-sale_price'),
    'rating': ('Rating', '-avg_rating'),
    'newest': ('Newest', '-created_at'),
    'popular': ('Popular', '-sold_count'),
}


def search_products(qs, q):
    """Search by product name, brand, category or supplement type."""
    q = q.strip()
    if not q:
        return qs
    # Match a type label too, e.g. "capsule" -> product_type 'capsule'
    type_keys = [key for key, label in Product.TYPE_CHOICES if q.lower() in label.lower()]
    return qs.filter(
        Q(name__icontains=q) | Q(brand__name__icontains=q) |
        Q(category__name__icontains=q) | Q(product_type__in=type_keys) |
        Q(description__icontains=q)
    ).distinct()


def _to_decimal(value):
    try:
        return Decimal(value)
    except (InvalidOperation, TypeError):
        return None


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('brand', 'category')
    g = request.GET

    products = search_products(products, g.get('q', ''))
    if g.get('category'):
        products = products.filter(category__slug=g['category'])
    if g.get('brand'):
        products = products.filter(brand__slug=g['brand'])
    if g.get('diet'):
        products = products.filter(dietary_preference=g['diet'])
    if g.get('type'):
        products = products.filter(product_type=g['type'])
    if g.get('rating') in ('1', '2', '3', '4'):
        products = products.filter(avg_rating__gte=int(g['rating']))
    if _to_decimal(g.get('min_price')) is not None:
        products = products.filter(sale_price__gte=_to_decimal(g['min_price']))
    if _to_decimal(g.get('max_price')) is not None:
        products = products.filter(sale_price__lte=_to_decimal(g['max_price']))
    if g.get('offers') == '1':
        products = products.filter(discount_percent__gt=0)

    sort = g.get('sort', 'newest')
    if sort not in SORT_OPTIONS:
        sort = 'newest'
    products = products.order_by(SORT_OPTIONS[sort][1], 'id')

    page = Paginator(products, 12).get_page(g.get('page'))
    params = g.copy()
    params.pop('page', None)

    return render(request, 'products/list.html', {
        'page': page,
        'categories': Category.objects.all(),
        'brands': Brand.objects.all(),
        'type_choices': Product.TYPE_CHOICES,
        'diet_choices': Product.DIET_CHOICES,
        'sort_options': [(k, v[0]) for k, v in SORT_OPTIONS.items()],
        'current': {'q': g.get('q', ''), 'category': g.get('category', ''),
                    'brand': g.get('brand', ''), 'diet': g.get('diet', ''),
                    'type': g.get('type', ''), 'rating': g.get('rating', ''),
                    'min_price': g.get('min_price', ''), 'max_price': g.get('max_price', ''),
                    'sort': sort, 'offers': g.get('offers', '')},
        'querystring': params.urlencode(),
    })


def search_suggest(request):
    """Small JSON endpoint used by the live-search dropdown."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})
    qs = search_products(Product.objects.filter(is_active=True), q)[:6]
    return JsonResponse({'results': [
        {'name': p.name, 'url': p.get_absolute_url(), 'price': int(p.sale_price)} for p in qs]})


def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related('brand', 'category'),
                                slug=slug, is_active=True)
    related = Product.objects.filter(category=product.category, is_active=True)\
        .exclude(pk=product.pk)[:4]
    reviews = product.reviews.filter(is_approved=True).select_related('user')
    in_wishlist = request.user.is_authenticated and \
        Wishlist.objects.filter(user=request.user, product=product).exists()
    user_review = None
    if request.user.is_authenticated:
        user_review = product.reviews.filter(user=request.user).first()
    images = [product.image.url] if product.image else []
    images += [g.image.url for g in product.gallery.all()]
    return render(request, 'products/detail.html', {
        'product': product,
        'images': images,
        'variants': product.variants.filter(is_available=True),
        'related': related,
        'reviews': reviews,
        'review_form': ReviewForm(instance=user_review),
        'user_review': user_review,
        'in_wishlist': in_wishlist,
        'max_qty': min(product.stock, settings.MAX_QTY_PER_ITEM),
    })
