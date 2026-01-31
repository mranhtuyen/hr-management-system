from flask import render_template, redirect, url_for
from flask_login import login_required, current_user
from app.dashboard import bp
from app.dashboard.utils import (
    get_admin_dashboard_stats,
    get_staff_dashboard_stats,
    get_weekly_hours_chart_data,
    get_top_employees,
    get_violation_stats,
    get_current_week_schedule,
    get_recent_notifications
)
from app.models import UserRole


@bp.route('/')
@login_required
def index():
    """Trang dashboard chinh - Redirect theo role"""
    if current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return redirect(url_for('dashboard.admin'))
    else:
        return redirect(url_for('dashboard.staff'))


@bp.route('/admin')
@login_required
def admin():
    """Dashboard cho Admin/Manager"""
    if current_user.role not in [UserRole.ADMIN, UserRole.MANAGER]:
        return redirect(url_for('dashboard.staff'))

    stats = get_admin_dashboard_stats()
    weekly_hours = get_weekly_hours_chart_data()
    top_employees = get_top_employees()
    violation_stats = get_violation_stats()
    week_schedule = get_current_week_schedule()
    notifications = get_recent_notifications(current_user.id)

    return render_template('dashboard/admin_dashboard.html',
                           stats=stats,
                           weekly_hours=weekly_hours,
                           top_employees=top_employees,
                           violation_stats=violation_stats,
                           week_schedule=week_schedule,
                           notifications=notifications)


@bp.route('/staff')
@login_required
def staff():
    """Dashboard cho Nhan vien"""
    stats = get_staff_dashboard_stats(current_user.id)
    notifications = get_recent_notifications(current_user.id)

    # Lich lam viec tuan nay cua NV
    from datetime import datetime, timedelta
    from app.models import WorkSchedule, ScheduleShift

    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    my_schedule = WorkSchedule.query.filter(
        WorkSchedule.user_id == current_user.id,
        WorkSchedule.week_start_date <= today,
        WorkSchedule.week_end_date >= today
    ).first()

    my_shifts = []
    if my_schedule:
        my_shifts = ScheduleShift.query.filter(
            ScheduleShift.schedule_id == my_schedule.id,
            ScheduleShift.is_confirmed == True
        ).order_by(ScheduleShift.date).all()

    # Kiem tra trang thai dang ky lich tuan sau
    next_week_start = week_end + timedelta(days=1)
    next_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=next_week_start
    ).first()

    return render_template('dashboard/staff_dashboard.html',
                           stats=stats,
                           notifications=notifications,
                           my_shifts=my_shifts,
                           next_schedule=next_schedule,
                           week_start=week_start,
                           week_end=week_end)
