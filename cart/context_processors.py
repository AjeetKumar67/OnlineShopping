def cart_count(request):
    """
    Context processor to get the cart count for the current user.
    This makes cart item count available across all templates.
    """
    count = 0
    if request.user.is_authenticated:
        try:
            cart = request.user.cart
            count = cart.total_items
        except:
            count = 0
    return {'cart_count': count}
