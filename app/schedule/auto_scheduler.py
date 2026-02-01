"""
Thuat toan xep lich tu dong theo 5 quy tac:
1. Moi ca = 2 nhan vien chinh
2. Them NV part-time vao gio dong (dua iPOS)
3. Moi NV nghi >= 1 ngay/tuan
4. Uu tien nguyen vong NV (theo thoi gian submit)
5. Can bang so ca giua cac NV
"""

from datetime import datetime, timedelta, time
from collections import defaultdict
from app.models import (
    User, WorkSchedule, ScheduleShift, CustomerTraffic,
    EmploymentType, ShiftType, ScheduleStatus, db
)


# Dinh nghia thoi gian cac ca
SHIFT_TIMES = {
    ShiftType.MORNING: (time(7, 0), time(12, 0)),
    ShiftType.AFTERNOON: (time(12, 0), time(18, 0)),
    ShiftType.EVENING: (time(18, 0), time(22, 0))
}


def auto_generate_schedule(week_start_date, staff_per_shift=2):
    """
    Xep lich tu dong cho 1 tuan
    Args:
        week_start_date: Ngay dau tuan (Monday)
        staff_per_shift: So nhan vien moi ca (mac dinh 2)
    Returns:
        dict: Ket qua xep lich
    """
    week_end_date = week_start_date + timedelta(days=6)

    # 1. Lay danh sach lich da dang ky (sap xep theo thoi gian submit)
    submitted_schedules = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == week_start_date,
        WorkSchedule.status == ScheduleStatus.SUBMITTED
    ).order_by(WorkSchedule.submitted_at).all()

    # 2. Lay danh sach nhan vien active (bao gom ca staff)
    from app.models import UserRole
    active_users = User.query.filter(
        User.status == 'active',
        User.role != UserRole.ADMIN  # Khong xep Admin
    ).all()

    # Neu khong co NV nao, lay tat ca nguoi da dang ky lich
    if not active_users:
        active_users = [s.user for s in submitted_schedules]

    fulltime_users = [u for u in active_users if u.employment_type == EmploymentType.FULL_TIME]
    parttime_users = [u for u in active_users if u.employment_type == EmploymentType.PART_TIME]

    # 3. Lay du lieu gio dong tu tuan truoc (bo qua neu khong co)
    try:
        peak_hours = get_peak_hours(week_start_date - timedelta(days=7))
    except:
        peak_hours = set()

    # 4. Khoi tao lich trong (7 ngay x 3 ca)
    week_schedule = initialize_empty_schedule(week_start_date)

    # 5. Theo doi so ca cua moi NV
    shift_count = defaultdict(int)
    days_worked = defaultdict(set)

    # 6. Xep theo nguyen vong cua NV da dang ky TRUOC
    # Chi xep vao ca NV da dang ky, TON TRONG nguyen vong
    for schedule in submitted_schedules:
        assign_parttime_shifts(schedule, week_schedule, shift_count, days_worked, staff_per_shift)

    # 7. Xep Full-time vao cac ca con trong - chi xep neu ho CHUA dang ky
    registered_user_ids = [s.user_id for s in submitted_schedules]
    for user in fulltime_users:
        if user.id not in registered_user_ids:
            assign_fulltime_shifts(user, week_schedule, week_start_date, shift_count, days_worked, staff_per_shift)

    # 8. Phan bo them NV vao gio dong (neu co du lieu)
    if peak_hours:
        assign_peak_hour_staff(week_schedule, peak_hours, parttime_users, shift_count, days_worked, staff_per_shift)

    # 9. Dam bao moi ca co nguoi (linh hoat theo so NV)
    fill_understaffed_shifts(week_schedule, active_users, shift_count, days_worked, staff_per_shift)

    # 10. Can bang so ca giua cac NV
    balance_shifts(week_schedule, shift_count)

    # 11. Luu vao database
    save_schedule_to_db(week_schedule, week_start_date, week_end_date)

    return {
        'success': True,
        'week_start': week_start_date,
        'week_end': week_end_date,
        'total_shifts_assigned': sum(shift_count.values()),
        'total_employees': len([u for u in shift_count if shift_count[u] > 0])
    }


