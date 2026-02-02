from flask import render_template, redirect, url_for, flash, request, session, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta, time
from app.schedule import bp
from app.schedule.forms import WeeklyScheduleForm
from app.schedule.auto_scheduler import auto_generate_schedule
from app.models import (
    WorkSchedule, ScheduleShift, User, ShiftType, ScheduleStatus,
    UserRole, EmploymentType, ScheduleSettings, SystemConfig, db
)
from app.auth.routes import manager_required, admin_required


# Dinh nghia thoi gian mac dinh cac ca
DEFAULT_SHIFT_TIMES = {
    ShiftType.MORNING: (time(7, 0), time(12, 0)),
    ShiftType.AFTERNOON: (time(12, 0), time(18, 0)),
    ShiftType.EVENING: (time(18, 0), time(22, 0))
}

# Alias de tuong thich voi code cu
SHIFT_TIMES = DEFAULT_SHIFT_TIMES


def get_shift_settings():
    """Lay cai dat ca lam viec tu SystemConfig"""
    settings = {
        'morning_color': '#FEF3C7',  # Mac dinh yellow
        'afternoon_color': '#FED7AA',  # Mac dinh orange
        'evening_color': '#C7D2FE',  # Mac dinh indigo
        'morning_start': '07:00',
        'morning_end': '12:00',
        'afternoon_start': '12:00',
        'afternoon_end': '18:00',
        'evening_start': '18:00',
        'evening_end': '22:00',
    }

    # Load tu SystemConfig
    for config in SystemConfig.query.filter(SystemConfig.key.like('shift_%')).all():
        key = config.key.replace('shift_', '')
        settings[key] = config.value

    return settings


def get_dynamic_shift_times():
    """Lay thoi gian ca tu SystemConfig (tra ve datetime.time objects)"""
    settings = get_shift_settings()

    def parse_time(time_str):
        try:
            parts = time_str.split(':')
            return time(int(parts[0]), int(parts[1]))
        except:
            return None

    return {
        ShiftType.MORNING: (
            parse_time(settings['morning_start']) or time(7, 0),
            parse_time(settings['morning_end']) or time(12, 0)
        ),
        ShiftType.AFTERNOON: (
            parse_time(settings['afternoon_start']) or time(12, 0),
            parse_time(settings['afternoon_end']) or time(18, 0)
        ),
        ShiftType.EVENING: (
            parse_time(settings['evening_start']) or time(18, 0),
            parse_time(settings['evening_end']) or time(22, 0)
        ),
    }


def get_next_week_dates():
    """Lay ngay dau va cuoi tuan sau"""
    today = datetime.now().date()
    # Tim Monday cua tuan sau
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)
    next_sunday = next_monday + timedelta(days=6)
    return next_monday, next_sunday


def is_registration_open():
    """Kiem tra dang ky lich con mo khong - CHO PHEP DANG KY BAT KY LUC NAO TRUOC DEADLINE"""
    now = datetime.now()
    settings = ScheduleSettings.get_settings()

    # Lay cau hinh deadline
    deadline_day = settings.deadline_day  # 0=Mon, 1=Tue, ... 5=Sat, 6=Sun
    deadline_hour = settings.deadline_hour
    deadline_minute = settings.deadline_minute

    # LOGIC MOI: Cho phep dang ky bat ky luc nao TRUOC deadline
    # Deadline thuong la Thu 7 (weekday=5) luc 18h
    current_weekday = now.weekday()

    # Neu chua den ngay deadline -> LUON MO
    if current_weekday < deadline_day:
        return True

    # Neu dung ngay deadline -> kiem tra gio
    if current_weekday == deadline_day:
        if now.hour < deadline_hour:
            return True
        elif now.hour == deadline_hour and now.minute < deadline_minute:
            return True
        # Da qua deadline
        return False

    # Neu da qua ngay deadline (VD: Chu Nhat) -> DONG
    # Nhung van cho phep dang ky neu la tuan moi
    return False


def check_late_registration():
    """Kiem tra xem dang ky co muon khong"""
    now = datetime.now()
    settings = ScheduleSettings.get_settings()

    deadline_day = settings.deadline_day
    deadline_hour = settings.deadline_hour
    deadline_minute = settings.deadline_minute

    # Neu la ngay deadline va qua gio deadline
    if now.weekday() == deadline_day:
        if now.hour > deadline_hour:
            return True, settings.late_registration_message
        elif now.hour == deadline_hour and now.minute >= deadline_minute:
            return True, settings.late_registration_message

    return False, None


@bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Dang ky lich lam viec - ho tro nhieu tuan"""
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())

    # Lay week parameter (0 = tuan hien tai, 1 = tuan sau, 2 = tuan sau nua...)
    week_param = request.args.get('week', 1, type=int)

    # Tinh week_start va week_end dua tren week_param
    week_start = current_week_start + timedelta(weeks=week_param)
    week_end = week_start + timedelta(days=6)
    is_current_week = (week_param == 0)

    # Kiem tra da dang ky chua
    existing_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=week_start
    ).first()

    # Neu tuan nay da APPROVED -> huong dan dang ky tuan ke tiep
    if existing_schedule and existing_schedule.status == ScheduleStatus.APPROVED:
        next_week_param = week_param + 1
        next_week_start = current_week_start + timedelta(weeks=next_week_param)
        next_week_end = next_week_start + timedelta(days=6)

        # Kiem tra tuan ke tiep da dang ky chua
        next_schedule = WorkSchedule.query.filter_by(
            user_id=current_user.id,
            week_start_date=next_week_start
        ).first()

        if not next_schedule or next_schedule.status == ScheduleStatus.DRAFT:
            flash(f'Lich tuan {week_start.strftime("%d/%m")} - {week_end.strftime("%d/%m")} da duoc duyet. '
                  f'Ban co the dang ky tuan {next_week_start.strftime("%d/%m")} - {next_week_end.strftime("%d/%m")}.', 'info')
            return redirect(url_for('schedule.register', week=next_week_param))
        else:
            flash('Lich cua ban da duoc duyet.', 'info')
            return redirect(url_for('schedule.my_approved_schedule', week=week_param))

    # Kiem tra cau hinh cho phep sua tuan hien tai
    settings = ScheduleSettings.get_settings()
    allow_current_week = getattr(settings, 'allow_current_week_edit', True)

    if is_current_week:
        # Sua lich tuan hien tai
        if not allow_current_week:
            flash('Cau hinh he thong khong cho phep sua lich tuan hien tai.', 'warning')
            return redirect(url_for('schedule.my_schedule', week=0))
        # Chi cho phep sua khi lich bi tra lai (DRAFT)
        if not (existing_schedule and existing_schedule.status == ScheduleStatus.DRAFT):
            flash('Chi co the sua lich tuan hien tai khi bi quan ly tra lai.', 'warning')
            return redirect(url_for('schedule.my_schedule', week=0))
    else:
        # Dang ky tuan tuong lai - luon cho phep (khong kiem tra deadline qua nghiem ngat)
        # Chi hien canh bao neu qua deadline
        if not is_registration_open():
            is_late, late_msg = check_late_registration()
            if is_late and late_msg:
                flash(late_msg, 'warning')

    form = WeeklyScheduleForm()

    # Pre-fill form voi shifts hien tai neu dang sua
    if existing_schedule and request.method == 'GET':
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        for shift in existing_schedule.shifts:
            day_offset = (shift.date - week_start).days
            if 0 <= day_offset < 7:
                day_name = day_names[day_offset]
                day_form = getattr(form, day_name)
                if shift.shift_type == ShiftType.MORNING:
                    day_form.morning.data = True
                elif shift.shift_type == ShiftType.AFTERNOON:
                    day_form.afternoon.data = True
                elif shift.shift_type == ShiftType.EVENING:
                    day_form.evening.data = True
                if shift.is_and_condition:
                    day_form.is_and_condition.data = True

    if form.validate_on_submit():
        # Tao hoac cap nhat WorkSchedule
        if not existing_schedule:
            schedule = WorkSchedule(
                user_id=current_user.id,
                week_start_date=week_start,
                week_end_date=week_end,
                status=ScheduleStatus.SUBMITTED,
                submitted_at=datetime.now()
            )
            db.session.add(schedule)
            db.session.flush()
        else:
            schedule = existing_schedule
            schedule.status = ScheduleStatus.SUBMITTED
            schedule.submitted_at = datetime.now()
            # Xoa shifts cu
            ScheduleShift.query.filter_by(schedule_id=schedule.id).delete()

        # Luu cac shifts
        day_forms = [
            ('monday', 0), ('tuesday', 1), ('wednesday', 2), ('thursday', 3),
            ('friday', 4), ('saturday', 5), ('sunday', 6)
        ]

        for day_name, day_offset in day_forms:
            day_form = getattr(form, day_name)
            shift_date = week_start + timedelta(days=day_offset)
            is_and = day_form.is_and_condition.data

            # Lay thoi gian ca tu SystemConfig
            dynamic_shift_times = get_dynamic_shift_times()

            for shift_type, field_name in [(ShiftType.MORNING, 'morning'),
                                           (ShiftType.AFTERNOON, 'afternoon'),
                                           (ShiftType.EVENING, 'evening')]:
                if getattr(day_form, field_name).data:
                    shift_start, shift_end = dynamic_shift_times[shift_type]
                    shift = ScheduleShift(
                        schedule_id=schedule.id,
                        date=shift_date,
                        shift_type=shift_type,
                        shift_start_time=shift_start,
                        shift_end_time=shift_end,
                        is_preferred=True,
                        is_confirmed=False,
                        is_and_condition=is_and
                    )
                    db.session.add(shift)

        db.session.commit()
        flash('Da gui dang ky lich thanh cong!', 'success')
        return redirect(url_for('schedule.my_schedule', week=0 if is_current_week else 1))

    return render_template('schedule/register.html',
                           form=form,
                           week_start=week_start,
                           week_end=week_end,
                           week_param=week_param,
                           is_current_week=is_current_week,
                           is_open=is_registration_open() or (existing_schedule and existing_schedule.status == ScheduleStatus.DRAFT) or is_current_week,
                           existing_schedule=existing_schedule,
                           timedelta=timedelta)


@bp.route('/resubmit-current-week', methods=['POST'])
@login_required
def resubmit_current_week():
    """Day lai lich tuan hien tai len Quan ly"""
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())

    # Kiem tra cau hinh
    settings = ScheduleSettings.get_settings()
    allow_current_week = getattr(settings, 'allow_current_week_edit', True)

    if not allow_current_week:
        flash('Cau hinh he thong khong cho phep day lai lich tuan hien tai.', 'warning')
        return redirect(url_for('schedule.my_schedule', week=0))

    # Tim lich tuan hien tai
    existing_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=current_week_start
    ).first()

    if not existing_schedule:
        flash('Khong tim thay lich tuan hien tai.', 'warning')
        return redirect(url_for('schedule.my_schedule', week=0))

    if existing_schedule.status != ScheduleStatus.DRAFT:
        flash('Chi co the day lai lich khi trang thai la "Nhap".', 'warning')
        return redirect(url_for('schedule.my_schedule', week=0))

    # Chuyen trang thai tu DRAFT sang SUBMITTED
    existing_schedule.status = ScheduleStatus.SUBMITTED
    existing_schedule.submitted_at = datetime.now()
    db.session.commit()

    flash('Da day lich tuan hien tai len Quan ly thanh cong!', 'success')
    return redirect(url_for('schedule.my_schedule', week=0))


@bp.route('/reset-my-schedule', methods=['POST'])
@login_required
def reset_my_schedule():
    """Cho phep NV reset lich dang ky de lam lai tu dau"""
    week_start, week_end = get_next_week_dates()

    existing_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=week_start
    ).first()

    if existing_schedule:
        # Chi cho phep reset neu chua duoc duyet
        if existing_schedule.status == ScheduleStatus.APPROVED:
            flash('Lich da duoc duyet, khong the reset.', 'warning')
            return redirect(url_for('schedule.register'))

        # Xoa tat ca shifts
        ScheduleShift.query.filter_by(schedule_id=existing_schedule.id).delete()
        # Xoa schedule
        db.session.delete(existing_schedule)
        db.session.commit()
        flash('Da reset lich thanh cong. Ban co the dang ky lai tu dau.', 'success')
    else:
        flash('Khong co lich de reset.', 'info')

    return redirect(url_for('schedule.register'))


@bp.route('/my-schedule')
@login_required
def my_schedule():
    """Xem lich lam viec cua ban than - ho tro xem nhieu tuan"""
    today = datetime.now().date()

    # Lay week_offset tu params (0 = tuan hien tai, 1 = tuan sau, -1 = tuan truoc)
    week_offset = request.args.get('week', 0, type=int)

    # Tinh tuan dang xem
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # Xac dinh loai tuan
    is_past_week = week_end < today
    is_current_week = week_start <= today <= week_end
    is_future_week = week_start > today

    # Lay lich cua tuan dang xem
    my_schedule_data = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=week_start
    ).first()

    # Lay shifts - hien thi TAT CA shifts (ke ca chua confirmed) de NV thay lich da dang ky
    my_shifts = []
    if my_schedule_data:
        my_shifts = ScheduleShift.query.filter_by(
            schedule_id=my_schedule_data.id
        ).order_by(ScheduleShift.date).all()

    # Kiem tra co the sua lich khong
    # - Tuan da qua: KHONG SUA DUOC
    # - Tuan hien tai: SUA DUOC neu chua duyet
    # - Tuan sap toi: SUA DUOC neu chua duyet
    can_edit = False
    if not is_past_week:
        if my_schedule_data:
            can_edit = my_schedule_data.status != ScheduleStatus.APPROVED
        else:
            can_edit = True  # Chua co lich -> co the dang ky moi

    return render_template('schedule/my_schedule.html',
                           my_schedule=my_schedule_data,
                           my_shifts=my_shifts,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset,
                           today=today,
                           is_past_week=is_past_week,
                           is_current_week=is_current_week,
                           is_future_week=is_future_week,
                           can_edit=can_edit,
                           timedelta=timedelta)


@bp.route('/my-approved-schedule')
@login_required
def my_approved_schedule():
    """Xem lich da duoc duyet - lich ma Quan ly da xep cho NV"""
    today = datetime.now().date()

    # Lay week_offset tu params
    week_offset = request.args.get('week', 0, type=int)

    # Tinh tuan dang xem
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # Xac dinh loai tuan
    is_past_week = week_end < today
    is_current_week = week_start <= today <= week_end
    is_future_week = week_start > today

    # Lay lich cua tuan dang xem
    my_schedule_data = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=week_start
    ).first()

    # Chi lay shifts DA CONFIRMED (da duoc Quan ly duyet)
    approved_shifts = []
    if my_schedule_data:
        approved_shifts = ScheduleShift.query.filter_by(
            schedule_id=my_schedule_data.id,
            is_confirmed=True
        ).order_by(ScheduleShift.date, ScheduleShift.shift_type).all()

    # To chuc theo ngay va ca de hien thi dang bang
    schedule_by_date = {}
    for i in range(7):
        date = week_start + timedelta(days=i)
        schedule_by_date[date] = {
            'morning': [],
            'afternoon': [],
            'evening': []
        }

    for shift in approved_shifts:
        if shift.date in schedule_by_date:
            shift_type = shift.shift_type.value
            schedule_by_date[shift.date][shift_type].append(shift)

    # Lay shift settings de hien thi mau sac
    shift_settings = get_shift_settings()

    return render_template('schedule/my_approved_schedule.html',
                           my_schedule=my_schedule_data,
                           approved_shifts=approved_shifts,
                           schedule_by_date=schedule_by_date,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset,
                           today=today,
                           is_past_week=is_past_week,
                           is_current_week=is_current_week,
                           is_future_week=is_future_week,
                           shift_settings=shift_settings,
                           timedelta=timedelta)


@bp.route('/view')
@login_required
@manager_required
def view():
    """Xem lich lam viec cua tat ca NV (Admin/Manager)"""
    # Lay tuan can xem
    week_offset = request.args.get('week', 0, type=int)
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # Lay tat ca shifts trong tuan
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

    # Nhom theo ngay va ca (dung string keys cho template)
    schedule_grid = {}
    for day_offset in range(7):
        date = week_start + timedelta(days=day_offset)
        schedule_grid[date] = {
            'morning': [],
            'afternoon': [],
            'evening': []
        }

    for shift, user in shifts:
        shift_type_str = shift.shift_type.value  # Convert enum to string
        schedule_grid[shift.date][shift_type_str].append({
            'user': user,
            'shift': shift
        })

    # Lay danh sach NV de them ca
    staff_list = User.query.filter_by(status='active').order_by(User.full_name).all()

    return render_template('schedule/view.html',
                           schedule_grid=schedule_grid,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset,
                           staff_list=staff_list,
                           timedelta=timedelta)


@bp.route('/review')
@login_required
@manager_required
def review():
    """Duyet lich dang ky cua NV - ho tro xem nhieu tuan"""
    today = datetime.now().date()

    # Lay week_offset tu params (0 = tuan hien tai, 1 = tuan sau, -1 = tuan truoc)
    week_offset = request.args.get('week', 0, type=int)

    # Tinh tuan dang xem
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # Xac dinh loai tuan
    is_past_week = week_end < today
    is_current_week = week_start <= today <= week_end
    is_future_week = week_start > today

    # Lay cac lich chua duyet
    pending_schedules = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == week_start,
        WorkSchedule.status == ScheduleStatus.SUBMITTED
    ).order_by(WorkSchedule.submitted_at).all()

    # Lay cac lich da duyet
    approved_schedules = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == week_start,
        WorkSchedule.status == ScheduleStatus.APPROVED
    ).all()

    # Thong ke NV chua dang ky
    all_staff = User.query.filter_by(status='active', role=UserRole.STAFF).all()
    registered_user_ids = [s.user_id for s in pending_schedules + approved_schedules]
    not_registered = [u for u in all_staff if u.id not in registered_user_ids]

    # Lay shift settings tu SystemConfig
    shift_settings = get_shift_settings()

    return render_template('schedule/review.html',
                           pending_schedules=pending_schedules,
                           approved_schedules=approved_schedules,
                           not_registered=not_registered,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset,
                           is_past_week=is_past_week,
                           is_current_week=is_current_week,
                           is_future_week=is_future_week,
                           shift_settings=shift_settings,
                           timedelta=timedelta)


@bp.route('/approve/<int:schedule_id>', methods=['POST'])
@login_required
@manager_required
def approve(schedule_id):
    """Duyet lich cho 1 NV"""
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    schedule.status = ScheduleStatus.APPROVED
    schedule.approved_at = datetime.now()
    schedule.approved_by = current_user.id

    # Confirm tat ca shifts
    for shift in schedule.shifts:
        shift.is_confirmed = True

    db.session.commit()
    flash(f'Da duyet lich cho {schedule.user.full_name}', 'success')
    return redirect(url_for('schedule.review'))


@bp.route('/return/<int:schedule_id>', methods=['POST'])
@login_required
@manager_required
def return_schedule(schedule_id):
    """Tra lich lai cho NV de sua"""
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    schedule.status = ScheduleStatus.DRAFT
    schedule.approved_at = None
    schedule.approved_by = None

    # Unconfirm tat ca shifts
    for shift in schedule.shifts:
        shift.is_confirmed = False

    db.session.commit()
    flash(f'Da tra lich lai cho {schedule.user.full_name} de sua', 'info')
    return redirect(url_for('schedule.review'))


@bp.route('/unapprove/<int:schedule_id>', methods=['POST'])
@login_required
@manager_required
def unapprove(schedule_id):
    """Huy duyet lich - cho phep NV sua lai"""
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    schedule.status = ScheduleStatus.DRAFT
    schedule.approved_at = None
    schedule.approved_by = None

    # Unconfirm tat ca shifts
    for shift in schedule.shifts:
        shift.is_confirmed = False

    db.session.commit()
    flash(f'Da huy duyet lich cua {schedule.user.full_name}', 'info')
    return redirect(url_for('schedule.review'))


@bp.route('/edit-schedule/<int:schedule_id>', methods=['GET', 'POST'])
@login_required
@manager_required
def edit_schedule(schedule_id):
    """Admin sua lich cua NV truoc khi duyet"""
    schedule = WorkSchedule.query.get_or_404(schedule_id)
    week_start = schedule.week_start_date
    week_end = schedule.week_end_date

    if request.method == 'POST':
        # Xoa shifts cu
        ScheduleShift.query.filter_by(schedule_id=schedule.id).delete()

        # Luu shifts moi
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        # Lay thoi gian ca tu SystemConfig
        dynamic_shift_times = get_dynamic_shift_times()

        for day_offset, day_name in enumerate(day_names):
            shift_date = week_start + timedelta(days=day_offset)
            for shift_type_str in ['morning', 'afternoon', 'evening']:
                field_name = f'{day_name}_{shift_type_str}'
                if request.form.get(field_name):
                    shift_type = ShiftType(shift_type_str)
                    shift_start, shift_end = dynamic_shift_times[shift_type]
                    shift = ScheduleShift(
                        schedule_id=schedule.id,
                        date=shift_date,
                        shift_type=shift_type,
                        shift_start_time=shift_start,
                        shift_end_time=shift_end,
                        is_preferred=True,
                        is_confirmed=False
                    )
                    db.session.add(shift)

        db.session.commit()
        flash(f'Da cap nhat lich cho {schedule.user.full_name}', 'success')
        return redirect(url_for('schedule.review'))

    return render_template('schedule/edit_schedule.html',
                           schedule=schedule,
                           week_start=week_start,
                           week_end=week_end,
                           timedelta=timedelta)


@bp.route('/auto-generate', methods=['GET', 'POST'])
@login_required
@admin_required
def auto_generate():
    """Chay thuat toan xep lich tu dong (Admin only - GET/POST)"""
    week_start, week_end = get_next_week_dates()

    # Lay so nhan vien moi ca tu form
    staff_per_shift = request.form.get('staff_per_shift', type=int, default=2)
    if staff_per_shift < 1:
        staff_per_shift = 2
    if staff_per_shift > 4:
        staff_per_shift = 4

    try:
        result = auto_generate_schedule(week_start, staff_per_shift=staff_per_shift)
        if result and result.get('success'):
            flash(f'Da xep lich tu dong thanh cong! Tuan {week_start.strftime("%d/%m")} - {week_end.strftime("%d/%m/%Y")}. Tong cong {result.get("total_shifts_assigned", 0)} ca ({staff_per_shift} NV/ca).', 'success')
        else:
            flash('Xep lich tu dong hoan thanh nhung co the chua toi uu.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Loi khi xep lich tu dong: {str(e)}', 'danger')

    return redirect(url_for('schedule.review'))


@bp.route('/reset-schedule', methods=['POST'])
@login_required
@admin_required
def reset_schedule():
    """Reset lich da xep de xep lai bang tay"""
    # Lay week_offset tu form
    week_offset = request.form.get('week_offset', type=int, default=0)
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    try:
        # Chi dat is_confirmed = False cho cac shifts, khong xoa
        # Giu nguyen dang ky cua NV
        shifts_reset = 0
        schedules = WorkSchedule.query.filter_by(week_start_date=week_start).all()
        for schedule in schedules:
            for shift in schedule.shifts:
                if shift.is_confirmed:
                    shift.is_confirmed = False
                    shifts_reset += 1

        db.session.commit()
        flash(f'Da reset {shifts_reset} ca lam viec tuan {week_start.strftime("%d/%m")} - {week_end.strftime("%d/%m/%Y")}. Cac dang ky giu nguyen, co the xep lai bang tay.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Loi khi reset lich: {str(e)}', 'danger')

    return redirect(url_for('schedule.view', week=week_offset))


@bp.route('/add-shift', methods=['POST'])
@login_required
@admin_required
def add_shift():
    """Them ca lam viec moi"""
    user_id = request.form.get('user_id', type=int)
    date_str = request.form.get('date')
    shift_type_str = request.form.get('shift_type')
    week_offset = request.form.get('week_offset', 0, type=int)

    if not all([user_id, date_str, shift_type_str]):
        flash('Thieu thong tin ca lam viec.', 'danger')
        return redirect(url_for('schedule.view', week=week_offset))

    try:
        shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shift_type = ShiftType(shift_type_str)
        # Lay thoi gian ca tu SystemConfig
        dynamic_shift_times = get_dynamic_shift_times()
        shift_start, shift_end = dynamic_shift_times[shift_type]

        # Tim hoac tao WorkSchedule
        week_start = shift_date - timedelta(days=shift_date.weekday())
        week_end = week_start + timedelta(days=6)

        schedule = WorkSchedule.query.filter_by(
            user_id=user_id,
            week_start_date=week_start
        ).first()

        if not schedule:
            schedule = WorkSchedule(
                user_id=user_id,
                week_start_date=week_start,
                week_end_date=week_end,
                status=ScheduleStatus.APPROVED,
                approved_at=datetime.now(),
                approved_by=current_user.id
            )
            db.session.add(schedule)
            db.session.flush()

        # Kiem tra shift DA CONFIRMED da ton tai chua
        # Chi chan neu da co shift confirmed cho user nay tai ngay/ca nay
        existing_confirmed = ScheduleShift.query.filter_by(
            schedule_id=schedule.id,
            date=shift_date,
            shift_type=shift_type,
            is_confirmed=True
        ).first()

        if existing_confirmed:
            flash('Ca lam viec nay da ton tai.', 'warning')
        else:
            # Xoa cac shift chua confirmed (draft) truoc khi them moi
            ScheduleShift.query.filter_by(
                schedule_id=schedule.id,
                date=shift_date,
                shift_type=shift_type,
                is_confirmed=False
            ).delete()

            shift = ScheduleShift(
                schedule_id=schedule.id,
                date=shift_date,
                shift_type=shift_type,
                shift_start_time=shift_start,
                shift_end_time=shift_end,
                is_preferred=False,
                is_confirmed=True,
                shift_source='system',
                draft_status='final'
            )
            db.session.add(shift)
            db.session.commit()
            flash('Da them ca lam viec thanh cong.', 'success')

        # Tinh week_offset de quay ve dung tuan
        today = datetime.now().date()
        current_week_start = today - timedelta(days=today.weekday())
        target_week_offset = (week_start - current_week_start).days // 7
        return redirect(url_for('schedule.view', week=target_week_offset))

    except Exception as e:
        db.session.rollback()
        flash(f'Loi khi them ca: {str(e)}', 'danger')

    return redirect(url_for('schedule.view', week=week_offset))


@bp.route('/edit/<int:shift_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_shift(shift_id):
    """Sua 1 ca lam viec (Admin)"""
    shift = ScheduleShift.query.get_or_404(shift_id)

    # Tinh week_offset de quay lai dung tuan
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    shift_week_start = shift.date - timedelta(days=shift.date.weekday())
    week_offset = (shift_week_start - current_week_start).days // 7

    if request.method == 'POST':
        new_user_id = request.form.get('user_id', type=int)
        if new_user_id:
            # Tim schedule cua user moi
            new_schedule = WorkSchedule.query.filter_by(
                user_id=new_user_id,
                week_start_date=shift.schedule.week_start_date
            ).first()

            if not new_schedule:
                new_schedule = WorkSchedule(
                    user_id=new_user_id,
                    week_start_date=shift.schedule.week_start_date,
                    week_end_date=shift.schedule.week_end_date,
                    status=ScheduleStatus.APPROVED,
                    approved_at=datetime.now(),
                    approved_by=current_user.id
                )
                db.session.add(new_schedule)
                db.session.flush()

            shift.schedule_id = new_schedule.id
            db.session.commit()
            flash('Da cap nhat ca lam viec.', 'success')

        return redirect(url_for('schedule.view', week=week_offset))

    # Lay danh sach NV de chon
    staff_list = User.query.filter_by(status='active').all()
    return render_template('schedule/edit_shift.html', shift=shift, staff_list=staff_list, week_offset=week_offset)


@bp.route('/delete/<int:shift_id>', methods=['POST'])
@login_required
@admin_required
def delete_shift(shift_id):
    """Xoa 1 ca lam viec (Admin)"""
    shift = ScheduleShift.query.get_or_404(shift_id)

    # Tinh week_offset de quay lai dung tuan
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())
    shift_week_start = shift.date - timedelta(days=shift.date.weekday())
    week_offset = (shift_week_start - current_week_start).days // 7

    db.session.delete(shift)
    db.session.commit()
    flash('Da xoa ca lam viec.', 'success')
    return redirect(url_for('schedule.view', week=week_offset))


@bp.route('/settings', methods=['GET', 'POST'])
@login_required
@admin_required
def settings():
    """Cai dat thoi gian dang ky lich va mau sac/gio ca"""
    schedule_settings = ScheduleSettings.get_settings()

    if request.method == 'POST':
        schedule_settings.deadline_day = request.form.get('deadline_day', type=int, default=5)
        schedule_settings.deadline_hour = request.form.get('deadline_hour', type=int, default=18)
        schedule_settings.deadline_minute = request.form.get('deadline_minute', type=int, default=0)
        schedule_settings.late_registration_message = request.form.get('late_message', 'Ban da dang ky muon, Hay luu y.')
        schedule_settings.allow_current_week_edit = request.form.get('allow_current_week_edit') == '1'
        schedule_settings.updated_by = current_user.id

        # Luu cai dat mau sac va gio ca
        shift_configs = [
            ('shift_morning_color', request.form.get('morning_color', '#FEF3C7')),
            ('shift_afternoon_color', request.form.get('afternoon_color', '#FED7AA')),
            ('shift_evening_color', request.form.get('evening_color', '#C7D2FE')),
            ('shift_morning_start', request.form.get('morning_start', '07:00')),
            ('shift_morning_end', request.form.get('morning_end', '12:00')),
            ('shift_afternoon_start', request.form.get('afternoon_start', '12:00')),
            ('shift_afternoon_end', request.form.get('afternoon_end', '18:00')),
            ('shift_evening_start', request.form.get('evening_start', '18:00')),
            ('shift_evening_end', request.form.get('evening_end', '22:00')),
        ]

        for key, value in shift_configs:
            config = SystemConfig.query.filter_by(key=key).first()
            if config:
                config.value = value
            else:
                config = SystemConfig(key=key, value=value)
                db.session.add(config)

        db.session.commit()
        flash('Da cap nhat cai dat thanh cong!', 'success')
        return redirect(url_for('schedule.settings'))

    # Load cai dat mau sac va gio ca hien tai
    shift_settings = {}
    for config in SystemConfig.query.filter(SystemConfig.key.like('shift_%')).all():
        shift_settings[config.key] = config.value

    days = ['Thu 2', 'Thu 3', 'Thu 4', 'Thu 5', 'Thu 6', 'Thu 7', 'Chu nhat']
    return render_template('schedule/settings.html',
                           settings=schedule_settings,
                           shift_settings=shift_settings,
                           days=days)


# =============================================================================
# WORKFLOW MOI: XEP LICH TU DONG VOI DRAFT
# =============================================================================

@bp.route('/select-staff', methods=['GET', 'POST'])
@login_required
@manager_required
def select_staff():
    """Buoc 1: Chon nhan vien tham gia xep lich tu dong - ho tro chon tuan"""
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())

    # Lay week_offset tu params (0 = tuan hien tai, 1 = tuan sau, -1 = tuan truoc)
    week_offset = request.args.get('week', 1, type=int)  # Mac dinh la tuan sau

    # Tinh week_start va week_end
    week_start = current_week_start + timedelta(weeks=week_offset)
    week_end = week_start + timedelta(days=6)

    # Xac dinh loai tuan
    is_past_week = week_end < today
    is_current_week = week_start <= today <= week_end
    is_future_week = week_start > today

    if request.method == 'POST':
        selected_ids = request.form.getlist('staff_ids')
        session['selected_staff_ids'] = [int(id) for id in selected_ids]
        session['auto_week_start'] = week_start.isoformat()
        session['auto_week_offset'] = week_offset

        if not selected_ids:
            flash('Vui long chon it nhat 1 nhan vien!', 'warning')
            return redirect(url_for('schedule.select_staff', week=week_offset))

        flash(f'Da chon {len(selected_ids)} nhan vien.', 'success')
        return redirect(url_for('schedule.config_auto_schedule'))

    # Lay danh sach NV da dang ky
    schedules = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == week_start,
        WorkSchedule.status.in_([ScheduleStatus.SUBMITTED, ScheduleStatus.APPROVED])
    ).order_by(WorkSchedule.submitted_at).all()

    return render_template('schedule/select_staff.html',
                           schedules=schedules,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset,
                           is_past_week=is_past_week,
                           is_current_week=is_current_week,
                           is_future_week=is_future_week)


@bp.route('/config-auto-schedule', methods=['GET', 'POST'])
@login_required
@manager_required
def config_auto_schedule():
    """Buoc 2: Cau hinh va chay xep lich tu dong"""
    selected_ids = session.get('selected_staff_ids', [])
    week_start_str = session.get('auto_week_start')

    if not selected_ids or not week_start_str:
        flash('Vui long chon nhan vien truoc!', 'warning')
        return redirect(url_for('schedule.select_staff'))

    week_start = datetime.fromisoformat(week_start_str).date()
    week_end = week_start + timedelta(days=6)

    if request.method == 'POST':
        staff_per_shift = request.form.get('staff_per_shift', '2')

        # Chay auto-scheduler voi config moi
        try:
            result = auto_generate_schedule(
                week_start,
                staff_per_shift=int(staff_per_shift) if staff_per_shift.isdigit() else 2,
                selected_staff_ids=selected_ids,
                create_draft=True  # TAO LICH NHAP, KHONG GHI DE
            )

            if result and result.get('success'):
                flash(f'Da tao lich NHAP thanh cong! Tong: {result.get("total_shifts", 0)} ca', 'success')
                return redirect(url_for('schedule.review_draft'))
            else:
                flash('Loi khi xep lich!', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Loi: {str(e)}', 'danger')

        return redirect(url_for('schedule.review'))

    return render_template('schedule/config_auto.html',
                           selected_count=len(selected_ids),
                           week_start=week_start,
                           week_end=week_end)


@bp.route('/review-draft')
@login_required
@manager_required
def review_draft():
    """Buoc 3: Xem va sua lich nhap"""
    week_start_str = session.get('auto_week_start')

    if not week_start_str:
        flash('Khong tim thay lich nhap!', 'warning')
        return redirect(url_for('schedule.review'))

    week_start = datetime.fromisoformat(week_start_str).date()
    week_end = week_start + timedelta(days=6)

    # Lay tat ca shifts NHAP (draft)
    draft_shifts = db.session.query(ScheduleShift, User)\
        .select_from(ScheduleShift)\
        .join(WorkSchedule, ScheduleShift.schedule_id == WorkSchedule.id)\
        .join(User, WorkSchedule.user_id == User.id)\
        .filter(
            ScheduleShift.date >= week_start,
            ScheduleShift.date <= week_end,
            ScheduleShift.shift_source == 'system',
            ScheduleShift.draft_status == 'draft'
        )\
        .order_by(ScheduleShift.date, ScheduleShift.shift_type)\
        .all()

    # To chuc theo ngay va ca
    schedule_by_date = {}
    for i in range(7):
        date = week_start + timedelta(days=i)
        schedule_by_date[date] = {
            'morning': [],
            'afternoon': [],
            'evening': []
        }

    for shift, user in draft_shifts:
        shift_type = shift.shift_type.value
        if shift.date in schedule_by_date:
            schedule_by_date[shift.date][shift_type].append({
                'shift': shift,
                'user': user
            })

    # Lay danh sach NV de them vao draft
    all_staff = User.query.filter_by(status='active').filter(User.role != UserRole.ADMIN).all()

    return render_template('schedule/review_draft.html',
                           schedule_by_date=schedule_by_date,
                           week_start=week_start,
                           week_end=week_end,
                           total_shifts=len(draft_shifts),
                           all_staff=all_staff,
                           timedelta=timedelta)


@bp.route('/save-draft', methods=['POST'])
@login_required
@manager_required
def save_draft():
    """Buoc 4: Luu lich nhap thanh chinh thuc"""
    week_start_str = session.get('auto_week_start')

    if not week_start_str:
        flash('Khong tim thay lich nhap!', 'warning')
        return redirect(url_for('schedule.review'))

    week_start = datetime.fromisoformat(week_start_str).date()
    week_end = week_start + timedelta(days=6)

    # QUAN TRONG: Xoa tat ca shifts FINAL cu cua tuan nay truoc khi luu moi
    # Tranh duplicate data khi xep lich nhieu lan
    ScheduleShift.query.filter(
        ScheduleShift.date >= week_start,
        ScheduleShift.date <= week_end,
        ScheduleShift.shift_source == 'system',
        ScheduleShift.draft_status == 'final'
    ).delete()

    # Chuyen tat ca shifts nhap thanh final
    updated = ScheduleShift.query.filter(
        ScheduleShift.date >= week_start,
        ScheduleShift.date <= week_end,
        ScheduleShift.shift_source == 'system',
        ScheduleShift.draft_status == 'draft'
    ).update({'draft_status': 'final', 'is_confirmed': True})

    db.session.commit()

    # Giu lai auto_week_start de final_review dung, chi xoa selected_staff_ids
    session.pop('selected_staff_ids', None)
    # KHONG xoa auto_week_start de final_review va publish_to_staff dung dung tuan

    flash(f'Da luu {updated} ca lam viec thanh chinh thuc!', 'success')
    return redirect(url_for('schedule.final_review'))


@bp.route('/discard-draft', methods=['POST'])
@login_required
@manager_required
def discard_draft():
    """Huy bo lich nhap"""
    week_start_str = session.get('auto_week_start')

    if week_start_str:
        week_start = datetime.fromisoformat(week_start_str).date()
        week_end = week_start + timedelta(days=6)

        # Xoa tat ca shifts nhap
        deleted = ScheduleShift.query.filter(
            ScheduleShift.date >= week_start,
            ScheduleShift.date <= week_end,
            ScheduleShift.shift_source == 'system',
            ScheduleShift.draft_status == 'draft'
        ).delete()

        db.session.commit()

        # Xoa session
        session.pop('selected_staff_ids', None)
        session.pop('auto_week_start', None)

        flash(f'Da huy {deleted} ca lich nhap!', 'info')

    return redirect(url_for('schedule.review'))


@bp.route('/remove-draft-shift', methods=['POST'])
@login_required
@manager_required
def remove_draft_shift():
    """Xoa 1 shift khoi lich nhap"""
    if request.is_json:
        data = request.get_json()
        shift_id = data.get('shift_id')
    else:
        shift_id = request.form.get('shift_id')

    if shift_id:
        shift = ScheduleShift.query.filter_by(
            id=shift_id,
            shift_source='system',
            draft_status='draft'
        ).first()

        if shift:
            db.session.delete(shift)
            db.session.commit()
            return jsonify({'success': True})

    return jsonify({'success': False, 'error': 'Khong tim thay shift'})


@bp.route('/add-draft-shift', methods=['POST'])
@login_required
@manager_required
def add_draft_shift():
    """Them 1 shift vao lich nhap"""
    # Xu ly ca JSON va form data
    if request.is_json:
        data = request.get_json()
        user_id = int(data.get('user_id', 0)) if data.get('user_id') else 0
        date_str = data.get('date')
        shift_type_str = data.get('shift_type')
    else:
        user_id = request.form.get('user_id', type=int)
        date_str = request.form.get('date')
        shift_type_str = request.form.get('shift_type')

    if not all([user_id, date_str, shift_type_str]):
        return jsonify({'success': False, 'error': 'Thieu thong tin'})

    try:
        shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shift_type = ShiftType(shift_type_str)
        # Lay thoi gian ca tu SystemConfig
        dynamic_shift_times = get_dynamic_shift_times()
        shift_start, shift_end = dynamic_shift_times[shift_type]

        # Tim hoac tao WorkSchedule
        week_start = shift_date - timedelta(days=shift_date.weekday())
        week_end = week_start + timedelta(days=6)

        schedule = WorkSchedule.query.filter_by(
            user_id=user_id,
            week_start_date=week_start
        ).first()

        if not schedule:
            schedule = WorkSchedule(
                user_id=user_id,
                week_start_date=week_start,
                week_end_date=week_end,
                status=ScheduleStatus.SUBMITTED,
                submitted_at=datetime.now()
            )
            db.session.add(schedule)
            db.session.flush()

        # Kiem tra shift da ton tai chua
        existing = ScheduleShift.query.filter_by(
            schedule_id=schedule.id,
            date=shift_date,
            shift_type=shift_type,
            shift_source='system',
            draft_status='draft'
        ).first()

        if existing:
            return jsonify({'success': False, 'error': 'NV nay da co trong ca nay'})

        # Tao shift moi
        shift = ScheduleShift(
            schedule_id=schedule.id,
            date=shift_date,
            shift_type=shift_type,
            shift_start_time=shift_start,
            shift_end_time=shift_end,
            is_preferred=False,
            is_confirmed=False,
            shift_source='system',
            draft_status='draft'
        )
        db.session.add(shift)
        db.session.commit()

        user = User.query.get(user_id)
        return jsonify({
            'success': True,
            'shift_id': shift.id,
            'user_name': user.full_name if user else 'Unknown'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/final-review')
@login_required
@manager_required
def final_review():
    """Buoc 5: Xem lich final va day ve nhan vien"""
    today = datetime.now().date()
    current_week_start = today - timedelta(days=today.weekday())

    # Neu co tham so week thi dung no
    if 'week' in request.args:
        week_offset = request.args.get('week', 1, type=int)
        week_start = current_week_start + timedelta(weeks=week_offset)
        week_end = week_start + timedelta(days=6)
        # Xoa session khi user chuyen tuan thu cong
        session.pop('auto_week_start', None)
    else:
        # Uu tien dung tuan tu session (neu vua luu xong)
        week_start_str = session.get('auto_week_start')
        if week_start_str:
            week_start = datetime.fromisoformat(week_start_str).date()
            week_end = week_start + timedelta(days=6)
        else:
            # Fallback: dung tuan sau
            week_offset = 1
            week_start = current_week_start + timedelta(weeks=week_offset)
            week_end = week_start + timedelta(days=6)

    # Tinh week_offset de truyen vao template
    week_offset = (week_start - current_week_start).days // 7

    # Lay lich final (da luu)
    final_shifts = db.session.query(ScheduleShift, User)\
        .select_from(ScheduleShift)\
        .join(WorkSchedule, ScheduleShift.schedule_id == WorkSchedule.id)\
        .join(User, WorkSchedule.user_id == User.id)\
        .filter(
            ScheduleShift.date >= week_start,
            ScheduleShift.date <= week_end,
            ScheduleShift.is_confirmed == True
        )\
        .order_by(ScheduleShift.date, ScheduleShift.shift_type)\
        .all()

    # To chuc theo ngay va ca
    schedule_by_date = {}
    for i in range(7):
        date = week_start + timedelta(days=i)
        schedule_by_date[date] = {
            'morning': [],
            'afternoon': [],
            'evening': []
        }

    for shift, user in final_shifts:
        shift_type = shift.shift_type.value
        if shift.date in schedule_by_date:
            schedule_by_date[shift.date][shift_type].append({
                'shift': shift,
                'user': user
            })

    # Kiem tra da publish chua
    schedules = WorkSchedule.query.filter_by(
        week_start_date=week_start,
        status=ScheduleStatus.APPROVED
    ).all()
    is_published = len(schedules) > 0

    return render_template('schedule/final_review.html',
                           schedule_by_date=schedule_by_date,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset,
                           total_shifts=len(final_shifts),
                           is_published=is_published,
                           timedelta=timedelta)


@bp.route('/publish-to-staff', methods=['POST'])
@login_required
@admin_required
def publish_to_staff():
    """Day lich ve cho nhan vien"""
    # Uu tien dung tuan tu session
    week_start_str = session.get('auto_week_start')
    if week_start_str:
        week_start = datetime.fromisoformat(week_start_str).date()
        week_end = week_start + timedelta(days=6)
    else:
        week_start, week_end = get_next_week_dates()

    # Update trang thai WorkSchedule thanh APPROVED
    schedules = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == week_start,
        WorkSchedule.status.in_([ScheduleStatus.SUBMITTED, ScheduleStatus.DRAFT])
    ).all()

    for schedule in schedules:
        schedule.status = ScheduleStatus.APPROVED
        schedule.approved_at = datetime.now()
        schedule.approved_by = current_user.id
        # Confirm tat ca shifts cua schedule nay
        for shift in schedule.shifts:
            shift.is_confirmed = True

    db.session.commit()

    flash(f'Da day lich ve cho {len(schedules)} nhan vien!', 'success')
    return redirect(url_for('schedule.final_review'))
