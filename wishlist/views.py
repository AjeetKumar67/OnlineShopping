from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from .models import Wishlist, WishlistItem
from products.models import Product, Category
from cart.models import Cart, CartItem

@login_required
def view_wishlist(request):
    """
    Display the user's wishlist.
    """
    try:
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        wishlist_items = wishlist.items.all().select_related('product')
        
        context = {
            'wishlist': wishlist,
            'wishlist_items': wishlist_items,
            'categories': Category.objects.all(),
        }
        return render(request, 'wishlist/wishlist.html', context)
    except Exception as e:
        messages.error(request, f"Error loading wishlist: {str(e)}")
        return redirect('home')

@login_required
def add_to_wishlist(request):
    """
    Add a product to the wishlist via AJAX.
    """
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        
        try:
            product = Product.objects.get(id=product_id)
            
            # Get or create wishlist
            wishlist, created = Wishlist.objects.get_or_create(user=request.user)
            
            # Check if product is already in wishlist
            item, created = WishlistItem.objects.get_or_create(
                wishlist=wishlist,
                product=product
            )
            
            if created:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Product added to wishlist'
                })
            else:
                return JsonResponse({
                    'status': 'info',
                    'message': 'Product already in wishlist'
                })
        
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found'
            })
        
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request'})

@login_required
def remove_from_wishlist(request, item_id):
    """
    Remove a product from the wishlist.
    """
    try:
        wishlist_item = WishlistItem.objects.get(id=item_id, wishlist__user=request.user)
        wishlist_item.delete()
        messages.success(request, 'Item removed from wishlist')
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found in wishlist')
    
    return redirect('wishlist')

@login_required
def move_to_cart(request, item_id):
    """
    Move an item from wishlist to cart.
    """
    try:
        with transaction.atomic():
            # Get the wishlist item
            wishlist_item = WishlistItem.objects.get(id=item_id, wishlist__user=request.user)
            product = wishlist_item.product
            
            # Check if product is in stock
            if product.stock <= 0:
                messages.error(request, f'{product.title} is out of stock')
                return redirect('wishlist')
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Add to cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': 1}
            )
            
            # If already in cart, increment quantity
            if not created:
                if cart_item.quantity < product.stock:
                    cart_item.quantity += 1
                    cart_item.save()
                else:
                    messages.warning(request, f'Cannot add more {product.title} to cart. Maximum stock reached.')
                    return redirect('wishlist')
            
            # Remove from wishlist
            wishlist_item.delete()
            
            messages.success(request, f'{product.title} moved to cart')
            
    except WishlistItem.DoesNotExist:
        messages.error(request, 'Item not found in wishlist')
    except Exception as e:
        messages.error(request, f'Error moving item to cart: {str(e)}')
    
    return redirect('cart')
