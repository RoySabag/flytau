from flask import Blueprint, render_template, request, session, redirect, url_for, current_app

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    # גישה ל-DAO דרך האפליקציה הנוכחית (עוקף את המעגל)
    employee_dao = current_app.employee_dao

    if request.method == 'POST':
        emp_id = request.form.get('employee_id')
        password = request.form.get('password')  # בעתיד נוסיף בדיקת סיסמה

        # שימוש ב-DAO ובדיקת Admin
        if employee_dao.get_employee_by_id(emp_id) and employee_dao.is_admin(emp_id):
            session['admin_logged_in'] = True
            session['admin_id'] = emp_id
            # הפניה לדשבורד (שים לב לנקודה: admin.dashboard)
            return redirect(url_for('admin.dashboard'))
        else:
            return render_template('admin/login.html', error="Access Denied")

    return render_template('admin/login.html')


@admin_bp.route('/dashboard')
def dashboard():
    return "<h1>Admin Dashboard - Success!</h1>"