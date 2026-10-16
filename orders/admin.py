from django.contrib import admin
from .models import Coupon, Order, OrderItem, Payment


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'flavour', 'price', 'quantity')
    can_delete = False


class PaymentInline(admin.StackedInline):
    model = Payment
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total', 'status', 'payment_status', 'created_at')
    list_editable = ('status',)                     # change status straight from the list
    list_filter = ('status', 'created_at', 'payment__method')
    search_fields = ('id', 'user__username', 'full_name', 'phone')
    readonly_fields = ('user', 'subtotal', 'discount', 'delivery_charge', 'total',
                       'coupon', 'coupon_code', 'created_at')
    inlines = [OrderItemInline, PaymentInline]
    actions = ['mark_confirmed', 'mark_packed', 'mark_shipped', 'mark_delivered']

    @admin.display(description='Payment')
    def payment_status(self, order):
        return order.payment.get_status_display() if hasattr(order, 'payment') else '-'

    def _set_status(self, request, queryset, status):
        updated = queryset.exclude(status='cancelled').update(status=status)
        self.message_user(request, f'{updated} order(s) marked as {status}.')

    @admin.action(description='Mark as Confirmed')
    def mark_confirmed(self, request, qs): self._set_status(request, qs, 'confirmed')

    @admin.action(description='Mark as Packed')
    def mark_packed(self, request, qs): self._set_status(request, qs, 'packed')

    @admin.action(description='Mark as Shipped')
    def mark_shipped(self, request, qs): self._set_status(request, qs, 'shipped')

    @admin.action(description='Mark as Delivered (COD becomes Paid)')
    def mark_delivered(self, request, qs):
        self._set_status(request, qs, 'delivered')
        Payment.objects.filter(order__in=qs, method='cod', status='pending')\
            .exclude(order__status='cancelled').update(status='paid')


@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_type', 'value', 'min_order', 'valid_to',
                    'is_active', 'used_count')
    list_editable = ('is_active',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('order', 'method', 'status', 'amount', 'paid_at')
    list_filter = ('method', 'status')