def initialize_empty_schedule(week_start_date):
    """Khoi tao lich trong cho 7 ngay x 3 ca"""
    schedule = {}
    for day_offset in range(7):
        date = week_start_date + timedelta(days=day_offset)
        schedule[date] = {
            ShiftType.MORNING: [],
            ShiftType.AFTERNOON: [],
            ShiftType.EVENING: []
        }
    return schedule


def get_peak_hours(week_start_date):
    """Lay cac gio dong tu du lieu iPOS tuan truoc"""
    week_end_date = week_start_date + timedelta(days=6)

    peak_data = CustomerTraffic.query.filter(
        CustomerTraffic.date >= week_start_date,
        CustomerTraffic.date <= week_end_date,
        CustomerTraffic.is_peak_hour == True
    ).all()

    # Map hour_segment to shift_type
    peak_shifts = set()
    for p in peak_data:
        hour = int(p.hour_segment.split('h')[0])
        if 7 <= hour < 12:
            peak_shifts.add((p.date.weekday(), ShiftType.MORNING))
        elif 12 <= hour < 18:
            peak_shifts.add((p.date.weekday(), ShiftType.AFTERNOON))
        elif 18 <= hour < 22:
            peak_shifts.add((p.date.weekday(), ShiftType.EVENING))

    return peak_shifts


def assign_fulltime_shifts(user, week_schedule, week_start_date, shift_count, days_worked, staff_per_shift=2):
    """
    Xep lich cho nhan vien Full-time
    - Lam 6 ngay/tuan
    - Uu tien ca sang + chieu (8h/ngay)
    """
    # Xep 6 ngay (de 1 ngay nghi)
    days_to_work = 6
    assigned_days = 0

    for day_offset in range(7):
        if assigned_days >= days_to_work:
            break

        date = week_start_date + timedelta(days=day_offset)

        # Xep ca sang va chieu (8h)
        for shift_type in [ShiftType.MORNING, ShiftType.AFTERNOON]:
            if len(week_schedule[date][shift_type]) < staff_per_shift:
                week_schedule[date][shift_type].append(user)
                shift_count[user.id] += 1
                days_worked[user.id].add(date)

        assigned_days += 1


def assign_parttime_shifts(schedule, week_schedule, shift_count, days_worked, staff_per_shift=2):
    """
    Xep lich cho nhan vien theo nguyen vong da dang ky
    - Ap dung cho tat ca NV (khong chi part-time)
    - Dua vao lich da dang ky
    - TON TRONG nguyen vong cua NV: chi xep vao ca ho da dang ky
    """
    user = schedule.user

    for shift in schedule.shifts:
        # Xep tat ca shifts da dang ky (khong chi preferred)
        date = shift.date
        shift_type = shift.shift_type

        # Kiem tra date co trong week_schedule khong
        if date not in week_schedule:
            continue

        # Kiem tra ca con cho khong - ton trong staff_per_shift
        if len(week_schedule[date][shift_type]) < staff_per_shift:
            # Kiem tra user chua co trong ca nay
            if user not in week_schedule[date][shift_type]:
                # Kiem tra nguoi nay chua lam qua nhieu ca
                if shift_count[user.id] < 18:  # Toi da 18 ca/tuan (linh hoat)
                    week_schedule[date][shift_type].append(user)
                    shift_count[user.id] += 1
                    days_worked[user.id].add(date)


def assign_peak_hour_staff(week_schedule, peak_hours, parttime_users, shift_count, days_worked, staff_per_shift=2):
    """Them NV vao gio dong"""
    max_staff = staff_per_shift + 1  # Them 1 nguoi cho gio dong
    for weekday, shift_type in peak_hours:
        for date, shifts in week_schedule.items():
            if date.weekday() == weekday:
                current_staff = len(shifts[shift_type])
                if current_staff < max_staff:
                    # Tim NV part-time co the lam
                    for user in sorted(parttime_users, key=lambda u: shift_count[u.id]):
                        if user not in shifts[shift_type]:
                            # Dam bao NV van co ngay nghi
                            if len(days_worked[user.id]) < 6:
                                shifts[shift_type].append(user)
                                shift_count[user.id] += 1
                                days_worked[user.id].add(date)
                                break


