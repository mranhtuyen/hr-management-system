from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from datetime import datetime, timedelta, time
from app.schedule import bp
from app.schedule.forms import WeeklyScheduleForm
from app.schedule.auto_scheduler import auto_generate_schedule
from app.models import (
    WorkSchedule, ScheduleShift, User, ShiftType, ScheduleStatus,
    UserRole, EmploymentType, db
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
    # Mo tu Thu 6, dong luc 18h Thu 7
    # Weekday: 0=Mon, 4=Fri, 5=Sat, 6=Sun
    if now.weekday() == 4:  # Friday
        return True
    elif now.weekday() == 5:  # Saturday
        return now.hour < 18
    return False


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

    if existing_schedule and existing_schedule.status != ScheduleStatus.DRAFT:
        flash('Ban da dang ky lich cho tuan nay roi.', 'warning')
        return redirect(url_for('schedule.my_schedule'))

    # Kiem tra thoi gian dang ky
    if not is_registration_open():
        flash('Thoi gian dang ky lich da dong (18h Thu 7). Vui long cho tuan sau.', 'warning')
        return redirect(url_for('dashboard.index'))

    form = WeeklyScheduleForm()

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
                           is_open=is_registration_open(),
                           timedelta=timedelta)


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
        current_shifts = ScheduleShift.query.filter_by(
            schedule_id=current_schedule.id,
            is_confirmed=True
        ).order_by(ScheduleShift.date).all()

    # Lich tuan sau
    next_week_start, _ = get_next_week_dates()
    next_schedule = WorkSchedule.query.filter_by(
        user_id=current_user.id,
        week_start_date=next_week_start
    ).first()

    return render_template('schedule/my_schedule.html',
                           current_schedule=current_schedule,
                           current_shifts=current_shifts,
                           next_schedule=next_schedule,
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

    # Nhom theo ngay va ca
    schedule_grid = {}
    for day_offset in range(7):
        date = week_start + timedelta(days=day_offset)
        schedule_grid[date] = {
            ShiftType.MORNING: [],
            ShiftType.AFTERNOON: [],
            ShiftType.EVENING: []
        }

    for shift, user in shifts:
        schedule_grid[shift.date][shift.shift_type].append({
            'user': user,
            'shift': shift
        })

    return render_template('schedule/view.html',
                           schedule_grid=schedule_grid,
                           week_start=week_start,
                           week_end=week_end,
                           week_offset=week_offset)


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
                           week_end=week_end)


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


@bp.route('/auto-generate', methods=['GET', 'POST'])
@login_required
@admin_required
def auto_generate():
    """Chay thuat toan xep lich tu dong (Admin only - GET/POST)"""
    week_start, week_end = get_next_week_dates()

    try:
        result = auto_generate_schedule(week_start)
        if result and result.get('success'):
            flash(f'Da xep lich tu dong thanh cong! Tuan {week_start.strftime("%d/%m")} - {week_end.strftime("%d/%m/%Y")}. Tong cong {result.get("total_shifts_assigned", 0)} ca.', 'success')
        else:
            flash('Xep lich tu dong hoan thanh nhung co the chua toi uu.', 'warning')
    except Exception as e:
        db.session.rollback()
        flash(f'Loi khi xep lich tu dong: {str(e)}', 'danger')

    return redirect(url_for('schedule.review'))


@bp.route('/edit/<int:shift_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_shift(shift_id):
    """Sua 1 ca lam viec (Admin)"""
    shift = ScheduleShift.query.get_or_404(shift_id)

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

        return redirect(url_for('schedule.view'))

    # Lay danh sach NV de chon
    staff_list = User.query.filter_by(status='active').all()
    return render_template('schedule/edit_shift.html', shift=shift, staff_list=staff_list)


@bp.route('/delete/<int:shift_id>', methods=['POST'])
@login_required
@admin_required
def delete_shift(shift_id):
    """Xoa 1 ca lam viec (Admin)"""
    shift = ScheduleShift.query.get_or_404(shift_id)
    db.session.delete(shift)
    db.session.commit()
    flash('Da xoa ca lam viec.', 'success')
    return redirect(url_for('schedule.view'))
