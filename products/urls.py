from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.product_search, name='product_search'),
    path('category/<slug:category_slug>/', views.category_products, name='category_products'),
    path('product/<slug:product_slug>/', views.product_detail, name='product_detail'),
    path('brand/<slug:brand_slug>/', views.brand_products, name='brand_products'),
    path('ajax/get-subcategories/', views.get_subcategories, name='get_subcategories'),
]
