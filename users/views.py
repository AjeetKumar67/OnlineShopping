from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from .models import UserProfile, Address
from products.models import Category
from .forms import UserRegistrationForm, UserUpdateForm, ProfileUpdateForm, AddressForm

def register(request):
    """
    Register a new user.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Set additional profile fields
            user.profile.phone = form.cleaned_data.get('phone')
            user.profile.save()
            
            # Log the user in
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=password)
            login(request, user)
            
            messages.success(request, f'Account created for {username}! You are now logged in.')
            return redirect('home')
    else:
        form = UserRegistrationForm()
    
    # Add Bootstrap classes to form fields
    for field_name, field in form.fields.items():
        field.widget.attrs['class'] = 'form-control'
    
    context = {
        'form': form,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/register.html', context)

def custom_login(request):
    """
    Custom login view.
    """
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                
                # Redirect to the next page if specified, otherwise to home
                next_page = request.GET.get('next')
                return redirect(next_page) if next_page else redirect('home')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = AuthenticationForm()
    
    context = {
        'form': form,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/login.html', context)

@login_required
def profile(request):
    """
    Display user profile.
    """
    addresses = Address.objects.filter(user=request.user)
    default_address = addresses.filter(is_default=True).first()
    
    context = {
        'user': request.user,
        'addresses': addresses,
        'default_address': default_address,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/profile.html', context)

@login_required
@transaction.atomic
def update_profile(request):
    """
    Update user profile.
    """
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = ProfileUpdateForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/update_profile.html', context)

@login_required
def address_list(request):
    """
    List all addresses for a user.
    """
    addresses = Address.objects.filter(user=request.user)
    
    context = {
        'addresses': addresses,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/address_list.html', context)

@login_required
def add_address(request):
    """
    Add a new address.
    """
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            
            # If this is the first address or set_default is checked, make it default
            set_default = form.cleaned_data.get('set_default', False)
            address_count = Address.objects.filter(user=request.user).count()
            
            if address_count == 0 or set_default:
                # First unset any existing default
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                address.is_default = True
            
            address.save()
            messages.success(request, 'Address added successfully!')
            return redirect('address_list')
    else:
        form = AddressForm()
    
    context = {
        'form': form,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/add_address.html', context)

@login_required
def edit_address(request, address_id):
    """
    Edit an existing address.
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            addr = form.save(commit=False)
            
            # Handle default address status
            set_default = form.cleaned_data.get('set_default', False)
            if set_default and not addr.is_default:
                # First unset any existing default
                Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
                addr.is_default = True
            
            addr.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('address_list')
    else:
        form = AddressForm(instance=address)
    
    context = {
        'form': form,
        'address': address,
        'categories': Category.objects.all(),
    }
    return render(request, 'users/edit_address.html', context)

@login_required
def delete_address(request, address_id):
    """
    Delete an address.
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # If deleting the default address, set another as default if available
    if address.is_default:
        other_address = Address.objects.filter(user=request.user).exclude(id=address_id).first()
        if other_address:
            other_address.is_default = True
            other_address.save()
    
    address.delete()
    messages.success(request, 'Address deleted successfully!')
    return redirect('address_list')

@login_required
def set_default_address(request, address_id):
    """
    Set an address as the default.
    """
    address = get_object_or_404(Address, id=address_id, user=request.user)
    
    # First unset any existing default
    Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
    
    # Set the new default
    address.is_default = True
    address.save()
    
    messages.success(request, 'Default address updated!')
    return redirect('address_list')
