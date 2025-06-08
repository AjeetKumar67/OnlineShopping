from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.template.loader import get_template
from django.conf import settings

from .models import Order, OrderItem, OrderStatusHistory, Invoice
from cart.models import Cart, CartItem
from products.models import Product, Category
from users.models import Address
from payments.models import Payment, Coupon

import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

@login_required
def checkout(request):
    """
    Display checkout page with address selection and payment options.
    """
    try:
        # Get user's cart
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all().select_related('product')
        
        # Check if cart is empty
        if not cart_items.exists():
            messages.warning(request, 'Your cart is empty')
            return redirect('cart')
        
        # Calculate totals
        subtotal = sum(item.item_total for item in cart_items)
        delivery_fee = 40.00  # Fixed delivery fee
        discount = 0.00
        
        # Check for applied coupon
        coupon_code = request.session.get('coupon_code')
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon.is_valid:
                    if coupon.discount_amount:
                        discount = coupon.discount_amount
                    elif coupon.discount_percentage:
                        discount = (subtotal * coupon.discount_percentage) / 100
            except Coupon.DoesNotExist:
                # Clear invalid coupon
                if 'coupon_code' in request.session:
                    del request.session['coupon_code']
        
        # Apply free delivery if total > 500
        if subtotal > 500:
            delivery_fee = 0
        
        total = subtotal + delivery_fee - discount
        
        # Get user's addresses
        addresses = Address.objects.filter(user=request.user)
        default_address = addresses.filter(is_default=True).first()
        
        context = {
            'cart': cart,
            'cart_items': cart_items,
            'subtotal': subtotal,
            'delivery_fee': delivery_fee,
            'discount': discount,
            'total': total,
            'coupon': coupon,
            'addresses': addresses,
            'default_address': default_address,
            'categories': Category.objects.all(),
        }
        return render(request, 'orders/checkout.html', context)
    except Exception as e:
        messages.error(request, f"Error loading checkout: {str(e)}")
        return redirect('cart')

@login_required
@transaction.atomic
def place_order(request):
    """
    Process the order placement.
    """
    if request.method != 'POST':
        return redirect('checkout')
    
    try:
        # Get form data
        address_id = request.POST.get('address')
        payment_method = request.POST.get('payment_method')
        order_notes = request.POST.get('order_notes', '')
        
        # Validate address
        if not address_id:
            messages.error(request, 'Please select a delivery address')
            return redirect('checkout')
        
        address = get_object_or_404(Address, id=address_id, user=request.user)
        
        # Get user's cart
        cart = get_object_or_404(Cart, user=request.user)
        cart_items = cart.items.all().select_related('product')
        
        # Check if cart is empty
        if not cart_items.exists():
            messages.warning(request, 'Your cart is empty')
            return redirect('cart')
        
        # Calculate totals
        subtotal = sum(item.item_total for item in cart_items)
        delivery_fee = 40.00  # Fixed delivery fee
        discount = 0.00
        
        # Check for applied coupon
        coupon_code = request.session.get('coupon_code')
        coupon = None
        if coupon_code:
            try:
                coupon = Coupon.objects.get(code=coupon_code, is_active=True)
                if coupon.is_valid:
                    if coupon.discount_amount:
                        discount = coupon.discount_amount
                    elif coupon.discount_percentage:
                        discount = (subtotal * coupon.discount_percentage) / 100
                    
                    # Update coupon usage count
                    coupon.used_count += 1
                    coupon.save()
            except Coupon.DoesNotExist:
                pass
        
        # Apply free delivery if total > 500
        if subtotal > 500:
            delivery_fee = 0
        
        total = subtotal + delivery_fee - discount
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            address=address,
            total_amount=total,
            payment_method=payment_method,
            payment_status=payment_method == 'cod',  # COD is not paid yet
            order_status='placed',
            order_notes=order_notes
        )
        
        # Create order items
        for cart_item in cart_items:
            # Check if product is still in stock
            product = cart_item.product
            if product.stock < cart_item.quantity:
                raise Exception(f"Not enough stock for {product.title}")
            
            # Create order item
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=cart_item.quantity,
                price=product.current_price
            )
            
            # Update product stock
            product.stock -= cart_item.quantity
            product.save()
        
        # Create order status history
        OrderStatusHistory.objects.create(
            order=order,
            status='placed',
            notes='Order placed successfully'
        )
        
        # Create invoice
        invoice = Invoice.objects.create(
            order=order,
            invoice_date=timezone.now()
        )
        
        # Create payment record
        payment = Payment.objects.create(
            user=request.user,
            order=order,
            amount=total,
            payment_method=payment_method,
            payment_status='completed' if payment_method == 'cod' else 'pending'
        )
        
        # Clear the cart
        cart_items.delete()
        
        # Clear coupon from session
        if 'coupon_code' in request.session:
            del request.session['coupon_code']
        
        # Redirect to success page
        return redirect('order_success', order_number=order.order_number)
        
    except Exception as e:
        messages.error(request, f"Error placing order: {str(e)}")
        return redirect('checkout')

@login_required
def order_success(request, order_number):
    """
    Display order success page.
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        context = {
            'order': order,
            'categories': Category.objects.all(),
        }
        return render(request, 'orders/order_success.html', context)
    except Exception as e:
        messages.error(request, f"Error retrieving order: {str(e)}")
        return redirect('home')

@login_required
def order_history(request):
    """
    Display user's order history.
    """
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
        'categories': Category.objects.all(),
    }
    return render(request, 'orders/order_history.html', context)

@login_required
def order_detail(request, order_number):
    """
    Display detailed information about a specific order.
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        order_items = order.items.all().select_related('product')
        order_history = order.status_history.all().order_by('-status_date')
        
        context = {
            'order': order,
            'order_items': order_items,
            'order_history': order_history,
            'categories': Category.objects.all(),
        }
        return render(request, 'orders/order_detail.html', context)
    except Exception as e:
        messages.error(request, f"Error retrieving order details: {str(e)}")
        return redirect('order_history')

