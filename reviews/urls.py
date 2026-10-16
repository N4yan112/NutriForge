from django.urls import path
from . import views

urlpatterns = [path('product/<int:pk>/', views.submit_review, name='submit_review')]
