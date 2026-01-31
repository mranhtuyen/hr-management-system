"""
Module tinh luong thang

CONG THUC TINH LUONG:
    LUONG GOP = Tong gio x Luong gio x Ty le huong luong

    CONG THEM:
    - Tien ho tro an ca
    - Tien thuong

    TRU DI:
    - Tien phat
    - Tien tam ung

    THUC LINH = Luong gop + Thuong - Phat - Tam ung
"""

from datetime import datetime, date as date_type
from app.models import (
    Payroll, AttendanceRecord, Violation, Reward, Holiday, User,
    PayrollStatus, db
)
from flask import current_app


def get_holiday_multiplier(check_date):
    """Lay he so luong ngay le"""
    holiday = Holiday.query.filter_by(date=check_date).first()
    if holiday:
        return holiday.salary_multiplier
    return 1.0


def calculate_work_hours_with_holiday(user_id, month, year):
    """
    Tinh tong gio lam co ap dung he so ngay le

    Returns:
        tuple: (total_hours, total_shifts, holiday_hours)
    """
    month_start = date_type(year, month, 1)
    if month == 12:
        month_end = date_type(year + 1, 1, 1)
    else:
        month_end = date_type(year, month + 1, 1)

    records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date < month_end
    ).all()

    total_hours = 0
    holiday_hours = 0
    total_shifts = len(records)

    for record in records:
        multiplier = get_holiday_multiplier(record.date)
        hours = record.total_work_hours * multiplier
        total_hours += hours

        if multiplier > 1:
            holiday_hours += record.total_work_hours * (multiplier - 1)

    return total_hours, total_shifts, holiday_hours


def calculate_meal_support(user_id, month, year):
    """
    Tinh tien ho tro an ca
    - Chi ap dung cho NV Full-time (>=8h/ngay)
    - Muc ho tro: 25,000d/ngay
    """
    user = User.query.get(user_id)
    if not user or not user.meal_support_eligible:
        return 0, 0

    month_start = date_type(year, month, 1)
    if month == 12:
        month_end = date_type(year + 1, 1, 1)
    else:
        month_end = date_type(year, month + 1, 1)

    # Dem so ngay lam du 8h
    try:
        threshold = current_app.config.get('FULLTIME_THRESHOLD', 8)
        support_amount = current_app.config.get('MEAL_SUPPORT_AMOUNT', 25000)
    except RuntimeError:
        threshold = 8
        support_amount = 25000

    records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date < month_end,
        AttendanceRecord.total_work_hours >= threshold
    ).all()

    fulltime_days = len(records)
    total_support = fulltime_days * support_amount

    return total_support, fulltime_days


def calculate_penalties(user_id, month, year):
    """Tinh tong tien phat trong thang"""
    month_start = date_type(year, month, 1)
    if month == 12:
        month_end = date_type(year + 1, 1, 1)
    else:
        month_end = date_type(year, month + 1, 1)

    violations = Violation.query.filter(
        Violation.user_id == user_id,
        Violation.date >= month_start,
        Violation.date < month_end
    ).all()

    total_penalty = sum(v.penalty_amount for v in violations)
    late_count = sum(1 for v in violations if v.type.value == 'late')

    return total_penalty, late_count, violations


def calculate_rewards(user_id, month, year):
    """Tinh tong tien thuong trong thang"""
    month_start = datetime(year, month, 1)
    if month == 12:
        month_end = datetime(year + 1, 1, 1)
    else:
        month_end = datetime(year, month + 1, 1)

    rewards = Reward.query.filter(
        Reward.user_id == user_id,
        Reward.created_at >= month_start,
        Reward.created_at < month_end
    ).all()

    total_reward = sum(r.reward_amount for r in rewards)

    return total_reward, rewards


def calculate_monthly_payroll(user_id, month, year, advance_payment=0):
    """
    Tinh luong thang cho 1 nhan vien

    Args:
        user_id: ID nhan vien
        month: Thang
        year: Nam
        advance_payment: Tien tam ung

    Returns:
        Payroll object
    """
    user = User.query.get(user_id)
    if not user:
        return None

    # 1. Tinh tong gio lam (co he so ngay le)
    total_hours, total_shifts, holiday_hours = calculate_work_hours_with_holiday(
        user_id, month, year
    )

    # 2. Luong gop = Gio lam x Luong gio x Ty le
    gross_salary = total_hours * user.hourly_rate * (user.salary_percentage / 100)

    # 3. Tien ho tro an ca
    meal_support, fulltime_days = calculate_meal_support(user_id, month, year)

    # 4. Tien phat
    total_penalty, late_count, violations = calculate_penalties(user_id, month, year)

    # 5. Tien thuong
    total_reward, rewards = calculate_rewards(user_id, month, year)

    # 6. Thuc linh
    net_salary = gross_salary + meal_support + total_reward - total_penalty - advance_payment

    # 7. Tao hoac cap nhat Payroll record
    payroll = Payroll.query.filter_by(
        user_id=user_id,
        month=month,
        year=year
    ).first()

    if not payroll:
        payroll = Payroll(user_id=user_id, month=month, year=year)
        db.session.add(payroll)

    payroll.total_work_hours = round(total_hours, 2)
    payroll.total_shifts = total_shifts
    payroll.late_count = late_count
    payroll.total_penalty = total_penalty
    payroll.total_reward = total_reward
    payroll.meal_support_amount = meal_support
    payroll.advance_payment = advance_payment
    payroll.gross_salary = round(gross_salary, 0)
    payroll.net_salary = round(net_salary, 0)
    payroll.status = PayrollStatus.DRAFT

    db.session.commit()

    return payroll


def calculate_all_payrolls(month, year):
    """
    Tinh luong cho tat ca nhan vien

    Returns:
        list: Danh sach Payroll objects
    """
    users = User.query.filter_by(status='active').all()
    payrolls = []

    for user in users:
        payroll = calculate_monthly_payroll(user.id, month, year)
        if payroll:
            payrolls.append(payroll)

    return payrolls


def get_payroll_summary(month, year):
    """
    Lay thong ke luong thang

    Returns:
        dict: Thong ke
    """
    payrolls = Payroll.query.filter_by(month=month, year=year).all()

    total_gross = sum(p.gross_salary for p in payrolls)
    total_net = sum(p.net_salary for p in payrolls)
    total_penalty = sum(p.total_penalty for p in payrolls)
    total_reward = sum(p.total_reward for p in payrolls)
    total_meal = sum(p.meal_support_amount for p in payrolls)

    approved_count = sum(1 for p in payrolls if p.status == PayrollStatus.APPROVED)
    paid_count = sum(1 for p in payrolls if p.status == PayrollStatus.PAID)

    return {
        'total_employees': len(payrolls),
        'total_gross': total_gross,
        'total_net': total_net,
        'total_penalty': total_penalty,
        'total_reward': total_reward,
        'total_meal': total_meal,
        'approved_count': approved_count,
        'paid_count': paid_count,
        'pending_count': len(payrolls) - approved_count - paid_count
    }
