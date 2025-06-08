from django.urls import path
from . import views

urlpatterns = [
    path('checkout/', views.checkout, name='checkout'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<str:order_number>/', views.order_success, name='order_success'),
    path('order-history/', views.order_history, name='order_history'),
    path('order-detail/<str:order_number>/', views.order_detail, name='order_detail'),
    path('cancel-order/<str:order_number>/', views.cancel_order, name='cancel_order'),
    path('return-order/<str:order_number>/', views.return_order, name='return_order'),
    path('invoice/<str:order_number>/', views.generate_invoice, name='generate_invoice'),
]
