import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Service, Booking, Message, Payment, Milestone
from datetime import datetime
import uuid
from sqlalchemy import or_, and_

app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-this-secret-key-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


@app.after_request
def no_cache(response):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, private'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.before_request
def enforce_session_user():
    open_routes = {'login', 'register', 'static'}
    if request.endpoint in open_routes:
        return

    session_uid = session.get('_user_id')

    if session_uid is None:
        return

    if current_user.is_authenticated and str(current_user.id) != str(session_uid):
        logout_user()
        flash('Session expired. Please log in again.', 'info')
        return redirect(url_for('login'))


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(request.args.get('next') or url_for('dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        username  = request.form.get('username',  '').strip()
        email     = request.form.get('email',     '').strip().lower()
        role      = request.form.get('role',      'client')
        password  = request.form.get('password',  '')
        confirm   = request.form.get('confirm',   '')

        if not all([full_name, username, email, password, confirm]):
            flash('All fields are required.', 'error')
            return render_template('register.html')
        if password != confirm:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        if role not in ('client', 'freelancer'):
            flash('Invalid role selected.', 'error')
            return render_template('register.html')
        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')

        user = User(full_name=full_name, username=username, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash('Account created! You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    role = current_user.role

    if role == 'admin':
        total_users        = User.query.filter(User.role != 'admin').count()
        total_clients      = User.query.filter_by(role='client').count()
        total_freelancers  = User.query.filter_by(role='freelancer').count()
        total_bookings     = Booking.query.count()
        active_bookings    = Booking.query.filter_by(status='accepted').count()
        pending_bookings   = Booking.query.filter_by(status='pending').count()
        completed_bookings = Booking.query.filter_by(status='completed').count()
        cancelled_bookings = Booking.query.filter_by(status='cancelled').count()
        total_services     = Service.query.filter_by(is_active=True).count()
        total_revenue      = db.session.query(
                                db.func.sum(Booking.amount)
                             ).filter_by(status='completed').scalar() or 0
        recent_bookings    = Booking.query.order_by(Booking.created_at.desc()).limit(5).all()
        recent_users       = User.query.filter(User.role != 'admin')\
                                .order_by(User.created_at.desc()).limit(5).all()
        booking_stats      = [pending_bookings, active_bookings,
                              completed_bookings, cancelled_bookings]

        # FIX: pre-compute percentages so the template never divides by zero
        total_b = sum(booking_stats)
        def pct(n):
            return round(n / total_b * 100, 1) if total_b > 0 else 0

        booking_pcts = [pct(s) for s in booking_stats]

        # FIX: pre-compute user-ratio percentages
        client_pct     = round(total_clients    / total_users * 100) if total_users > 0 else 0
        freelancer_pct = round(total_freelancers / total_users * 100) if total_users > 0 else 0

        # FIX: pre-compute platform health %
        health_pct = round(completed_bookings / total_bookings * 100) if total_bookings > 0 else 0

        return render_template('dashboard_admin.html',
            total_users=total_users,
            total_clients=total_clients,
            total_freelancers=total_freelancers,
            total_bookings=total_bookings,
            active_bookings=active_bookings,
            pending_bookings=pending_bookings,
            completed_bookings=completed_bookings,
            total_services=total_services,
            total_revenue=total_revenue,
            recent_bookings=recent_bookings,
            recent_users=recent_users,
            booking_stats=booking_stats,
            booking_pcts=booking_pcts,
            client_pct=client_pct,
            freelancer_pct=freelancer_pct,
            health_pct=health_pct,
            total_b=total_b)

    elif role == 'freelancer':
        my_services    = Service.query.filter_by(freelancer_id=current_user.id, is_active=True).all()
        my_bookings    = Booking.query.filter_by(freelancer_id=current_user.id)\
                               .order_by(Booking.created_at.desc()).all()
        active_jobs    = Booking.query.filter_by(freelancer_id=current_user.id, status='accepted').count()
        proposals_sent = Service.query.filter_by(freelancer_id=current_user.id).count()
        total_earnings = db.session.query(db.func.sum(Booking.amount)).filter_by(
            freelancer_id=current_user.id, status='completed').scalar() or 0
        unread_msgs    = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
        return render_template('dashboard_freelancer.html',
            my_services=my_services,
            my_bookings=my_bookings,
            active_jobs=active_jobs,
            proposals_sent=proposals_sent,
            total_earnings=total_earnings,
            unread_msgs=unread_msgs)

    else:  # client
        available_services = Service.query.filter_by(is_active=True).join(User).filter(
            User.role == 'freelancer').order_by(Service.created_at.desc()).all()
        my_bookings       = Booking.query.filter_by(client_id=current_user.id)\
                                  .order_by(Booking.created_at.desc()).all()
        active_projects   = Booking.query.filter_by(client_id=current_user.id, status='accepted').count()
        pending_proposals = Booking.query.filter_by(client_id=current_user.id, status='pending').count()
        completed         = Booking.query.filter_by(client_id=current_user.id, status='completed').count()
        unread_msgs       = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
        return render_template('dashboard_client.html',
            available_services=available_services,
            my_bookings=my_bookings,
            active_projects=active_projects,
            pending_proposals=pending_proposals,
            completed=completed,
            unread_msgs=unread_msgs)


# ── My Bookings (Client) ─────────────────────────────────────────────────────

@app.route('/my-bookings')
@login_required
def my_bookings():
    if current_user.role != 'client':
        return redirect(url_for('dashboard'))

    bookings = Booking.query.filter_by(
        client_id=current_user.id
    ).order_by(
        Booking.created_at.desc()
    ).all()

    unread_msgs = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count()

    return render_template(
        'my_bookings.html',
        my_bookings=bookings,
        unread_msgs=unread_msgs
    )


# ── Booking Requests (Freelancer) ─────────────────────────────────────────────

@app.route('/freelancer/booking-requests')
@login_required
def booking_requests():
    if current_user.role != 'freelancer':
        return redirect(url_for('dashboard'))
    my_bookings   = Booking.query.filter_by(freelancer_id=current_user.id)\
                          .order_by(Booking.created_at.desc()).all()
    pending_count = sum(1 for b in my_bookings if b.status == 'pending')
    unread_msgs   = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return render_template('booking_requests.html',
        my_bookings=my_bookings,
        pending_count=pending_count,
        unread_msgs=unread_msgs)


# ── Chat / Messenger ──────────────────────────────────────────────────────────

@app.route('/chat/<int:other_id>', methods=['GET', 'POST'])
@login_required
def chat(other_id):
    other = db.session.get(User, other_id)
    if not other or other.id == current_user.id:
        flash('User not found.', 'error')
        return redirect(url_for('dashboard'))

    service_id = request.args.get('service_id', type=int)
    service    = db.session.get(Service, service_id) if service_id else None

    if request.method == 'POST':
        action  = request.form.get('action')
        content = request.form.get('content', '').strip()

        if action == 'send_message' and content:
            msg = Message(sender_id=current_user.id, receiver_id=other_id,
                          content=content, msg_type='text')
            db.session.add(msg)
            db.session.commit()

        elif action == 'send_booking' and service:
            existing = Booking.query.filter_by(client_id=current_user.id,
                                               service_id=service.id,
                                               status='pending').first()
            if existing:
                flash('You already have a pending booking for this service.', 'info')
            else:
                note = request.form.get('content', '').strip()
                booking = Booking(
                    client_id=current_user.id,
                    freelancer_id=other_id,
                    service_id=service.id,
                    amount=service.price,
                    message=note or None
                )
                db.session.add(booking)
                db.session.flush()

                card_text = f"📦 Booking Request: {service.title} — ₹{service.price:.2f}"
                msg = Message(sender_id=current_user.id, receiver_id=other_id,
                              content=card_text, msg_type='booking_request',
                              booking_id=booking.id)
                db.session.add(msg)
                db.session.commit()
                flash('Booking request sent!', 'success')

        return redirect(url_for('chat', other_id=other_id,
                                service_id=service_id if service_id else ''))

    Message.query.filter_by(sender_id=other_id, receiver_id=current_user.id,
                             is_read=False).update({'is_read': True})
    db.session.commit()

    messages = Message.query.filter(
        or_(
            and_(Message.sender_id == current_user.id, Message.receiver_id == other_id),
            and_(Message.sender_id == other_id,        Message.receiver_id == current_user.id)
        )
    ).order_by(Message.created_at.asc()).all()

    conversations = _get_conversations()

    return render_template('chat.html',
        other=other,
        messages=messages,
        service=service,
        conversations=conversations)


@app.route('/chat/<int:other_id>/booking/<int:booking_id>/update', methods=['POST'])
@login_required
def chat_update_booking(other_id, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.freelancer_id != current_user.id:
        flash('Not found.', 'error')
        return redirect(url_for('chat', other_id=other_id))

    new_status = request.form.get('status')
    if new_status in ('accepted', 'cancelled'):
        booking.status = new_status
        label = '✅ Booking Accepted' if new_status == 'accepted' else '❌ Booking Declined'
        msg = Message(sender_id=current_user.id, receiver_id=other_id,
                      content=label, msg_type='text')
        db.session.add(msg)
        db.session.commit()
        flash(f'Booking {new_status}.', 'success')
    return redirect(url_for('chat', other_id=other_id))


@app.route('/chat/<int:other_id>/booking/<int:booking_id>/complete', methods=['POST'])
@login_required
def chat_complete_booking(other_id, booking_id):
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.freelancer_id != current_user.id:
        flash('Not found.', 'error')
        return redirect(url_for('chat', other_id=other_id))
    booking.status = 'completed'
    msg = Message(sender_id=current_user.id, receiver_id=other_id,
                  content='🎉 Project marked as completed!', msg_type='text')
    db.session.add(msg)
    db.session.commit()
    flash('Marked as completed.', 'success')
    return redirect(url_for('chat', other_id=other_id))


@app.route('/messages')
@login_required
def messages():
    conversations = _get_conversations()

    unread_msgs = Message.query.filter_by(
        receiver_id=current_user.id,
        is_read=False
    ).count()

    return render_template(
        'messages.html',
        conversations=conversations,
        unread_msgs=unread_msgs
    )


def _get_conversations():
    uid = current_user.id
    all_msgs = Message.query.filter(
        or_(Message.sender_id == uid, Message.receiver_id == uid)
    ).order_by(Message.created_at.desc()).all()

    seen, convos = set(), []
    for m in all_msgs:
        other_id = m.receiver_id if m.sender_id == uid else m.sender_id
        if other_id in seen:
            continue
        seen.add(other_id)
        other = db.session.get(User, other_id)
        unread = Message.query.filter_by(sender_id=other_id, receiver_id=uid, is_read=False).count()
        convos.append({'user': other, 'last': m, 'unread': unread})
    return convos


# ── Freelancer: Service management ────────────────────────────────────────────

@app.route('/freelancer/service/add', methods=['GET', 'POST'])
@login_required
def add_service():
    if current_user.role != 'freelancer':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        title       = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category    = request.form.get('category', '').strip()
        price_raw   = request.form.get('price', '0').strip()

        if not all([title, description, category, price_raw]):
            flash('All fields are required.', 'error')
            unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
            return render_template('freelancer_add_service.html', unread_msgs=unread_msgs)
        try:
            price = float(price_raw)
            if price <= 0:
                raise ValueError
        except ValueError:
            flash('Price must be a positive number.', 'error')
            unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
            return render_template('freelancer_add_service.html', unread_msgs=unread_msgs)

        service = Service(freelancer_id=current_user.id, title=title,
                          description=description, category=category, price=price)
        db.session.add(service)
        db.session.commit()
        flash('Proposal added successfully!', 'success')
        return redirect(url_for('dashboard'))
    unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return render_template('freelancer_add_service.html', unread_msgs=unread_msgs)


@app.route('/freelancer/service/delete/<int:service_id>', methods=['POST'])
@login_required
def delete_service(service_id):
    service = db.session.get(Service, service_id)
    if not service or service.freelancer_id != current_user.id:
        flash('Service not found.', 'error')
        return redirect(url_for('dashboard'))
    service.is_active = False
    db.session.commit()
    flash('Proposal removed.', 'info')
    return redirect(url_for('dashboard'))


# ── Admin ─────────────────────────────────────────────────────────────────────

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    users = User.query.order_by(User.id).all()
    return render_template('admin_users.html', users=users)


@app.route('/admin/profile', methods=['GET', 'POST'])
@login_required
def admin_profile():
    if current_user.role != 'admin':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_name':
            new_full_name = request.form.get('full_name', '').strip()
            if not new_full_name:
                flash('Full name cannot be empty.', 'error')
            else:
                current_user.full_name = new_full_name
                db.session.commit()
                flash('Full name updated successfully.', 'success')
        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw     = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'error')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'error')
            elif new_pw != confirm_pw:
                flash('New passwords do not match.', 'error')
            elif current_pw == new_pw:
                flash('New password must differ from the current one.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password changed successfully.', 'success')
        return redirect(url_for('admin_profile'))
    return render_template('admin_profile.html')


# ── Client: Book Service ──────────────────────────────────────────────────────

@app.route('/client/book/<int:service_id>', methods=['POST'])
@login_required
def client_book(service_id):
    if current_user.role != 'client':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))

    service = db.session.get(Service, service_id)
    if not service or not service.is_active:
        flash('Service not found.', 'error')
        return redirect(url_for('dashboard'))

    existing = Booking.query.filter_by(
        client_id=current_user.id,
        service_id=service_id,
        status='pending'
    ).first()
    if existing:
        flash('You already have a pending booking for this service.', 'info')
        return redirect(url_for('dashboard'))

    message      = request.form.get('message', '').strip()
    week_descs   = request.form.getlist('week_desc[]')
    week_prices  = request.form.getlist('week_price[]')

    if not week_descs or not week_prices:
        flash('Please add at least one weekly milestone.', 'error')
        return redirect(url_for('dashboard'))

    try:
        prices = [float(p) for p in week_prices if p.strip()]
    except ValueError:
        flash('Invalid milestone prices.', 'error')
        return redirect(url_for('dashboard'))

    if not prices:
        flash('Please enter prices for all milestones.', 'error')
        return redirect(url_for('dashboard'))

    total = round(sum(prices), 2)
    if abs(total - service.price) > 0.01:
        flash(f'Milestone prices (₹{total:.2f}) must equal the service price (₹{service.price:.2f}).', 'error')
        return redirect(url_for('dashboard'))

    booking = Booking(
        client_id=current_user.id,
        freelancer_id=service.freelancer_id,
        service_id=service_id,
        amount=service.price,
        message=message or None
    )
    db.session.add(booking)
    db.session.flush()

    for i, (desc, price) in enumerate(zip(week_descs, prices), start=1):
        if desc.strip():
            db.session.add(Milestone(
                booking_id=booking.id,
                week_number=i,
                description=desc.strip(),
                price=price
            ))

    db.session.commit()
    flash('Booking request sent successfully!', 'success')
    return redirect(url_for('dashboard'))


# ── Freelancer Profile ────────────────────────────────────────────────────────

@app.route('/freelancer/profile', methods=['GET', 'POST'])
@login_required
def freelancer_profile():
    if current_user.role != 'freelancer':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            email     = request.form.get('email', '').strip().lower()
            if not full_name or not email:
                flash('Name and email are required.', 'error')
            else:
                existing = User.query.filter(User.email == email, User.id != current_user.id).first()
                if existing:
                    flash('Email already in use.', 'error')
                else:
                    current_user.full_name = full_name
                    current_user.email     = email
                    db.session.commit()
                    flash('Profile updated successfully.', 'success')
        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw     = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'error')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'error')
            elif new_pw != confirm_pw:
                flash('Passwords do not match.', 'error')
            elif current_pw == new_pw:
                flash('New password must differ from the current one.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password changed successfully.', 'success')
        return redirect(url_for('freelancer_profile'))
    unread_msgs    = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    total_earnings = db.session.query(db.func.sum(Booking.amount)).filter_by(
        freelancer_id=current_user.id, status='completed').scalar() or 0
    total_jobs     = Booking.query.filter_by(freelancer_id=current_user.id, status='completed').count()
    return render_template('profile_freelancer.html',
        unread_msgs=unread_msgs,
        total_earnings=total_earnings,
        total_jobs=total_jobs)


