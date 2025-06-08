from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import F, Sum
from django.contrib import messages
from .models import Cart, CartItem
from products.models import Product
from users.models import Address  # Changed from addresses.models to users.models

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product')
    
    # Calculate totals
    subtotal = sum(item.get_total() for item in cart_items)
    shipping = 0 if subtotal >= 500 else 40  # Free shipping for orders above ₹500
    total = subtotal + shipping
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
        'cart_count': cart_items.count(),
    }
    return render(request, 'cart/cart.html', context)

@login_required
def update_cart(request):
    if request.method == 'POST':
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            cart_item = CartItem.objects.get(id=item_id, cart__user=request.user)
            
            # Check stock availability
            if quantity > cart_item.product.stock:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Only {cart_item.product.stock} items available in stock.'
                })
            
            if quantity <= 0:
                cart_item.delete()
                status = 'removed'
            else:
                cart_item.quantity = quantity
                cart_item.save()
                status = 'updated'
            
            # Recalculate totals
            cart = cart_item.cart
            cart_items = CartItem.objects.filter(cart=cart)
            subtotal = sum(item.get_total() for item in cart_items)
            shipping = 0 if subtotal >= 500 else 40
            total = subtotal + shipping
            
            return JsonResponse({
                'status': 'success',
                'action': status,
                'item_total': cart_item.get_total() if status != 'removed' else 0,
                'subtotal': subtotal,
                'shipping': shipping,
                'total': total,
                'cart_count': cart_items.count(),
            })
            
        except CartItem.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Item not found in your cart.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })

@login_required
def remove_from_cart(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    messages.success(request, 'Item removed from your cart.')
    return redirect('view_cart')

@login_required
def add_to_cart(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        
        try:
            product = Product.objects.get(id=product_id, is_available=True)
            
            # Check if product is in stock
            if product.stock < quantity:
                return JsonResponse({
                    'status': 'error',
                    'message': f'Only {product.stock} items available in stock.'
                })
            
            # Get or create cart
            cart, created = Cart.objects.get_or_create(user=request.user)
            
            # Check if item already in cart
            try:
                cart_item = CartItem.objects.get(cart=cart, product=product)
                new_quantity = cart_item.quantity + quantity
                
                # Check if new quantity exceeds stock
                if new_quantity > product.stock:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Cannot add more. You already have {cart_item.quantity} in your cart and only {product.stock} are available.'
                    })
                
                cart_item.quantity = new_quantity
                cart_item.save()
            except CartItem.DoesNotExist:
                cart_item = CartItem.objects.create(
                    cart=cart,
                    product=product,
                    quantity=quantity
                )
            
            # Count total items in cart
            cart_count = CartItem.objects.filter(cart=cart).aggregate(
                total_items=Sum('quantity')
            )['total_items'] or 0
            
            return JsonResponse({
                'status': 'success',
                'message': 'Product added to cart successfully!',
                'cart_count': cart_count
            })
            
        except Product.DoesNotExist:
            return JsonResponse({
                'status': 'error',
                'message': 'Product not found or unavailable.'
            })
    
    return JsonResponse({
        'status': 'error',
        'message': 'Invalid request method.'
    })

@login_required
def checkout(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart).select_related('product')
    
    if not cart_items:
        messages.warning(request, 'Your cart is empty. Add items before checkout.')
        return redirect('view_cart')
    
    # Check stock availability
    for item in cart_items:
        if item.quantity > item.product.stock:
            messages.error(request, f'Only {item.product.stock} units of {item.product.title} available. Please update your cart.')
            return redirect('view_cart')
    
    # Calculate totals
    subtotal = sum(item.get_total() for item in cart_items)
    shipping = 0 if subtotal >= 500 else 40
    total = subtotal + shipping
    
    # Get user's addresses
    addresses = Address.objects.filter(user=request.user)
    
    context = {
        'cart_items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
        'addresses': addresses,
    }
    return render(request, 'cart/checkout.html', context)

@login_required
def clear_cart(request):
    """Clear all items from the user's cart."""
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        CartItem.objects.filter(cart=cart).delete()
        messages.success(request, 'Your cart has been cleared.')
    return redirect('view_cart')

@login_required
def apply_coupon(request):
    """Apply a coupon code to the cart."""
    if request.method == 'POST':
        coupon_code = request.POST.get('coupon_code')
        # Implement coupon validation and application logic here
        # This is a placeholder implementation
        messages.info(request, f'Coupon "{coupon_code}" is not valid or expired.')
        return redirect('view_cart')
    return redirect('view_cart')
