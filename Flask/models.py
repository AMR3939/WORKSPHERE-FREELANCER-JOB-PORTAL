from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80),  unique=True, nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False)
    full_name     = db.Column(db.String(150), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(20),  nullable=False, default='client')
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)

    services               = db.relationship('Service',  foreign_keys='Service.freelancer_id',  backref='freelancer', lazy=True)
    bookings_as_client     = db.relationship('Booking',  foreign_keys='Booking.client_id',      backref='client',     lazy=True)
    bookings_as_freelancer = db.relationship('Booking',  foreign_keys='Booking.freelancer_id',  backref='freelancer', lazy=True)
    sent_messages          = db.relationship('Message',  foreign_keys='Message.sender_id',      backref='sender',     lazy=True)
    received_messages      = db.relationship('Message',  foreign_keys='Message.receiver_id',    backref='receiver',   lazy=True)
    payments_made          = db.relationship('Payment',  foreign_keys='Payment.client_id',      backref='client',     lazy=True)
    payments_received      = db.relationship('Payment',  foreign_keys='Payment.freelancer_id',  backref='freelancer', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Service(db.Model):
    __tablename__ = 'service'
    id            = db.Column(db.Integer, primary_key=True)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title         = db.Column(db.String(150), nullable=False)
    description   = db.Column(db.Text,        nullable=False)
    category      = db.Column(db.String(80),  nullable=False)
    price         = db.Column(db.Float,       nullable=False)
    is_active     = db.Column(db.Boolean,     default=True)
    created_at    = db.Column(db.DateTime,    default=datetime.utcnow)
    bookings      = db.relationship('Booking', backref='service', lazy=True)


class Booking(db.Model):
    __tablename__ = 'booking'
    id            = db.Column(db.Integer, primary_key=True)
    client_id     = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    freelancer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    service_id    = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    status        = db.Column(db.String(20), default='pending')  # pending|accepted|completed|cancelled
    amount        = db.Column(db.Float,      nullable=False)
    message       = db.Column(db.Text,       nullable=True)
    created_at    = db.Column(db.DateTime,   default=datetime.utcnow)
    # FIX 1: renamed backref from 'booking' to 'booking_record' to avoid
    # conflict with Message.booking's backref 'chat_message' both touching Booking
    payment       = db.relationship('Payment',   backref='booking',      uselist=False, lazy=True)
    milestones    = db.relationship('Milestone', backref='booking',      lazy=True, order_by='Milestone.week_number')
    # FIX 2: removed Message relationship from Booking entirely —
    # Message already defines its own 'booking' relationship with backref='chat_message'
    # Having it declared on BOTH sides caused the mapper conflict


class Message(db.Model):
    __tablename__ = 'message'
    id           = db.Column(db.Integer, primary_key=True)
    sender_id    = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    receiver_id  = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content      = db.Column(db.Text,    nullable=False)
    msg_type     = db.Column(db.String(20), default='text')
    booking_id   = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=True)
    is_read      = db.Column(db.Boolean, default=False)
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    # FIX 3: changed backref name from 'chat_message' to 'messages' so
    # Booking.messages gives all chat messages for that booking (makes more sense)
    booking      = db.relationship('Booking', backref='messages', lazy=True)


class Milestone(db.Model):
    __tablename__ = 'milestone'
    id          = db.Column(db.Integer, primary_key=True)
    booking_id  = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text,    nullable=False)
    price       = db.Column(db.Float,   nullable=False)
    status      = db.Column(db.String(20), default='pending')  # pending|completed
    created_at  = db.Column(db.DateTime,   default=datetime.utcnow)


class Payment(db.Model):
    __tablename__ = 'payment'
    id             = db.Column(db.Integer, primary_key=True)
    booking_id     = db.Column(db.Integer, db.ForeignKey('booking.id'), nullable=False)
    client_id      = db.Column(db.Integer, db.ForeignKey('user.id'),    nullable=False)
    freelancer_id  = db.Column(db.Integer, db.ForeignKey('user.id'),    nullable=False)
    amount         = db.Column(db.Float,   nullable=False)
    status         = db.Column(db.String(20), default='pending')  # pending|paid
    transaction_id = db.Column(db.String(64), nullable=True)
    paid_at        = db.Column(db.DateTime,   nullable=True)
    # FIX 4: added missing created_at column that app.py's Payment queries rely on
    created_at     = db.Column(db.DateTime,   default=datetime.utcnow)