# ── Client Profile ────────────────────────────────────────────────────────────

@app.route('/client/profile', methods=['GET', 'POST'])
@login_required
def client_profile():
    if current_user.role != 'client':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_profile':
            full_name = request.form.get('full_name', '').strip()
            email     = request.form.get('email', '').strip().lower()
            if not full_name or not email:
                flash('Name and email are required.', 'error')
            else:
                existing = User.query.filter(User.email == email, User.id != current_user.id).first()
                if existing:
                    flash('Email already in use.', 'error')
                else:
                    current_user.full_name = full_name
                    current_user.email     = email
                    db.session.commit()
                    flash('Profile updated successfully.', 'success')
        elif action == 'change_password':
            current_pw = request.form.get('current_password', '')
            new_pw     = request.form.get('new_password', '')
            confirm_pw = request.form.get('confirm_password', '')
            if not current_user.check_password(current_pw):
                flash('Current password is incorrect.', 'error')
            elif len(new_pw) < 6:
                flash('New password must be at least 6 characters.', 'error')
            elif new_pw != confirm_pw:
                flash('Passwords do not match.', 'error')
            elif current_pw == new_pw:
                flash('New password must differ from the current one.', 'error')
            else:
                current_user.set_password(new_pw)
                db.session.commit()
                flash('Password changed successfully.', 'success')
        return redirect(url_for('client_profile'))
    total_bookings = Booking.query.filter_by(client_id=current_user.id).count()
    completed      = Booking.query.filter_by(client_id=current_user.id, status='completed').count()
    unread_msgs    = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
    return render_template('profile_client.html',
        total_bookings=total_bookings,
        completed=completed,
        unread_msgs=unread_msgs)


