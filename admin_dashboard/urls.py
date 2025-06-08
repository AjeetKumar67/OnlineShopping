from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('products/', views.admin_products, name='admin_products'),
    path('orders/', views.admin_orders, name='admin_orders'),
    path('users/', views.admin_users, name='admin_users'),
    path('reports/', views.admin_reports, name='admin_reports'),
    path('reports/sales/', views.sales_report, name='sales_report'),
    path('reports/products/', views.product_report, name='product_report'),
    path('settings/', views.admin_settings, name='admin_settings'),
    path('product/add/', views.add_product, name='add_product'),
    path('product/edit/<int:product_id>/', views.edit_product, name='edit_product'),
    path('product/delete/<int:product_id>/', views.delete_product, name='delete_product'),
    path('category/add/', views.add_category, name='add_category'),
    path('category/edit/<int:category_id>/', views.edit_category, name='edit_category'),
    path('category/delete/<int:category_id>/', views.delete_category, name='delete_category'),
    path('subcategory/add/', views.add_subcategory, name='add_subcategory'),
    path('subcategory/edit/<int:subcategory_id>/', views.edit_subcategory, name='edit_subcategory'),
    path('subcategory/delete/<int:subcategory_id>/', views.delete_subcategory, name='delete_subcategory'),
    path('brand/add/', views.add_brand, name='add_brand'),
    path('brand/edit/<int:brand_id>/', views.edit_brand, name='edit_brand'),
    path('brand/delete/<int:brand_id>/', views.delete_brand, name='delete_brand'),
]
