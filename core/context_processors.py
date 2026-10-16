"""Variables available in EVERY template (navbar counts, wishlist hearts, categories)."""
from django.db.models import Sum

from cart.models import CartItem
from products.models import Category
from wishlist.models import Wishlist


def site_context(request):
    ctx = {'nav_categories': Category.objects.all(), 'cart_count': 0,
           'wishlist_count': 0, 'wishlist_ids': set()}
    if request.user.is_authenticated:
        ctx['cart_count'] = CartItem.objects.filter(cart__user=request.user)\
            .aggregate(n=Sum('quantity'))['n'] or 0
        ids = set(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))
        ctx['wishlist_ids'] = ids
        ctx['wishlist_count'] = len(ids)
    return ctx