# ── Payments ──────────────────────────────────────────────────────────────────

@app.route('/payments')
@login_required
def payments():
    unread_msgs = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()

    if current_user.role == 'client':
        bookings = Booking.query.filter(
            Booking.client_id == current_user.id,
            Booking.status.in_(['pending', 'accepted', 'completed'])
        ).order_by(Booking.created_at.desc()).all()
        my_payments = Payment.query.filter_by(client_id=current_user.id)\
                             .order_by(Payment.created_at.desc()).all()

        # FIX: pre-compute total paid in Python instead of broken Jinja selectattr+sum
        total_paid    = sum(p.amount for p in my_payments if p.status == 'paid')
        pending_count = sum(
            1 for b in bookings
            if not b.payment or b.payment.status != 'paid'
        )

        return render_template('payments_client.html',
            bookings=bookings,
            my_payments=my_payments,
            total_paid=total_paid,
            pending_count=pending_count,
            unread_msgs=unread_msgs)

    elif current_user.role == 'freelancer':
        my_payments  = Payment.query.filter_by(freelancer_id=current_user.id)\
                              .order_by(Payment.created_at.desc()).all()
        total_earned = sum(p.amount for p in my_payments if p.status == 'paid')
        pending_amt  = sum(p.amount for p in my_payments if p.status == 'pending')
        unread_msgs  = Message.query.filter_by(receiver_id=current_user.id, is_read=False).count()
        return render_template('payments_freelancer.html',
            my_payments=my_payments,
            total_earned=total_earned,
            pending_amt=pending_amt,
            unread_msgs=unread_msgs)
    else:
        return redirect(url_for('dashboard'))


@app.route('/payments/pay/<int:booking_id>', methods=['POST'])
@login_required
def pay_booking(booking_id):
    if current_user.role != 'client':
        flash('Access denied.', 'error')
        return redirect(url_for('dashboard'))
    booking = db.session.get(Booking, booking_id)
    if not booking or booking.client_id != current_user.id:
        flash('Booking not found.', 'error')
        return redirect(url_for('payments'))
    existing = Payment.query.filter_by(booking_id=booking_id, status='paid').first()
    if existing:
        flash('This booking has already been paid.', 'info')
        return redirect(url_for('payments'))
    txn_id = 'TXN-' + uuid.uuid4().hex[:12].upper()
    payment = Payment(
        booking_id=booking_id,
        client_id=current_user.id,
        freelancer_id=booking.freelancer_id,
        amount=booking.amount,
        status='paid',
        transaction_id=txn_id,
        paid_at=datetime.utcnow()
    )
    db.session.add(payment)
    booking.status = 'completed'
    db.session.commit()
    flash(f'Payment of ₹{booking.amount:.2f} successful! Transaction ID: {txn_id}', 'success')
    return redirect(url_for('payments'))



# ── Init DB ───────────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True)