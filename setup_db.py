import os
import sys
import django
from django.db import connection

# Add the project directory to the Python path
sys.path.append('/home/hotelogix/Desktop/pac/onlineShopping/flipkart_clone')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'flipkart_clone.settings')
django.setup()

# Create the MySQL database
def create_database():
    with connection.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS flipkart_clone_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        print("Database created successfully or already exists")

if __name__ == "__main__":
    create_database()
    print("Database setup completed")
