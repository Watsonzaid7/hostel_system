/**
 * main.js — Client-side interactions for Hostel Management System
 * ================================================================
 * Handles:
 *   • Mobile sidebar toggle (with backdrop)
 *   • Client-side form validation
 *   • Auto-dismiss flash alerts
 */

document.addEventListener('DOMContentLoaded', () => {

    // ── Mobile Sidebar Toggle ──────────────────────────────────────────
    const sidebar       = document.getElementById('sidebar');
    const toggleBtn     = document.getElementById('sidebarToggle');
    let   backdrop      = document.querySelector('.sidebar-backdrop');

    if (sidebar && toggleBtn) {
        // Create backdrop element if it doesn't exist
        if (!backdrop) {
            backdrop = document.createElement('div');
            backdrop.className = 'sidebar-backdrop';
            document.body.appendChild(backdrop);
        }

        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('show');
            backdrop.classList.toggle('show');
        });

        backdrop.addEventListener('click', () => {
            sidebar.classList.remove('show');
            backdrop.classList.remove('show');
        });
    }


    // ── Client-Side Form Validation ────────────────────────────────────
    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        registerForm.addEventListener('submit', (e) => {
            const password = document.getElementById('password');
            const confirm  = document.getElementById('confirm_password');

            if (password.value.length < 6) {
                e.preventDefault();
                showValidationError(password, 'Password must be at least 6 characters.');
                return;
            }

            if (password.value !== confirm.value) {
                e.preventDefault();
                showValidationError(confirm, 'Passwords do not match.');
                return;
            }
        });
    }
    // Generic required-field validation for room form
    const roomForm = document.getElementById('roomForm');
    if (roomForm) {
        roomForm.addEventListener('submit', (e) => {
            const required = roomForm.querySelectorAll('[required]');
            for (const field of required) {
                if (!field.value.trim()) {
                    e.preventDefault();
                    showValidationError(field, 'This field is required.');
                    field.focus();
                    return;
                }
            }
        });
    }

    // Room request confirmation (Browse Rooms page)
    document.querySelectorAll('.room-request-form').forEach(form => {
        form.addEventListener('submit', (e) => {
            const roomNumber = form.getAttribute('data-room');
            if (!confirm('Submit request for Room ' + roomNumber + '?')) {
                e.preventDefault();
            }
        });
    });


    // ── Auto-Dismiss Flash Alerts (after 5 seconds) ───────────────────
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
            bsAlert.close();
        }, 5000);
    });


    // ── Helper: Show inline validation error ──────────────────────────
    function showValidationError(field, message) {
        // Remove old error if exists
        const prev = field.parentElement.querySelector('.invalid-feedback');
        if (prev) prev.remove();
        field.classList.remove('is-invalid');

        // Add error
        field.classList.add('is-invalid');
        const feedback = document.createElement('div');
        feedback.className = 'invalid-feedback';
        feedback.textContent = message;
        field.parentElement.appendChild(feedback);

        // Auto-clear after 3 seconds
        setTimeout(() => {
            field.classList.remove('is-invalid');
            feedback.remove();
        }, 3000);
    }

});