def fill_understaffed_shifts(week_schedule, all_users, shift_count, days_worked, staff_per_shift=2):
    """Dam bao moi ca co du nguoi theo cau hinh"""
    active_users = [u for u in all_users if u.status == 'active']
    total_active = len(active_users)

    # Neu chi co it NV, cho phep it nguoi hon/ca
    if total_active <= 3:
        min_staff = 1
    else:
        min_staff = min(staff_per_shift, total_active // 3)  # Dam bao du nguoi cho 3 ca

    for date, shifts in week_schedule.items():
        for shift_type, staff_list in shifts.items():
            while len(staff_list) < min_staff:
                # Tim NV co the lam (uu tien nguoi it ca nhat)
                # Neu it NV, bo qua rang buoc 6 ngay/tuan
                if total_active <= 3:
                    available_users = [
                        u for u in active_users
                        if u not in staff_list
                    ]
                else:
                    available_users = [
                        u for u in active_users
                        if u not in staff_list
                        and len(days_worked[u.id]) < 6
                    ]

                if not available_users:
                    break

                # Chon nguoi it ca nhat
                user = min(available_users, key=lambda u: shift_count[u.id])
                staff_list.append(user)
                shift_count[user.id] += 1
                days_worked[user.id].add(date)


def balance_shifts(week_schedule, shift_count):
    """Can bang so ca giua cac NV (chenh lech toi da 2 ca)"""
    if not shift_count:
        return

    avg_shifts = sum(shift_count.values()) / len(shift_count)

    # Tim NV co qua nhieu ca va qua it ca
    overloaded = [uid for uid, count in shift_count.items() if count > avg_shifts + 2]
    underloaded = [uid for uid, count in shift_count.items() if count < avg_shifts - 2]

    # TODO: Implement shift swapping if needed
    # Hien tai chi canh bao, khong tu dong swap
    pass


def save_schedule_to_db(week_schedule, week_start_date, week_end_date):
    """Luu lich vao database"""
    for date, shifts in week_schedule.items():
        for shift_type, staff_list in shifts.items():
            for user in staff_list:
                # Tim hoac tao WorkSchedule cho user
                ws = WorkSchedule.query.filter_by(
                    user_id=user.id,
                    week_start_date=week_start_date
                ).first()

                if not ws:
                    ws = WorkSchedule(
                        user_id=user.id,
                        week_start_date=week_start_date,
                        week_end_date=week_end_date,
                        status=ScheduleStatus.APPROVED,
                        approved_at=datetime.now()
                    )
                    db.session.add(ws)
                    db.session.flush()
                else:
                    # Cap nhat trang thai APPROVED neu chua
                    if ws.status != ScheduleStatus.APPROVED:
                        ws.status = ScheduleStatus.APPROVED
                        ws.approved_at = datetime.now()

                # Tim hoac tao ScheduleShift
                shift_start, shift_end = SHIFT_TIMES[shift_type]
                existing_shift = ScheduleShift.query.filter_by(
                    schedule_id=ws.id,
                    date=date,
                    shift_type=shift_type
                ).first()

                if existing_shift:
                    # Cap nhat shift hien tai thanh confirmed
                    existing_shift.is_confirmed = True
                else:
                    # Tao shift moi
                    shift = ScheduleShift(
                        schedule_id=ws.id,
                        date=date,
                        shift_type=shift_type,
                        shift_start_time=shift_start,
                        shift_end_time=shift_end,
                        is_preferred=False,
                        is_confirmed=True
                    )
                    db.session.add(shift)

    db.session.commit()


def check_schedule_constraints(week_schedule):
    """Kiem tra cac rang buoc"""
    errors = []

    for date, shifts in week_schedule.items():
        for shift_type, staff_list in shifts.items():
            if len(staff_list) < 2:
                errors.append(f'{date} - {shift_type.value}: Chi co {len(staff_list)} nguoi (can 2)')

    return errors
