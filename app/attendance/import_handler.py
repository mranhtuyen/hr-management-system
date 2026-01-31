"""
Module xu ly import file Excel cham cong tu may van tay

Format Excel mong doi:
| Ma NV | Ho ten | Ngay | Gio vao | Gio ra |
|-------|--------|------|---------|--------|
| 001   | Nguyen A | 2026-01-20 | 06:45 | 12:15 |
"""

from openpyxl import load_workbook
from datetime import datetime, time, timedelta
from app.models import (
    AttendanceRecord, User, WorkSchedule, ScheduleShift,
    ShiftType, db
)


def parse_time(value):
    """Chuyen doi gia tri thanh time object"""
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        # Thu parse cac format khac nhau
        for fmt in ['%H:%M:%S', '%H:%M', '%H.%M']:
            try:
                return datetime.strptime(value.strip(), fmt).time()
            except ValueError:
                continue
    return None


def parse_date(value):
    """Chuyen doi gia tri thanh date object"""
    if isinstance(value, datetime):
        return value.date()
    if hasattr(value, 'date'):
        return value.date()
    if isinstance(value, str):
        for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y']:
            try:
                return datetime.strptime(value.strip(), fmt).date()
            except ValueError:
                continue
    return None


def calculate_late_minutes(scheduled_start, actual_checkin):
    """
    Tinh so phut di muon
    Returns: So phut di muon (0 neu dung gio hoac som)
    """
    if actual_checkin is None or scheduled_start is None:
        return 0

    if actual_checkin <= scheduled_start:
        return 0

    # Chuyen sang datetime de tinh
    today = datetime.today().date()
    scheduled_dt = datetime.combine(today, scheduled_start)
    actual_dt = datetime.combine(today, actual_checkin)

    delta = actual_dt - scheduled_dt
    return int(delta.total_seconds() / 60)


def round_up_to_half_hour(t):
    """
    Lam tron len 30 phut
    VD: 7h06 -> 7h30, 7h35 -> 8h00
    """
    if t is None:
        return None

    minutes = t.minute
    if minutes <= 30:
        new_minute = 30
        new_hour = t.hour
    else:
        new_minute = 0
        new_hour = t.hour + 1
        if new_hour >= 24:
            new_hour = 23
            new_minute = 59

    return time(new_hour, new_minute, 0)


def calculate_work_hours(scheduled_start, scheduled_end, actual_checkin, late_minutes):
    """
    Tinh gio lam viec thuc te
    - Neu dung gio: Tinh theo lich
    - Neu di muon: Lam tron xuong
    """
    if scheduled_start is None or scheduled_end is None:
        return 0

    today = datetime.today().date()
    start_dt = datetime.combine(today, scheduled_start)
    end_dt = datetime.combine(today, scheduled_end)

    if late_minutes == 0:
        # Tinh theo lich
        delta = end_dt - start_dt
    else:
        # Lam tron len thoi gian bat dau
        rounded_start = round_up_to_half_hour(actual_checkin)
        if rounded_start:
            start_dt = datetime.combine(today, rounded_start)
        delta = end_dt - start_dt

    hours = delta.total_seconds() / 3600
    return max(0, hours)


def find_scheduled_shift(user_id, date, actual_checkin):
    """Tim ca lam viec da duoc phan cho NV"""
    # Lay tat ca shifts cua user trong ngay do
    shifts = db.session.query(ScheduleShift).join(WorkSchedule).filter(
        WorkSchedule.user_id == user_id,
        ScheduleShift.date == date,
        ScheduleShift.is_confirmed == True
    ).all()

    if not shifts:
        return None

    if len(shifts) == 1:
        return shifts[0]

    # Neu co nhieu ca, tim ca gan nhat voi thoi gian check-in
    if actual_checkin:
        closest_shift = None
        min_diff = float('inf')

        for shift in shifts:
            diff = abs(
                (datetime.combine(date, actual_checkin) -
                 datetime.combine(date, shift.shift_start_time)).total_seconds()
            )
            if diff < min_diff:
                min_diff = diff
                closest_shift = shift

        return closest_shift

    return shifts[0]


def import_attendance_excel(file_path):
    """
    Import file Excel cham cong

    Args:
        file_path: Duong dan file Excel

    Returns:
        dict: {
            'success': so record thanh cong,
            'errors': list loi,
            'records': list records da tao
        }
    """
    try:
        wb = load_workbook(file_path)
        ws = wb.active
    except Exception as e:
        return {'success': 0, 'errors': [f'Khong the doc file: {str(e)}'], 'records': []}

    records_created = 0
    errors = []
    records = []

    # Bo qua dong header
    for row_num, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        try:
            # Kiem tra dong trong
            if not row or not row[0]:
                continue

            employee_code = str(row[0]).strip()
            # employee_name = row[1]  # Khong can dung
            date = parse_date(row[2])
            checkin_time = parse_time(row[3])
            checkout_time = parse_time(row[4]) if len(row) > 4 else None

            if not date:
                errors.append(f'Dong {row_num}: Ngay khong hop le')
                continue

            # Tim user theo username
            user = User.query.filter_by(username=employee_code).first()
            if not user:
                # Thu tim theo full_name
                user = User.query.filter(User.full_name.ilike(f'%{employee_code}%')).first()

            if not user:
                errors.append(f'Dong {row_num}: Khong tim thay NV "{employee_code}"')
                continue

            # Tim ca lam viec da duoc phan
            scheduled_shift = find_scheduled_shift(user.id, date, checkin_time)

            if not scheduled_shift:
                errors.append(f'Dong {row_num}: Khong co lich cho NV {employee_code} ngay {date}')
                continue

            # Kiem tra da import chua
            existing = AttendanceRecord.query.filter_by(
                user_id=user.id,
                date=date,
                shift_type=scheduled_shift.shift_type
            ).first()

            if existing:
                errors.append(f'Dong {row_num}: Da import cho NV {employee_code} ngay {date}')
                continue

            # Tinh toan
            late_minutes = calculate_late_minutes(
                scheduled_shift.shift_start_time,
                checkin_time
            )

            work_hours = calculate_work_hours(
                scheduled_shift.shift_start_time,
                scheduled_shift.shift_end_time,
                checkin_time,
                late_minutes
            )

            # Check early bird (di truoc 6h55)
            early_bird_threshold = time(6, 55)
            is_early_bird = checkin_time and checkin_time < early_bird_threshold

            # Tao record
            record = AttendanceRecord(
                user_id=user.id,
                date=date,
                shift_type=scheduled_shift.shift_type,
                scheduled_start=scheduled_shift.shift_start_time,
                scheduled_end=scheduled_shift.shift_end_time,
                actual_checkin=checkin_time,
                actual_checkout=checkout_time,
                late_minutes=late_minutes,
                total_work_hours=round(work_hours, 2),
                is_late=(late_minutes > 0),
                is_early_bird=is_early_bird
            )

            db.session.add(record)
            records.append(record)
            records_created += 1

        except Exception as e:
            errors.append(f'Dong {row_num}: Loi - {str(e)}')

    if records_created > 0:
        db.session.commit()

    return {
        'success': records_created,
        'errors': errors,
        'records': records
    }
