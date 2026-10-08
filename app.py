"""
app.py — Main Application Entry Point
=======================================
• Initialises Flask, SQLAlchemy, Flask-Login
• Registers admin & student blueprints
• Handles login / register / logout routes
• Seeds the database with 1 admin + 20 sample rooms
"""

import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user

from models import db, User, Room, AllocationRequest
from routes.admin import admin_bp
from routes.student import student_bp

# ─── App Factory ─────────────────────────────────────────────────────────────
app = Flask(__name__)
app.config["SECRET_KEY"] = "hostel-system-secret-key-change-in-production"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hostel.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialise extensions
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

# Register blueprints
app.register_blueprint(admin_bp)
app.register_blueprint(student_bp)


# ── User loader for Flask-Login ─────────────────────────────────────────────
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ═══════════════════════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    """Redirect to the appropriate dashboard based on role."""
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.dashboard"))
        return redirect(url_for("student.dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    """Login page for both admins and students."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get("next")
            if user.role == "admin":
                return redirect(next_page or url_for("admin.dashboard"))
            return redirect(next_page or url_for("student.dashboard"))
        else:
            flash("Invalid email or password.", "danger")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Student self-registration."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        name       = request.form.get("name", "").strip()
        email      = request.form.get("email", "").strip().lower()
        student_id = request.form.get("student_id", "").strip()
        phone      = request.form.get("phone", "").strip()
        password   = request.form.get("password", "")
        confirm    = request.form.get("confirm_password", "")

        # ── Validation ──────────────────────────────────────────────────
        errors = []
        if not all([name, email, student_id, password]):
            errors.append("All fields marked * are required.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if User.query.filter_by(email=email).first():
            errors.append("An account with this email already exists.")
        if User.query.filter_by(student_id=student_id).first():
            errors.append("This Student ID is already registered.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return redirect(url_for("register"))

        # ── Create user ─────────────────────────────────────────────────
        new_user = User(
            name=name,
            email=email,
            student_id=student_id,
            phone=phone,
            role="student",
        )
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/logout")
@login_required
def logout():
    """Log the current user out."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))


# ═══════════════════════════════════════════════════════════════════════════════
#  DATABASE SEEDING
# ═══════════════════════════════════════════════════════════════════════════════

def seed_database():
    """
    Populate the database with:
      • 1 default admin  (admin@hostel.com / admin123)
      • 20 sample rooms across blocks A, B, C, D
    Only runs when the DB has no users yet.
    """
    if User.query.first():
        return  # already seeded

    # ── Admin account ────────────────────────────────────────────────────
    admin = User(
        name="Admin",
        email="admin@hostel.com",
        role="admin",
    )
    admin.set_password("admin123")
    db.session.add(admin)

    # ── Room definitions ─────────────────────────────────────────────────
    room_configs = [
        # Block A — Single rooms (floor 1)
        ("A101", "A", 1, "single", 5000, 1, "Wi-Fi, Bed, Table, Chair, Cupboard"),
        ("A102", "A", 1, "single", 5000, 1, "Wi-Fi, Bed, Table, Chair, Cupboard"),
        ("A201", "A", 2, "double", 4000, 2, "Wi-Fi, 2 Beds, Table, Chairs, Cupboard"),
        ("A202", "A", 2, "double", 4000, 2, "Wi-Fi, 2 Beds, Table, Chairs, Cupboard"),
        ("A301", "A", 3, "triple", 3000, 3, "Wi-Fi, 3 Beds, Table, Chairs, Cupboard"),
        # Block B — Mix
        ("B101", "B", 1, "single", 5500, 1, "Wi-Fi, AC, Bed, Table, Attached Bath"),
        ("B102", "B", 1, "single", 5500, 1, "Wi-Fi, AC, Bed, Table, Attached Bath"),
        ("B201", "B", 2, "double", 4500, 2, "Wi-Fi, AC, 2 Beds, Table, Attached Bath"),
        ("B202", "B", 2, "double", 4500, 2, "Wi-Fi, AC, 2 Beds, Table, Attached Bath"),
        ("B301", "B", 3, "triple", 3500, 3, "Wi-Fi, 3 Beds, Table, Shared Bath"),
        # Block C — Budget
        ("C101", "C", 1, "double", 3500, 2, "Wi-Fi, 2 Beds, Table, Shared Bath"),
        ("C102", "C", 1, "double", 3500, 2, "Wi-Fi, 2 Beds, Table, Shared Bath"),
        ("C201", "C", 2, "triple", 2500, 3, "Wi-Fi, 3 Beds, Table, Shared Bath"),
        ("C202", "C", 2, "triple", 2500, 3, "Wi-Fi, 3 Beds, Table, Shared Bath"),
        ("C301", "C", 3, "single", 4500, 1, "Wi-Fi, Bed, Table, Cupboard"),
        # Block D — Premium
        ("D101", "D", 1, "single", 7000, 1, "Wi-Fi, AC, Bed, Table, Attached Bath, Balcony"),
        ("D102", "D", 1, "single", 7000, 1, "Wi-Fi, AC, Bed, Table, Attached Bath, Balcony"),
        ("D201", "D", 2, "double", 6000, 2, "Wi-Fi, AC, 2 Beds, Table, Attached Bath, Balcony"),
        ("D202", "D", 2, "double", 6000, 2, "Wi-Fi, AC, 2 Beds, Table, Attached Bath, Balcony"),
        ("D301", "D", 3, "triple", 5000, 3, "Wi-Fi, AC, 3 Beds, Table, Attached Bath"),
    ]

    for number, block, floor, rtype, price, cap, amenities in room_configs:
        room = Room(
            room_number=number,
            block=block,
            floor=floor,
            room_type=rtype,
            price=price,
            capacity=cap,
            amenities=amenities,
            status="vacant",
        )
        db.session.add(room)

    db.session.commit()
    print("[OK] Database seeded with admin account and 20 rooms.")


# ═══════════════════════════════════════════════════════════════════════════════
#  RUN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_database()
    app.run(debug=True, port=5000)
