from datetime import datetime, timedelta
from sqlalchemy import func
from app.models import User, AttendanceRecord, Violation, Payroll, WorkSchedule, ScheduleShift, UserRole, db


def get_admin_dashboard_stats():
    """Lay thong ke cho dashboard Admin/Manager"""
    today = datetime.now().date()
    month_start = today.replace(day=1)

    # Tong so nhan vien dang lam viec
    total_staff = User.query.filter_by(status='active').count()

    # Tong gio lam trong thang
    total_hours = db.session.query(func.sum(AttendanceRecord.total_work_hours)).filter(
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date <= today
    ).scalar() or 0

    # Tong so vi pham trong thang
    total_violations = Violation.query.filter(
        Violation.date >= month_start,
        Violation.date <= today
    ).count()

    # Tong luong du kien thang nay
    total_payroll = db.session.query(func.sum(Payroll.net_salary)).filter(
        Payroll.month == today.month,
        Payroll.year == today.year
    ).scalar() or 0

    return {
        'total_staff': total_staff,
        'total_hours': round(total_hours, 1),
        'total_violations': total_violations,
        'total_payroll': total_payroll
    }


def get_staff_dashboard_stats(user_id):
    """Lay thong ke cho dashboard Nhan vien"""
    today = datetime.now().date()
    month_start = today.replace(day=1)

    # Tong gio lam trong thang
    total_hours = db.session.query(func.sum(AttendanceRecord.total_work_hours)).filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date <= today
    ).scalar() or 0

    # Tong so ca lam trong thang
    total_shifts = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date <= today
    ).count()

    # So lan di muon trong thang
    late_count = Violation.query.filter(
        Violation.user_id == user_id,
        Violation.type == 'late',
        Violation.date >= month_start,
        Violation.date <= today
    ).count()

    # Luong du kien
    payroll = Payroll.query.filter_by(
        user_id=user_id,
        month=today.month,
        year=today.year
    ).first()
    estimated_salary = payroll.net_salary if payroll else 0

    return {
        'total_hours': round(total_hours, 1),
        'total_shifts': total_shifts,
        'late_count': late_count,
        'estimated_salary': estimated_salary
    }


def get_weekly_hours_chart_data():
    """Lay du lieu bieu do gio lam theo tuan (4 tuan gan nhat)"""
    today = datetime.now().date()
    weeks = []
    data = []

    for i in range(4):
        week_end = today - timedelta(days=today.weekday()) - timedelta(weeks=i)
        week_start = week_end - timedelta(days=6)

        total = db.session.query(func.sum(AttendanceRecord.total_work_hours)).filter(
            AttendanceRecord.date >= week_start,
            AttendanceRecord.date <= week_end
        ).scalar() or 0

        weeks.insert(0, f'Tuan {4-i}')
        data.insert(0, round(total, 1))

    return {'labels': weeks, 'data': data}


def get_top_employees():
    """Lay top 5 nhan vien guong mau (di som nhat)"""
    today = datetime.now().date()
    month_start = today.replace(day=1)

    # Dem so ngay di som (early_bird)
    top_employees = db.session.query(
        User.full_name,
        func.count(AttendanceRecord.id).label('early_bird_count')
    ).join(AttendanceRecord).filter(
        AttendanceRecord.is_early_bird == True,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date <= today
    ).group_by(User.id).order_by(func.count(AttendanceRecord.id).desc()).limit(5).all()

    return [{'name': e[0], 'count': e[1]} for e in top_employees]


def get_violation_stats():
    """Thong ke vi pham theo loai"""
    today = datetime.now().date()
    month_start = today.replace(day=1)

    stats = db.session.query(
        Violation.type,
        func.count(Violation.id)
    ).filter(
        Violation.date >= month_start,
        Violation.date <= today
    ).group_by(Violation.type).all()

    labels = []
    data = []
    for stat in stats:
        labels.append(stat[0].value if hasattr(stat[0], 'value') else str(stat[0]))
        data.append(stat[1])

    return {'labels': labels, 'data': data}


def get_current_week_schedule():
    """Lay lich lam viec tuan hien tai"""
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    shifts = db.session.query(
        ScheduleShift, User
    ).select_from(ScheduleShift)\
     .join(WorkSchedule, ScheduleShift.schedule_id == WorkSchedule.id)\
     .join(User, WorkSchedule.user_id == User.id)\
     .filter(
        ScheduleShift.date >= week_start,
        ScheduleShift.date <= week_end,
        ScheduleShift.is_confirmed == True
    ).order_by(ScheduleShift.date, ScheduleShift.shift_type).all()

    return shifts


def get_recent_notifications(user_id, limit=5):
    """Lay thong bao gan day cua user"""
    from app.models import Notification
    return Notification.query.filter_by(
        user_id=user_id
    ).order_by(Notification.created_at.desc()).limit(limit).all()
