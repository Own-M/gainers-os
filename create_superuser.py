import os
import django

# Django সেটআপ কনফিগারেশন
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sme_project.settings")
django.setup()

from django.contrib.auth.models import User

def create_admin():
    # এখানে আপনার পছন্দমতো অ্যাডমিন তথ্য দিন
    username = "admin"            
    email = "admin@gainers.com"   
    password = "admin123"         # লগইন করার পর এটি চেঞ্জ করে নিবেন

    if not User.objects.filter(username=username).exists():
        print(f"Creating superuser: {username}...")
        try:
            User.objects.create_superuser(username, email, password)
            print("✅ Superuser created successfully!")
        except Exception as e:
            print(f"❌ Error creating superuser: {e}")
    else:
        print("ℹ️ Superuser already exists. Skipping.")

if __name__ == "__main__":
    create_admin()
