import os
from flask import render_template, redirect, url_for, flash, request, send_file, current_app
from flask_login import login_required, current_user
from datetime import datetime
from app.payroll import bp
from app.payroll.calculator import (
    calculate_monthly_payroll,
    calculate_all_payrolls,
    get_payroll_summary
)
from app.payroll.report_generator import generate_payslip_pdf, generate_monthly_report_pdf
from app.models import Payroll, User, UserRole, PayrollStatus, db
from app.auth.routes import manager_required, admin_required


@bp.route('/')
@login_required
def index():
    """Trang chinh luong"""
    if current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return redirect(url_for('payroll.list'))
    else:
        return redirect(url_for('payroll.my_payroll'))


@bp.route('/list')
@login_required
@manager_required
def list():
    """Danh sach luong tat ca NV"""
    # Loc theo thang
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    # Lay du lieu
    payrolls = db.session.query(Payroll, User).join(User).filter(
        Payroll.month == month,
        Payroll.year == year
    ).order_by(User.full_name).all()

    # Thong ke
    summary = get_payroll_summary(month, year)

    return render_template('payroll/list.html',
                           payrolls=payrolls,
                           summary=summary,
                           month=month,
                           year=year)


@bp.route('/calculate', methods=['GET', 'POST'])
@login_required
@admin_required
def calculate():
    """Tinh luong cho tat ca NV (GET hoac POST)"""
    if request.method == 'POST':
        month = request.form.get('month', type=int, default=datetime.now().month)
        year = request.form.get('year', type=int, default=datetime.now().year)
    else:
        month = request.args.get('month', type=int, default=datetime.now().month)
        year = request.args.get('year', type=int, default=datetime.now().year)

    try:
        payrolls = calculate_all_payrolls(month, year)
        flash(f'Da tinh luong cho {len(payrolls)} nhan vien.', 'success')
    except Exception as e:
        flash(f'Loi khi tinh luong: {str(e)}', 'danger')

    return redirect(url_for('payroll.list', month=month, year=year))


@bp.route('/detail/<int:payroll_id>')
@login_required
def detail(payroll_id):
    """Chi tiet luong 1 NV"""
    payroll = Payroll.query.get_or_404(payroll_id)

    # Kiem tra quyen
    if current_user.role == UserRole.STAFF and payroll.user_id != current_user.id:
        flash('Ban khong co quyen xem phieu luong nay.', 'danger')
        return redirect(url_for('payroll.my_payroll'))

    user = User.query.get(payroll.user_id)

    # Lay chi tiet vi pham va thuong
    from datetime import date as date_type, timedelta
    from app.models import Violation, Reward, AttendanceRecord, ScheduleShift, WorkSchedule
    import calendar

    month_start = date_type(payroll.year, payroll.month, 1)
    if payroll.month == 12:
        month_end = date_type(payroll.year + 1, 1, 1)
    else:
        month_end = date_type(payroll.year, payroll.month + 1, 1)

    violations = Violation.query.filter(
        Violation.user_id == payroll.user_id,
        Violation.date >= month_start,
        Violation.date < month_end
    ).order_by(Violation.date).all()

    rewards = Reward.query.filter(
        Reward.user_id == payroll.user_id,
        Reward.created_at >= datetime(payroll.year, payroll.month, 1),
        Reward.created_at < datetime(payroll.year, payroll.month + 1, 1) if payroll.month < 12 else datetime(payroll.year + 1, 1, 1)
    ).all()

    # Lay chi tiet cham cong hang ngay
    attendance_records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == payroll.user_id,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date < month_end
    ).order_by(AttendanceRecord.date).all()

    # Lay lich lam viec da duyet
    schedules = WorkSchedule.query.filter(
        WorkSchedule.user_id == payroll.user_id,
        WorkSchedule.week_start_date >= month_start,
        WorkSchedule.week_start_date < month_end
    ).all()

    # Tao du lieu chi tiet hang ngay
    days_in_month = calendar.monthrange(payroll.year, payroll.month)[1]
    daily_details = []

    for day in range(1, days_in_month + 1):
        current_date = date_type(payroll.year, payroll.month, day)

        # Tim cham cong ngay nay
        day_attendance = [a for a in attendance_records if a.date == current_date]

        # Tim lich lam viec ngay nay
        day_shifts = []
        for schedule in schedules:
            for shift in schedule.shifts:
                if shift.date == current_date and shift.is_confirmed:
                    day_shifts.append(shift)

        # Tinh so bua an
        meals = len(day_attendance) if user.meal_support_eligible else 0

        if day_attendance or day_shifts:
            daily_details.append({
                'date': current_date,
                'shifts': day_shifts,
                'attendance': day_attendance,
                'total_hours': sum(a.total_work_hours for a in day_attendance),
                'meals': meals,
                'is_late': any(a.is_late for a in day_attendance)
            })

    # Phan trang (10 ngay/trang)
    page = request.args.get('page', 1, type=int)
    per_page = 10
    total_pages = (len(daily_details) + per_page - 1) // per_page
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_details = daily_details[start_idx:end_idx]

    return render_template('payroll/detail.html',
                           payroll=payroll,
                           user=user,
                           violations=violations,
                           rewards=rewards,
                           daily_details=paginated_details,
                           page=page,
                           total_pages=total_pages,
                           total_days=len(daily_details))


