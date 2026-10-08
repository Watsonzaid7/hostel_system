"""
routes/admin.py — Admin Blueprint
==================================
Handles:
  • Admin dashboard with statistics
  • Room CRUD (Add / Edit / Delete)
  • View all students
  • View & process allocation requests (Approve / Reject)
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime

from models import db, User, Room, AllocationRequest

# ── Blueprint Registration ───────────────────────────────────────────────────
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ── Admin-Only Decorator ────────────────────────────────────────────────────
def admin_required(f):
    """Ensure the logged-in user has the 'admin' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "admin":
            flash("Access denied. Admins only.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@admin_bp.route("/dashboard")
@login_required
@admin_required
def dashboard():
    """Admin home page with stat cards."""
    total_rooms    = Room.query.count()
    occupied_rooms = Room.query.filter_by(status="occupied").count()
    vacant_rooms   = Room.query.filter_by(status="vacant").count()
    pending_reqs   = AllocationRequest.query.filter_by(status="pending").count()
    total_students = User.query.filter_by(role="student").count()
    approved_reqs  = AllocationRequest.query.filter_by(status="approved").count()

    return render_template(
        "admin/dashboard.html",
        total_rooms=total_rooms,
        occupied_rooms=occupied_rooms,
        vacant_rooms=vacant_rooms,
        pending_reqs=pending_reqs,
        total_students=total_students,
        approved_reqs=approved_reqs,
    )


# ─── ROOMS MANAGEMENT ───────────────────────────────────────────────────────
@admin_bp.route("/rooms")
@login_required
@admin_required
def rooms():
    """List all rooms with Add / Edit / Delete controls."""
    all_rooms = Room.query.order_by(Room.block, Room.room_number).all()
    return render_template("admin/rooms.html", rooms=all_rooms)


@admin_bp.route("/rooms/add", methods=["GET", "POST"])
@login_required
@admin_required
def add_room():
    """Add a new room to the system."""
    if request.method == "POST":
        # Collect form data
        room_number = request.form.get("room_number", "").strip()
        block       = request.form.get("block", "").strip()
        floor       = request.form.get("floor", type=int)
        room_type   = request.form.get("room_type", "").strip()
        price       = request.form.get("price", type=float)
        capacity    = request.form.get("capacity", type=int)
        amenities   = request.form.get("amenities", "").strip()

        # Basic validation
        if not all([room_number, block, floor is not None, room_type, price, capacity]):
            flash("Please fill in all required fields.", "warning")
            return redirect(url_for("admin.add_room"))

        # Check duplicate room number
        if Room.query.filter_by(room_number=room_number).first():
            flash(f"Room {room_number} already exists.", "danger")
            return redirect(url_for("admin.add_room"))

        new_room = Room(
            room_number=room_number,
            block=block,
            floor=floor,
            room_type=room_type,
            price=price,
            capacity=capacity,
            amenities=amenities,
            status="vacant",
        )
        db.session.add(new_room)
        db.session.commit()
        flash(f"Room {room_number} added successfully!", "success")
        return redirect(url_for("admin.rooms"))

    return render_template("admin/room_form.html", room=None, action="Add")


@admin_bp.route("/rooms/edit/<int:room_id>", methods=["GET", "POST"])
@login_required
@admin_required
def edit_room(room_id):
    """Edit an existing room's details."""
    room = Room.query.get_or_404(room_id)

    if request.method == "POST":
        room.room_number = request.form.get("room_number", "").strip()
        room.block       = request.form.get("block", "").strip()
        room.floor       = request.form.get("floor", type=int)
        room.room_type   = request.form.get("room_type", "").strip()
        room.price       = request.form.get("price", type=float)
        room.capacity    = request.form.get("capacity", type=int)
        room.amenities   = request.form.get("amenities", "").strip()
        room.status      = request.form.get("status", "vacant").strip()

        db.session.commit()
        flash(f"Room {room.room_number} updated.", "success")
        return redirect(url_for("admin.rooms"))

    return render_template("admin/room_form.html", room=room, action="Edit")


@admin_bp.route("/rooms/delete/<int:room_id>", methods=["POST"])
@login_required
@admin_required
def delete_room(room_id):
    """Delete a room (only if it has no approved allocations)."""
    room = Room.query.get_or_404(room_id)

    # Safety check: don't delete rooms with active allocations
    active = AllocationRequest.query.filter_by(room_id=room.id, status="approved").count()
    if active:
        flash("Cannot delete a room with active allocations.", "danger")
        return redirect(url_for("admin.rooms"))

    # Delete related pending/rejected requests first
    AllocationRequest.query.filter_by(room_id=room.id).delete()
    db.session.delete(room)
    db.session.commit()
    flash(f"Room {room.room_number} deleted.", "success")
    return redirect(url_for("admin.rooms"))


# ─── STUDENTS LIST ───────────────────────────────────────────────────────────
@admin_bp.route("/students")
@login_required
@admin_required
def students():
    """View all registered students."""
    all_students = User.query.filter_by(role="student").order_by(User.name).all()
    return render_template("admin/students.html", students=all_students)


# ─── ALLOCATION REQUESTS ────────────────────────────────────────────────────
@admin_bp.route("/requests")
@login_required
@admin_required
def requests_list():
    """View all allocation requests."""
    all_requests = (
        AllocationRequest.query
        .order_by(AllocationRequest.request_date.desc())
        .all()
    )
    return render_template("admin/requests.html", requests=all_requests)


@admin_bp.route("/requests/<int:req_id>/approve", methods=["POST"])
@login_required
@admin_required
def approve_request(req_id):
    """Approve a pending allocation request."""
    alloc = AllocationRequest.query.get_or_404(req_id)

    if alloc.status != "pending":
        flash("This request has already been processed.", "info")
        return redirect(url_for("admin.requests_list"))

    # Check room capacity
    room = Room.query.get(alloc.room_id)
    if room.is_full:
        flash(f"Room {room.room_number} is already at full capacity.", "danger")
        return redirect(url_for("admin.requests_list"))

    alloc.status      = "approved"
    alloc.approved_by = current_user.id
    alloc.remarks     = request.form.get("remarks", "").strip()
    alloc.move_in_date = datetime.utcnow().date()

    # Update room status if it reaches capacity
    if room.current_occupants + 1 >= room.capacity:
        room.status = "occupied"

    db.session.commit()
    flash(f"Request #{alloc.id} approved.", "success")
    return redirect(url_for("admin.requests_list"))


@admin_bp.route("/requests/<int:req_id>/reject", methods=["POST"])
@login_required
@admin_required
def reject_request(req_id):
    """Reject a pending allocation request."""
    alloc = AllocationRequest.query.get_or_404(req_id)

    if alloc.status != "pending":
        flash("This request has already been processed.", "info")
        return redirect(url_for("admin.requests_list"))

    alloc.status      = "rejected"
    alloc.approved_by = current_user.id
    alloc.remarks     = request.form.get("remarks", "").strip()

    db.session.commit()
    flash(f"Request #{alloc.id} rejected.", "warning")
    return redirect(url_for("admin.requests_list"))
