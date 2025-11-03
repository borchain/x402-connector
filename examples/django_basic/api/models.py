"""Models for the example API app.

This example doesn't require database models, but the file is included
for completeness as Django expects it.
"""

from django.db import models

# No models needed for this simple API example
# In a real application, you might have models like:

# class PaidContent(models.Model):
#     """Example model for paid content."""
#     title = models.CharField(max_length=200)
#     body = models.TextField()
#     price = models.DecimalField(max_digits=10, decimal_places=2)
#     created_at = models.DateTimeField(auto_now_add=True)
#
# class PaymentLog(models.Model):
#     """Example model for logging payments."""
#     transaction_hash = models.CharField(max_length=66)
#     payer_address = models.CharField(max_length=42)
#     amount = models.DecimalField(max_digits=20, decimal_places=6)
#     resource_path = models.CharField(max_length=500)
#     timestamp = models.DateTimeField(auto_now_add=True)

