from django.urls import path
from . import views

urlpatterns = [
    path('', views.wishlist_page, name='wishlist'),
    path('toggle/<int:pk>/', views.toggle, name='wishlist_toggle'),
    path('move/<int:pk>/', views.move_to_cart, name='wishlist_move'),
]
