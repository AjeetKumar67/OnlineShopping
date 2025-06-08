from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('register/', views.register, name='register'),
    path('login/', views.custom_login, name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('profile/', views.profile, name='profile'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('profile/addresses/', views.address_list, name='address_list'),
    path('profile/addresses/add/', views.add_address, name='add_address'),
    path('profile/addresses/edit/<int:address_id>/', views.edit_address, name='edit_address'),
    path('profile/addresses/delete/<int:address_id>/', views.delete_address, name='delete_address'),
    path('profile/addresses/set-default/<int:address_id>/', views.set_default_address, name='set_default_address'),
    
    # Password reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='users/password_reset.html'), 
        name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='users/password_reset_done.html'), 
        name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='users/password_reset_confirm.html'), 
        name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='users/password_reset_complete.html'), 
        name='password_reset_complete'),
]
