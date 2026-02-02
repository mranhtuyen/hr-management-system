"""
Thuat toan xep lich tu dong voi che do DRAFT:
- KHONG GHI DE lich dang ky cua NV (shift_source='employee')
- Tao lich NHAP (shift_source='system', draft_status='draft')
- Quan ly xem va sua truoc khi luu chinh thuc
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


def auto_generate_schedule(week_start_date, staff_per_shift=2, selected_staff_ids=None, create_draft=True):
    """
    Xep lich tu dong cho 1 tuan - VERSION MOI VOI DRAFT

    Args:
        week_start_date: Ngay dau tuan (Monday)
        staff_per_shift: So nhan vien moi ca (2, 3, hoac 4)
        selected_staff_ids: Chi xep cho cac NV nay (None = tat ca)
        create_draft: True = tao lich nhap, False = luu truc tiep

    Returns:
        dict: Ket qua xep lich
    """
    week_end_date = week_start_date + timedelta(days=6)

    # 1. XOA LICH NHAP CU (neu co) - Chi xoa draft, KHONG xoa lich NV dang ky
    if create_draft:
        ScheduleShift.query.filter(
            ScheduleShift.date >= week_start_date,
            ScheduleShift.date <= week_end_date,
            ScheduleShift.shift_source == 'system',
            ScheduleShift.draft_status == 'draft'
        ).delete()
        db.session.commit()

    # 2. LAY DANH SACH LICH DA DANG KY (chi tu NV - shift_source='employee' hoac None)
    submitted_schedules = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == week_start_date,
        WorkSchedule.status.in_([ScheduleStatus.SUBMITTED, ScheduleStatus.APPROVED])
    ).order_by(WorkSchedule.submitted_at).all()

    # Loc theo selected_staff_ids neu co
    if selected_staff_ids:
        submitted_schedules = [s for s in submitted_schedules if s.user_id in selected_staff_ids]

    # 3. KHOI TAO LICH TRONG (7 ngay x 3 ca)
    week_schedule = {}
    for day_offset in range(7):
        date = week_start_date + timedelta(days=day_offset)
        week_schedule[date] = {
            ShiftType.MORNING: [],
            ShiftType.AFTERNOON: [],
            ShiftType.EVENING: []
        }

    # 4. THEO DOI SO CA CUA MOI NV
    shift_count = defaultdict(int)
    days_worked = defaultdict(set)

    # 5. XEP THEO NGUYEN VONG CUA NV DA DANG KY
    # Chi xep vao ca NV da dang ky, TON TRONG nguyen vong
    for schedule in submitted_schedules:
        user = schedule.user

        # Lay shifts ma NV da dang ky (chi lay shift_source='employee' hoac None)
        employee_shifts = [s for s in schedule.shifts
                          if s.shift_source in ('employee', None) or s.shift_source == 'employee']

        # Neu khong co shift nao, skip
        if not employee_shifts:
            # Co the NV chua dang ky shift nao, lay tat ca shifts
            employee_shifts = schedule.shifts

        for shift in employee_shifts:
            date = shift.date
            shift_type = shift.shift_type

            if date not in week_schedule:
                continue

            # Kiem tra ca con cho khong
            if len(week_schedule[date][shift_type]) < staff_per_shift:
                # Kiem tra user chua co trong ca nay
                if user not in week_schedule[date][shift_type]:
                    # Kiem tra nguoi nay chua lam qua nhieu ca
                    if shift_count[user.id] < 18:  # Toi da 18 ca/tuan
                        week_schedule[date][shift_type].append(user)
                        shift_count[user.id] += 1
                        days_worked[user.id].add(date)

    # 6. LUU VAO DATABASE
    results = []

    for date, shifts in week_schedule.items():
        for shift_type, staff_list in shifts.items():
            for user in staff_list:
                # Tim WorkSchedule cua user
                ws = WorkSchedule.query.filter_by(
                    user_id=user.id,
                    week_start_date=week_start_date
                ).first()

                if not ws:
                    ws = WorkSchedule(
                        user_id=user.id,
                        week_start_date=week_start_date,
                        week_end_date=week_end_date,
                        status=ScheduleStatus.SUBMITTED,
                        submitted_at=datetime.now()
                    )
                    db.session.add(ws)
                    db.session.flush()

                # Kiem tra shift da ton tai chua (chi kiem tra system draft)
                shift_start, shift_end = SHIFT_TIMES[shift_type]

                existing_draft = ScheduleShift.query.filter_by(
                    schedule_id=ws.id,
                    date=date,
                    shift_type=shift_type,
                    shift_source='system',
                    draft_status='draft'
                ).first()

                if not existing_draft:
                    # Tao shift moi
                    new_shift = ScheduleShift(
                        schedule_id=ws.id,
                        date=date,
                        shift_type=shift_type,
                        shift_start_time=shift_start,
                        shift_end_time=shift_end,
                        is_preferred=True,
                        is_confirmed=not create_draft,  # True neu luu truc tiep
                        is_and_condition=False,
                        shift_source='system',
                        draft_status='draft' if create_draft else 'final'
                    )
                    db.session.add(new_shift)
                    results.append(new_shift)

    db.session.commit()

    return {
        'success': True,
        'week_start': week_start_date,
        'week_end': week_end_date,
        'total_shifts': len(results),
        'total_employees': len(set(shift_count.keys()))
    }


def get_peak_hours(week_start_date):
    """Lay cac gio dong tu du lieu iPOS tuan truoc"""
    week_end_date = week_start_date + timedelta(days=6)

    peak_data = CustomerTraffic.query.filter(
        CustomerTraffic.date >= week_start_date,
        CustomerTraffic.date <= week_end_date,
        CustomerTraffic.is_peak_hour == True
    ).all()

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


def check_schedule_constraints(week_schedule):
    """Kiem tra cac rang buoc"""
    errors = []

    for date, shifts in week_schedule.items():
        for shift_type, staff_list in shifts.items():
            if len(staff_list) < 2:
                errors.append(f'{date} - {shift_type.value}: Chi co {len(staff_list)} nguoi (can 2)')

    return errors
