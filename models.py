"""
models.py — Database Models for Hostel Room Allocation System
=============================================================
Defines three core tables:
  • User       – students and admins
  • Room       – hostel rooms across blocks
  • AllocationRequest – student ↔ room allocation workflow
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

# ── Shared SQLAlchemy instance (imported by app.py) ──────────────────────────
db = SQLAlchemy()


# ─── USER MODEL ──────────────────────────────────────────────────────────────
class User(UserMixin, db.Model):
    """Represents both admin and student accounts."""

    __tablename__ = "users"

    id         = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(120), unique=True, nullable=False)
    password   = db.Column(db.String(256), nullable=False)          # hashed
    role       = db.Column(db.String(10), nullable=False, default="student")  # admin | student
    student_id = db.Column(db.String(20), unique=True, nullable=True)        # NULL for admins
    phone      = db.Column(db.String(15), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    requests = db.relationship("AllocationRequest", backref="student",
                               foreign_keys="AllocationRequest.student_id",
                               lazy=True)

    # ── Password helpers ─────────────────────────────────────────────────
    def set_password(self, raw_password: str):
        """Hash and store the password."""
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        """Verify a raw password against the stored hash."""
        return check_password_hash(self.password, raw_password)

    def __repr__(self):
        return f"<User {self.name} ({self.role})>"


# ─── ROOM MODEL ──────────────────────────────────────────────────────────────
class Room(db.Model):
    """A single hostel room."""

    __tablename__ = "rooms"

    id          = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    block       = db.Column(db.String(5), nullable=False)          # A, B, C, D
    floor       = db.Column(db.Integer, nullable=False)
    room_type   = db.Column(db.String(10), nullable=False)         # single | double | triple
    price       = db.Column(db.Float, nullable=False)
    capacity    = db.Column(db.Integer, nullable=False)
    amenities   = db.Column(db.String(255), nullable=True)         # comma-separated
    status      = db.Column(db.String(10), nullable=False, default="vacant")  # vacant | occupied

    # Relationships
    allocations = db.relationship("AllocationRequest", backref="room", lazy=True)

    @property
    def current_occupants(self):
        """Return the count of approved allocations for this room."""
        return AllocationRequest.query.filter_by(
            room_id=self.id, status="approved"
        ).count()

    @property
    def is_full(self):
        """True when approved occupants have reached capacity."""
        return self.current_occupants >= self.capacity

    def __repr__(self):
        return f"<Room {self.room_number} Block-{self.block}>"


# ─── ALLOCATION REQUEST MODEL ───────────────────────────────────────────────
class AllocationRequest(db.Model):
    """Tracks a student's request for a specific room."""

    __tablename__ = "allocation_requests"

    id            = db.Column(db.Integer, primary_key=True)
    student_id    = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id       = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    request_date  = db.Column(db.DateTime, default=datetime.utcnow)
    status        = db.Column(db.String(10), nullable=False, default="pending")  # pending | approved | rejected
    approved_by   = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    move_in_date  = db.Column(db.Date, nullable=True)
    remarks       = db.Column(db.Text, nullable=True)

    # Extra relationship for the admin who approved / rejected
    approver = db.relationship("User", foreign_keys=[approved_by], lazy=True)

    def __repr__(self):
        return f"<AllocationRequest student={self.student_id} room={self.room_id} status={self.status}>"
