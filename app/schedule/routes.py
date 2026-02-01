from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, time
from app.schedule import bp
from app.schedule.forms import WeeklyScheduleForm
from app.schedule.auto_scheduler import auto_generate_schedule
from app.models import (
    WorkSchedule, ScheduleShift, User, ShiftType, ScheduleStatus,
    UserRole, EmploymentType, ScheduleSettings, db
)
from app.auth.routes import manager_required, admin_required


# Dinh nghia thoi gian cac ca
SHIFT_TIMES = {
    ShiftType.MORNING: (time(7, 0), time(12, 0)),
    ShiftType.AFTERNOON: (time(12, 0), time(18, 0)),
    ShiftType.EVENING: (time(18, 0), time(22, 0))
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
    """Kiem tra dang ky lich con mo khong"""
    now = datetime.now()
    settings = ScheduleSettings.get_settings()

    # Mac dinh: Mo tu Thu 6, dong luc 18h Thu 7
    deadline_day = settings.deadline_day  # 0=Mon, 5=Sat, 6=Sun
    deadline_hour = settings.deadline_hour
    deadline_minute = settings.deadline_minute

    # Weekday: 0=Mon, 4=Fri, 5=Sat, 6=Sun
    if now.weekday() == 4:  # Friday - luon mo
        return True
    elif now.weekday() == deadline_day:
        if now.hour < deadline_hour:
            return True
        elif now.hour == deadline_hour and now.minute < deadline_minute:
            return True
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
    """Dang ky lich lam viec tuan sau"""
    week_start, week_end = get_next_week_dates()

    # Kiem tra da dang ky chua
    existing_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=week_start
    ).first()

    # Chi chan khi da APPROVED
    if existing_schedule and existing_schedule.status == ScheduleStatus.APPROVED:
        flash('Lich cua ban da duoc duyet. Lien he Admin neu can thay doi.', 'warning')
        return redirect(url_for('schedule.my_schedule'))

    # Kiem tra thoi gian dang ky (bo qua neu dang sua lich bi tra lai)
    if not is_registration_open() and not (existing_schedule and existing_schedule.status == ScheduleStatus.DRAFT):
        flash('Thoi gian dang ky lich da dong (18h Thu 7). Vui long cho tuan sau.', 'warning')
        return redirect(url_for('dashboard.index'))

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

            for shift_type, field_name in [(ShiftType.MORNING, 'morning'),
                                           (ShiftType.AFTERNOON, 'afternoon'),
                                           (ShiftType.EVENING, 'evening')]:
                if getattr(day_form, field_name).data:
                    shift_start, shift_end = SHIFT_TIMES[shift_type]
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
        return redirect(url_for('schedule.my_schedule'))

    return render_template('schedule/register.html',
                           form=form,
                           week_start=week_start,
                           week_end=week_end,
                           is_open=is_registration_open() or (existing_schedule and existing_schedule.status == ScheduleStatus.DRAFT),
                           existing_schedule=existing_schedule,
                           timedelta=timedelta)


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
    """Xem lich lam viec cua ban than"""
    today = datetime.now().date()

    # Lich hien tai
    current_week_start = today - timedelta(days=today.weekday())
    current_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=current_week_start
    ).first()

    current_shifts = []
    if current_schedule:
        # Hien thi tat ca shifts da duoc confirmed
        current_shifts = ScheduleShift.query.filter_by(
            schedule_id=current_schedule.id,
            is_confirmed=True
        ).order_by(ScheduleShift.date).all()

    # Lich tuan sau
    next_week_start, next_week_end = get_next_week_dates()
    next_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=next_week_start
    ).first()

    # Lay shifts tuan sau (ca da dang ky va da duyet)
    next_shifts = []
    if next_schedule:
        next_shifts = ScheduleShift.query.filter_by(
            schedule_id=next_schedule.id
        ).order_by(ScheduleShift.date).all()

    return render_template('schedule/my_schedule.html',
                           current_schedule=current_schedule,
                           current_shifts=current_shifts,
                           next_schedule=next_schedule,
                           next_shifts=next_shifts,
                           next_week_start=next_week_start,
                           next_week_end=next_week_end,
                           today=today)


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
    """Duyet lich dang ky cua NV"""
    week_start, week_end = get_next_week_dates()

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

    return render_template('schedule/review.html',
                           pending_schedules=pending_schedules,
                           approved_schedules=approved_schedules,
                           not_registered=not_registered,
                           week_start=week_start,
                           week_end=week_end,
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
        for day_offset, day_name in enumerate(day_names):
            shift_date = week_start + timedelta(days=day_offset)
            for shift_type_str in ['morning', 'afternoon', 'evening']:
                field_name = f'{day_name}_{shift_type_str}'
                if request.form.get(field_name):
                    shift_type = ShiftType(shift_type_str)
                    shift_start, shift_end = SHIFT_TIMES[shift_type]
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

    if not all([user_id, date_str, shift_type_str]):
        flash('Thieu thong tin ca lam viec.', 'danger')
        return redirect(url_for('schedule.view', week=1))

    try:
        shift_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        shift_type = ShiftType(shift_type_str)
        shift_start, shift_end = SHIFT_TIMES[shift_type]

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

        # Kiem tra shift da ton tai chua
        existing = ScheduleShift.query.filter_by(
            schedule_id=schedule.id,
            date=shift_date,
            shift_type=shift_type
        ).first()

        if existing:
            flash('Ca lam viec nay da ton tai.', 'warning')
        else:
            shift = ScheduleShift(
                schedule_id=schedule.id,
                date=shift_date,
                shift_type=shift_type,
                shift_start_time=shift_start,
                shift_end_time=shift_end,
                is_preferred=False,
                is_confirmed=True
            )
            db.session.add(shift)
            db.session.commit()
            flash('Da them ca lam viec thanh cong.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Loi khi them ca: {str(e)}', 'danger')

    return redirect(url_for('schedule.view', week=1))


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
    """Cai dat thoi gian dang ky lich"""
    schedule_settings = ScheduleSettings.get_settings()

    if request.method == 'POST':
        schedule_settings.deadline_day = request.form.get('deadline_day', type=int, default=5)
        schedule_settings.deadline_hour = request.form.get('deadline_hour', type=int, default=18)
        schedule_settings.deadline_minute = request.form.get('deadline_minute', type=int, default=0)
        schedule_settings.late_registration_message = request.form.get('late_message', 'Ban da dang ky muon, Hay luu y.')
        schedule_settings.updated_by = current_user.id

        db.session.commit()
        flash('Da cap nhat cai dat thanh cong!', 'success')
        return redirect(url_for('schedule.settings'))

    days = ['Thu 2', 'Thu 3', 'Thu 4', 'Thu 5', 'Thu 6', 'Thu 7', 'Chu nhat']
    return render_template('schedule/settings.html',
                           settings=schedule_settings,
                           days=days)
