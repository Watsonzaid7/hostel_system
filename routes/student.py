"""
routes/student.py — Student Blueprint
=======================================
Handles:
  • Student dashboard
  • Browse available rooms (with filters)
  • Submit allocation request
  • View current request status
  • View assigned room & roommate details
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps

from models import db, User, Room, AllocationRequest

# ── Blueprint Registration ───────────────────────────────────────────────────
student_bp = Blueprint("student", __name__, url_prefix="/student")


# ── Student-Only Decorator ──────────────────────────────────────────────────
def student_required(f):
    """Ensure the logged-in user has the 'student' role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != "student":
            flash("Access denied. Students only.", "danger")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@student_bp.route("/dashboard")
@login_required
@student_required
def dashboard():
    """Student home page showing quick status info."""
    # Get the student's latest request (if any)
    latest_request = (
        AllocationRequest.query
        .filter_by(student_id=current_user.id)
        .order_by(AllocationRequest.request_date.desc())
        .first()
    )

    # If approved, fetch room details
    assigned_room = None
    if latest_request and latest_request.status == "approved":
        assigned_room = Room.query.get(latest_request.room_id)

    return render_template(
        "student/dashboard.html",
        latest_request=latest_request,
        assigned_room=assigned_room,
    )


# ─── BROWSE AVAILABLE ROOMS ─────────────────────────────────────────────────
@student_bp.route("/browse")
@login_required
@student_required
def browse_rooms():
    """List available rooms with optional type and price filters."""
    # Read query-string filters
    room_type  = request.args.get("type", "").strip()
    max_price  = request.args.get("max_price", type=float)
    block      = request.args.get("block", "").strip()

    query = Room.query.filter_by(status="vacant")

    if room_type:
        query = query.filter_by(room_type=room_type)
    if max_price:
        query = query.filter(Room.price <= max_price)
    if block:
        query = query.filter_by(block=block)

    available_rooms = query.order_by(Room.block, Room.room_number).all()

    return render_template(
        "student/browse_rooms.html",
        rooms=available_rooms,
        selected_type=room_type,
        selected_price=max_price,
        selected_block=block,
    )


# ─── SUBMIT ALLOCATION REQUEST ──────────────────────────────────────────────
@student_bp.route("/request/<int:room_id>", methods=["POST"])
@login_required
@student_required
def request_room(room_id):
    """Submit a new allocation request for the given room."""
    # Rule: one active request at a time (pending or approved)
    active = AllocationRequest.query.filter(
        AllocationRequest.student_id == current_user.id,
        AllocationRequest.status.in_(["pending", "approved"]),
    ).first()

    if active:
        flash("You already have an active room request. Cancel or wait for it to be processed.", "warning")
        return redirect(url_for("student.my_status"))

    room = Room.query.get_or_404(room_id)

    if room.is_full:
        flash("Sorry, this room is already full.", "danger")
        return redirect(url_for("student.browse_rooms"))

    new_request = AllocationRequest(
        student_id=current_user.id,
        room_id=room.id,
        status="pending",
    )
    db.session.add(new_request)
    db.session.commit()

    flash(f"Request submitted for Room {room.room_number}!", "success")
    return redirect(url_for("student.my_status"))


# ─── CANCEL REQUEST ─────────────────────────────────────────────────────────
@student_bp.route("/cancel/<int:req_id>", methods=["POST"])
@login_required
@student_required
def cancel_request(req_id):
    """Allow a student to cancel their own pending request."""
    alloc = AllocationRequest.query.get_or_404(req_id)

    # Security: only owner can cancel, and only if pending
    if alloc.student_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for("student.my_status"))

    if alloc.status != "pending":
        flash("Only pending requests can be cancelled.", "warning")
        return redirect(url_for("student.my_status"))

    db.session.delete(alloc)
    db.session.commit()
    flash("Request cancelled.", "info")
    return redirect(url_for("student.my_status"))


# ─── MY STATUS ───────────────────────────────────────────────────────────────
@student_bp.route("/status")
@login_required
@student_required
def my_status():
    """Show the student's request history and current assignment."""
    all_requests = (
        AllocationRequest.query
        .filter_by(student_id=current_user.id)
        .order_by(AllocationRequest.request_date.desc())
        .all()
    )

    # Find the approved allocation (if any) and its roommates
    approved = next((r for r in all_requests if r.status == "approved"), None)
    roommates = []
    assigned_room = None

    if approved:
        assigned_room = Room.query.get(approved.room_id)
        # Find other students approved for the same room
        roommate_allocs = AllocationRequest.query.filter(
            AllocationRequest.room_id == approved.room_id,
            AllocationRequest.status == "approved",
            AllocationRequest.student_id != current_user.id,
        ).all()
        roommates = [User.query.get(a.student_id) for a in roommate_allocs]

    return render_template(
        "student/my_status.html",
        requests=all_requests,
        approved=approved,
        assigned_room=assigned_room,
        roommates=roommates,
    )
