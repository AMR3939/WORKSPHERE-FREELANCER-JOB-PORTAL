"""
Run this script once to create the default admin account.

Usage:
    python create_admin.py
"""
from app import app
from models import db, User

def create_admin():
    with app.app_context():
        db.create_all()

        ADMIN_USERNAME = 'admin'
        ADMIN_EMAIL    = 'admin@gmail.com'
        ADMIN_PASSWORD = 'admin'
        ADMIN_FULLNAME = 'Alwin Shajees'

        if User.query.filter_by(username=ADMIN_USERNAME).first():
            print(f'[!] Admin user "{ADMIN_USERNAME}" already exists. Skipping.')
            return

        admin = User(
            username  = ADMIN_USERNAME,
            email     = ADMIN_EMAIL,
            full_name = ADMIN_FULLNAME,
            role      = 'admin'
        )
        admin.set_password(ADMIN_PASSWORD)
        db.session.add(admin)
        db.session.commit()

        print('✅ Admin account created successfully!')
        print(f'   Username : {ADMIN_USERNAME}')
        print(f'   Password : {ADMIN_PASSWORD}')
        print(f'   Email    : {ADMIN_EMAIL}')
        print('\n⚠️  Change the password after first login!')

if __name__ == '__main__':
    create_admin()