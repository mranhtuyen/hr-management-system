"""
Module xu ly di muon va tinh tien phat

Quy tac phat moi thang:
- Lan 1: Muon < 5 phut -> Khong phat (Nhac nho)
- Lan 2: Phat 50,000d
- Lan 3+: Phat 100,000d/lan
"""

from datetime import datetime
from app.models import Violation, AttendanceRecord, User, ViolationType, Notification, db
from flask import current_app


def get_late_count_in_month(user_id, date):
    """Dem so lan di muon trong thang cua user"""
    month_start = date.replace(day=1)

    count = Violation.query.filter(
        Violation.user_id == user_id,
        Violation.type == ViolationType.LATE,
        Violation.date >= month_start,
        Violation.date <= date
    ).count()

    return count


def calculate_penalty(late_count, late_minutes):
    """
    Tinh tien phat dua vao so lan di muon trong thang

    Args:
        late_count: So lan di muon (tinh ca lan nay)
        late_minutes: So phut di muon

    Returns:
        int: Tien phat (VND)
    """
    # Lay cau hinh tu config hoac database
    try:
        first_penalty = current_app.config.get('FIRST_LATE_PENALTY', 0)
        second_penalty = current_app.config.get('SECOND_LATE_PENALTY', 50000)
        third_penalty = current_app.config.get('THIRD_LATE_PENALTY', 100000)
    except RuntimeError:
        # Khong co app context
        first_penalty = 0
        second_penalty = 50000
        third_penalty = 100000

    if late_count == 1:
        return first_penalty
    elif late_count == 2:
        return second_penalty
    else:
        return third_penalty


def create_late_notification(user, late_count, late_minutes, penalty):
    """Tao thong bao di muon cho NV"""
    if late_count == 1:
        title = "Nhac nho di muon"
        message = f"Ban di muon {late_minutes} phut. Day la lan dau trong thang, chua bi phat. Hay co gang di dung gio!"
    else:
        title = f"Canh bao di muon lan {late_count}"
        message = f"Ban di muon {late_minutes} phut. Day la lan {late_count} trong thang. Tien phat: {penalty:,.0f}d. De nghi tuan thu di lam dung gio."

    notification = Notification(
        user_id=user.id,
        title=title,
        message=message,
        type='late'
    )
    db.session.add(notification)


def process_late_record(attendance_record):
    """
    Xu ly 1 ban ghi di muon

    Args:
        attendance_record: AttendanceRecord object

    Returns:
        Violation object or None
    """
    if not attendance_record.is_late:
        return None

    user = User.query.get(attendance_record.user_id)
    if not user:
        return None

    # Dem so lan di muon trong thang (chua tinh lan nay)
    late_count = get_late_count_in_month(user.id, attendance_record.date) + 1

    # Tinh tien phat
    penalty = calculate_penalty(late_count, attendance_record.late_minutes)

    # Tao violation record
    violation = Violation(
        user_id=user.id,
        date=attendance_record.date,
        type=ViolationType.LATE,
        description=f"Di muon {attendance_record.late_minutes} phut (lan {late_count} trong thang)",
        penalty_amount=penalty,
        late_count_in_month=late_count
    )
    db.session.add(violation)

    # Tao thong bao
    create_late_notification(user, late_count, attendance_record.late_minutes, penalty)

    return violation


def process_daily_attendance(date=None):
    """
    Xu ly tat ca ban ghi di muon trong ngay

    Args:
        date: Ngay can xu ly (mac dinh la hom nay)

    Returns:
        dict: Ket qua xu ly
    """
    if date is None:
        date = datetime.now().date()

    # Lay cac ban ghi di muon chua xu ly
    late_records = AttendanceRecord.query.filter(
        AttendanceRecord.date == date,
        AttendanceRecord.is_late == True
    ).all()

    processed = 0
    errors = []

    for record in late_records:
        # Kiem tra da xu ly chua
        existing_violation = Violation.query.filter_by(
            user_id=record.user_id,
            date=record.date,
            type=ViolationType.LATE
        ).first()

        if existing_violation:
            continue

        try:
            violation = process_late_record(record)
            if violation:
                processed += 1
        except Exception as e:
            errors.append(f"Loi xu ly user {record.user_id}: {str(e)}")

    if processed > 0:
        db.session.commit()

    return {
        'date': date,
        'processed': processed,
        'errors': errors
    }


def get_monthly_late_summary(user_id, month, year):
    """
    Thong ke di muon trong thang cua user

    Returns:
        dict: {
            'total_late': So lan di muon,
            'total_minutes': Tong so phut muon,
            'total_penalty': Tong tien phat,
            'violations': List violations
        }
    """
    from datetime import date as date_type
    month_start = date_type(year, month, 1)
    if month == 12:
        month_end = date_type(year + 1, 1, 1)
    else:
        month_end = date_type(year, month + 1, 1)

    violations = Violation.query.filter(
        Violation.user_id == user_id,
        Violation.type == ViolationType.LATE,
        Violation.date >= month_start,
        Violation.date < month_end
    ).order_by(Violation.date).all()

    total_late = len(violations)
    total_penalty = sum(v.penalty_amount for v in violations)

    # Tinh tong phut muon tu attendance records
    attendance_records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == user_id,
        AttendanceRecord.is_late == True,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date < month_end
    ).all()

    total_minutes = sum(r.late_minutes for r in attendance_records)

    return {
        'total_late': total_late,
        'total_minutes': total_minutes,
        'total_penalty': total_penalty,
        'violations': violations
    }


def create_early_bird_reward(attendance_record):
    """
    Ghi nhan diem guong mau cho NV di som

    Args:
        attendance_record: AttendanceRecord object
    """
    from app.models import Reward, RewardType

    if not attendance_record.is_early_bird:
        return None

    # Kiem tra da ghi nhan chua
    existing = Reward.query.filter_by(
        user_id=attendance_record.user_id,
        type=RewardType.PUNCTUAL,
        week_start_date=attendance_record.date
    ).first()

    if existing:
        return None

    reward = Reward(
        user_id=attendance_record.user_id,
        week_start_date=attendance_record.date,
        type=RewardType.PUNCTUAL,
        description=f"Di lam som ngay {attendance_record.date}",
        reward_amount=0  # Khong thuong tien, chi ghi nhan
    )
    db.session.add(reward)

    return reward