@bp.route('/my-payroll')
@login_required
def my_payroll():
    """Xem luong ca nhan"""
    # Lay lich su luong
    payrolls = Payroll.query.filter_by(
        user_id=current_user.id
    ).order_by(Payroll.year.desc(), Payroll.month.desc()).all()

    # Thang hien tai
    current_month = datetime.now().month
    current_year = datetime.now().year
    current_payroll = Payroll.query.filter_by(
        user_id=current_user.id,
        month=current_month,
        year=current_year
    ).first()

    return render_template('payroll/my_payroll.html',
                           payrolls=payrolls,
                           current_payroll=current_payroll)


@bp.route('/approve/<int:payroll_id>', methods=['POST'])
@login_required
@admin_required
def approve(payroll_id):
    """Duyet luong"""
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.status = PayrollStatus.APPROVED
    payroll.approved_at = datetime.now()
    db.session.commit()

    flash('Da duyet luong thanh cong.', 'success')
    return redirect(url_for('payroll.detail', payroll_id=payroll_id))


@bp.route('/mark-paid/<int:payroll_id>', methods=['POST'])
@login_required
@admin_required
def mark_paid(payroll_id):
    """Danh dau da tra luong"""
    payroll = Payroll.query.get_or_404(payroll_id)
    payroll.status = PayrollStatus.PAID
    payroll.paid_at = datetime.now()
    db.session.commit()

    flash('Da danh dau tra luong thanh cong.', 'success')
    return redirect(url_for('payroll.detail', payroll_id=payroll_id))


@bp.route('/download/<int:payroll_id>')
@login_required
def download_payslip(payroll_id):
    """Tai phieu luong PDF"""
    payroll = Payroll.query.get_or_404(payroll_id)

    # Kiem tra quyen
    if current_user.role == UserRole.STAFF and payroll.user_id != current_user.id:
        flash('Ban khong co quyen tai phieu luong nay.', 'danger')
        return redirect(url_for('payroll.my_payroll'))

    user = User.query.get(payroll.user_id)

    # Tao PDF
    pdf_buffer = generate_payslip_pdf(payroll_id)
    if not pdf_buffer:
        flash('Khong the tao phieu luong.', 'danger')
        return redirect(url_for('payroll.detail', payroll_id=payroll_id))

    filename = f"phieu_luong_{user.username}_{payroll.month}_{payroll.year}.pdf"

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


@bp.route('/download-report')
@login_required
@manager_required
def download_report():
    """Tai bao cao luong thang"""
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    pdf_buffer = generate_monthly_report_pdf(month, year)
    if not pdf_buffer:
        flash('Khong the tao bao cao.', 'danger')
        return redirect(url_for('payroll.list', month=month, year=year))

    filename = f"bao_cao_luong_{month}_{year}.pdf"

    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


@bp.route('/update-advance/<int:payroll_id>', methods=['POST'])
@login_required
@admin_required
def update_advance(payroll_id):
    """Cap nhat tien tam ung"""
    payroll = Payroll.query.get_or_404(payroll_id)

    advance = request.form.get('advance_payment', type=float, default=0)
    payroll.advance_payment = advance

    # Tinh lai luong thuc linh
    payroll.net_salary = (
        payroll.gross_salary +
        payroll.meal_support_amount +
        payroll.total_reward -
        payroll.total_penalty -
        advance
    )

    db.session.commit()
    flash('Da cap nhat tien tam ung.', 'success')

    return redirect(url_for('payroll.detail', payroll_id=payroll_id))


@bp.route('/update-salary/<int:payroll_id>', methods=['POST'])
@login_required
@admin_required
def update_salary(payroll_id):
    """Cap nhat chi tiet luong"""
    payroll = Payroll.query.get_or_404(payroll_id)

    payroll.gross_salary = request.form.get('gross_salary', type=float, default=payroll.gross_salary)
    payroll.meal_support_amount = request.form.get('meal_support_amount', type=float, default=payroll.meal_support_amount)
    payroll.total_reward = request.form.get('total_reward', type=float, default=payroll.total_reward)
    payroll.total_penalty = request.form.get('total_penalty', type=float, default=payroll.total_penalty)
    payroll.advance_payment = request.form.get('advance_payment', type=float, default=payroll.advance_payment)

    # Tinh lai luong thuc linh
    payroll.net_salary = (
        payroll.gross_salary +
        payroll.meal_support_amount +
        payroll.total_reward -
        payroll.total_penalty -
        payroll.advance_payment
    )

    db.session.commit()
    flash('Da cap nhat chi tiet luong.', 'success')

    return redirect(url_for('payroll.detail', payroll_id=payroll_id))