@login_required
@transaction.atomic
def cancel_order(request, order_number):
    """
    Cancel an order.
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        # Check if order can be cancelled
        if not order.can_cancel:
            messages.error(request, 'This order cannot be cancelled')
            return redirect('order_detail', order_number=order_number)
        
        # Update order status
        order.order_status = 'cancelled'
        order.save()
        
        # Create order status history
        OrderStatusHistory.objects.create(
            order=order,
            status='cancelled',
            notes='Order cancelled by customer'
        )
        
        # Restore product stock
        for item in order.items.all():
            product = item.product
            product.stock += item.quantity
            product.save()
        
        # Update payment status if applicable
        if hasattr(order, 'payment_details'):
            payment = order.payment_details
            payment.payment_status = 'refunded'
            payment.save()
        
        messages.success(request, 'Order cancelled successfully')
        return redirect('order_detail', order_number=order_number)
    except Exception as e:
        messages.error(request, f"Error cancelling order: {str(e)}")
        return redirect('order_detail', order_number=order_number)

@login_required
@transaction.atomic
def return_order(request, order_number):
    """
    Return an order.
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        # Check if order can be returned
        if not order.can_return:
            messages.error(request, 'This order cannot be returned')
            return redirect('order_detail', order_number=order_number)
        
        # Update order status
        order.order_status = 'returned'
        order.save()
        
        # Create order status history
        OrderStatusHistory.objects.create(
            order=order,
            status='returned',
            notes='Return requested by customer'
        )
        
        messages.success(request, 'Return request submitted successfully')
        return redirect('order_detail', order_number=order_number)
    except Exception as e:
        messages.error(request, f"Error processing return: {str(e)}")
        return redirect('order_detail', order_number=order_number)

@login_required
def generate_invoice(request, order_number):
    """
    Generate and download invoice PDF.
    """
    try:
        order = get_object_or_404(Order, order_number=order_number, user=request.user)
        
        # Create a file-like buffer to receive PDF data
        buffer = io.BytesIO()
        
        # Create the PDF object, using the buffer as its "file"
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Draw logo and header
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, "Flipkart Clone")
        
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 70, "Invoice for Order #" + order.order_number)
        p.drawString(50, height - 85, "Date: " + order.created_at.strftime("%d-%m-%Y %H:%M"))
        
        # Customer information
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 120, "Customer Information")
        
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 140, "Name: " + order.user.get_full_name())
        p.drawString(50, height - 155, "Email: " + order.user.email)
        
        # Shipping address
        p.setFont("Helvetica-Bold", 12)
        p.drawString(300, height - 120, "Shipping Address")
        
        p.setFont("Helvetica", 10)
        p.drawString(300, height - 140, order.address.address_line1)
        if order.address.address_line2:
            p.drawString(300, height - 155, order.address.address_line2)
            p.drawString(300, height - 170, f"{order.address.city}, {order.address.state} - {order.address.pincode}")
            p.drawString(300, height - 185, order.address.country)
        else:
            p.drawString(300, height - 155, f"{order.address.city}, {order.address.state} - {order.address.pincode}")
            p.drawString(300, height - 170, order.address.country)
        
        # Order summary
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, height - 220, "Order Summary")
        
        # Create data for the table
        data = [['Item', 'Quantity', 'Price', 'Total']]
        for item in order.items.all():
            data.append([
                item.product.title[:30] + '...' if len(item.product.title) > 30 else item.product.title,
                str(item.quantity),
                '₹' + str(item.price),
                '₹' + str(item.item_total)
            ])
        
        # Calculate dimensions
        col_widths = [250, 75, 75, 75]
        table = Table(data, colWidths=col_widths)
        
        # Add style
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
        table.setStyle(style)
        
        # Draw the table on the PDF
        table.wrapOn(p, width, height)
        table.drawOn(p, 50, height - 250 - (len(data) * 20))
        
        # Payment summary
        y_position = height - 280 - (len(data) * 20)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "Payment Summary")
        
        p.setFont("Helvetica", 10)
        p.drawString(400, y_position - 20, "Subtotal:")
        p.drawString(475, y_position - 20, '₹' + str(order.total_amount))
        
        p.drawString(400, y_position - 35, "Delivery Fee:")
        p.drawString(475, y_position - 35, '₹40.00' if order.total_amount < 500 else 'FREE')
        
        if hasattr(order, 'payment_details') and order.payment_details.payment_status == 'completed':
            p.drawString(400, y_position - 50, "Payment Status:")
            p.drawString(475, y_position - 50, "PAID")
            p.drawString(400, y_position - 65, "Payment Method:")
            p.drawString(475, y_position - 65, order.get_payment_method_display())
        
        p.setFont("Helvetica-Bold", 12)
        p.drawString(400, y_position - 85, "Total Amount:")
        p.drawString(475, y_position - 85, '₹' + str(order.total_amount))
        
        # Footer
        p.setFont("Helvetica", 8)
        p.drawString(50, 30, "This is a computer-generated invoice and does not require a signature.")
        p.drawString(50, 20, "For any queries, please contact support@flipkartclone.com")
        
        # Close the PDF object cleanly
        p.showPage()
        p.save()
        
        # Get the value of the BytesIO buffer and write it to the response
        buffer.seek(0)
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice-{order.order_number}.pdf"'
        
        return response
    except Exception as e:
        messages.error(request, f"Error generating invoice: {str(e)}")
        return redirect('order_detail', order_number=order_number)
