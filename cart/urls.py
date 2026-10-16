from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_page, name='cart'),
    path('add/<int:pk>/', views.add_to_cart, name='cart_add'),
    path('update/<int:item_id>/', views.update_item, name='cart_update'),
    path('remove/<int:item_id>/', views.remove_item, name='cart_remove'),
    path('coupon/apply/', views.apply_coupon, name='coupon_apply'),
    path('coupon/remove/', views.remove_coupon, name='coupon_remove'),
]
