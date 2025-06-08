from django.db import models
from django.contrib.auth.models import User
from products.models import Product

class SalesReport(models.Model):
    REPORT_TYPE_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    report_type = models.CharField(max_length=10, choices=REPORT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    total_sales = models.DecimalField(max_digits=12, decimal_places=2)
    total_orders = models.PositiveIntegerField()
    average_order_value = models.DecimalField(max_digits=10, decimal_places=2)
    report_data = models.JSONField(default=dict)
    generated_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.report_type.capitalize()} Sales Report ({self.start_date} to {self.end_date})"

class ProductViewLog(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='view_logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True, null=True)
    viewed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"{self.product.title} viewed by {user_str} on {self.viewed_at.strftime('%d-%m-%Y %H:%M')}"

class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('info', 'Information'),
        ('warning', 'Warning'),
        ('alert', 'Alert'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=100)
    message = models.TextField()
    notification_type = models.CharField(max_length=10, choices=NOTIFICATION_TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.title} for {self.user.username}"

class StockAlert(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_alerts')
    threshold = models.PositiveIntegerField(default=5)
    is_active = models.BooleanField(default=True)
    last_triggered = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        status = "Active" if self.is_active else "Inactive"
        return f"Stock Alert for {self.product.title} (Threshold: {self.threshold}) - {status}"
