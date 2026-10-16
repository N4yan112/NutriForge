"""Admin dashboard: statistics shown at the top of /admin/."""
from django.contrib import admin
from django.db.models import F, Sum

from accounts.models import User
from orders.models import Order
from products.models import Product
from .models import ContactMessage, NewsletterSubscriber

admin.site.site_header = 'NutriForge Admin'
admin.site.site_title = 'NutriForge Admin'
admin.site.index_title = 'Dashboard'

_original_index = admin.site.index


def dashboard_index(request, extra_context=None):
    valid_orders = Order.objects.exclude(status='cancelled')
    low_stock = Product.objects.filter(is_active=True, stock__lte=F('low_stock_limit'))
    extra_context = extra_context or {}
    extra_context['stats'] = [
        ('Total products', Product.objects.count()),
        ('Total customers', User.objects.filter(is_staff=False).count()),
        ('Total orders', Order.objects.count()),
        ('Total revenue', '₹{:,.0f}'.format(valid_orders.aggregate(s=Sum('total'))['s'] or 0)),
        ('Pending orders', Order.objects.filter(status__in=['placed', 'confirmed']).count()),
        ('Low-stock products', low_stock.count()),
    ]
    extra_context['low_stock_products'] = low_stock.order_by('stock')[:8]
    extra_context['recent_orders'] = Order.objects.select_related('user')[:5]
    return _original_index(request, extra_context)


admin.site.index = dashboard_index


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('subject', 'name', 'email', 'is_read', 'created_at')
    list_editable = ('is_read',)


admin.site.register(NewsletterSubscriber)
