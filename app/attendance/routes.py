import os
import json
from flask import render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from app.attendance import bp
from app.attendance.import_handler import import_attendance_excel, parse_attendance_preview, save_attendance_from_preview
from app.attendance.late_checker import process_daily_attendance, get_monthly_late_summary
from app.models import AttendanceRecord, User, UserRole, db
from app.auth.routes import manager_required


ALLOWED_EXTENSIONS = {'xlsx', 'xls'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route('/')
@login_required
def index():
    """Trang chinh cham cong"""
    if current_user.role in [UserRole.ADMIN, UserRole.MANAGER]:
        return redirect(url_for('attendance.import_page'))
    else:
        return redirect(url_for('attendance.my_attendance'))


@bp.route('/import', methods=['GET', 'POST'])
@login_required
@manager_required
def import_page():
    """Import file cham cong tu Excel - Buoc 1: Upload va chon nam"""
    if request.method == 'POST':
        # Kiem tra file
        if 'file' not in request.files:
            flash('Khong tim thay file.', 'danger')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('Chua chon file.', 'danger')
            return redirect(request.url)

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"

            upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            filepath = os.path.join(upload_folder, filename)
            file.save(filepath)

            # Lay nam da chon
            selected_year = request.form.get('year', type=int, default=datetime.now().year)
            date_format = request.form.get('date_format', 'auto')

            # Parse file de preview
            try:
                preview_records = parse_attendance_preview(filepath, selected_year, date_format)

                if not preview_records:
                    flash('Khong doc duoc du lieu tu file. Kiem tra lai dinh dang.', 'warning')
                    return redirect(request.url)

                # Luu vao session
                session['preview_records'] = preview_records
                session['preview_filepath'] = filepath
                session['preview_year'] = selected_year
                session['preview_date_format'] = date_format

                flash(f'Da doc {len(preview_records)} ban ghi. Vui long kiem tra va bo sung ma NV.', 'info')
                return redirect(url_for('attendance.preview_import'))

            except Exception as e:
                flash(f'Loi khi doc file: {str(e)}', 'danger')
                return redirect(request.url)

        flash('Chi chap nhan file Excel (.xlsx, .xls)', 'danger')
        return redirect(request.url)

    return render_template('attendance/import.html')


@bp.route('/preview-import')
@login_required
@manager_required
def preview_import():
    """Buoc 2: Xem preview va chinh sua truoc khi luu"""
    preview_records = session.get('preview_records', [])
    preview_year = session.get('preview_year', datetime.now().year)

    if not preview_records:
        flash('Khong co du lieu preview. Vui long upload file truoc.', 'warning')
        return redirect(url_for('attendance.import_page'))

    # Lay danh sach NV de goi y
    all_users = User.query.filter_by(status='active').order_by(User.full_name).all()

    return render_template('attendance/preview_import.html',
                           records=preview_records,
                           year=preview_year,
                           all_users=all_users)


@bp.route('/confirm-import', methods=['POST'])
@login_required
@manager_required
def confirm_import():
    """Buoc 3: Xac nhan va luu vao database"""
    records_json = request.form.get('records_json', '[]')

    try:
        records = json.loads(records_json)

        if not records:
            flash('Khong co du lieu de luu.', 'warning')
            return redirect(url_for('attendance.import_page'))

        # Luu vao database
        result = save_attendance_from_preview(records)

        # Xoa session
        session.pop('preview_records', None)
        session.pop('preview_filepath', None)
        session.pop('preview_year', None)
        session.pop('preview_date_format', None)

        if result['success'] > 0:
            flash(f"Da import thanh cong {result['success']} ban ghi.", 'success')

            # Xu ly di muon
            process_result = process_daily_attendance()
            if process_result['processed'] > 0:
                flash(f"Da xu ly {process_result['processed']} truong hop di muon.", 'info')

        if result['errors']:
            for error in result['errors'][:5]:
                flash(error, 'warning')
            if len(result['errors']) > 5:
                flash(f"... va {len(result['errors']) - 5} loi khac.", 'warning')

        return redirect(url_for('attendance.view'))

    except Exception as e:
        flash(f'Loi khi luu du lieu: {str(e)}', 'danger')
        return redirect(url_for('attendance.preview_import'))


@bp.route('/cancel-import', methods=['POST'])
@login_required
@manager_required
def cancel_import():
    """Huy preview va quay lai"""
    # Xoa file da upload
    filepath = session.get('preview_filepath')
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except:
            pass

    # Xoa session
    session.pop('preview_records', None)
    session.pop('preview_filepath', None)
    session.pop('preview_year', None)
    session.pop('preview_date_format', None)

    flash('Da huy import.', 'info')
    return redirect(url_for('attendance.import_page'))


@bp.route('/view')
@login_required
@manager_required
def view():
    """Xem cham cong cua tat ca NV - Ho tro loc theo khoang ngay"""
    # Loc theo khoang ngay
    from_date_str = request.args.get('from_date')
    to_date_str = request.args.get('to_date')
    user_id = request.args.get('user_id', type=int)

    # Default: 7 ngay gan nhat
    if from_date_str:
        try:
            from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        except ValueError:
            from_date = datetime.now().date() - timedelta(days=6)
    else:
        from_date = datetime.now().date() - timedelta(days=6)

    if to_date_str:
        try:
            to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
        except ValueError:
            to_date = datetime.now().date()
    else:
        to_date = datetime.now().date()

    # Query du lieu cham cong
    query = db.session.query(
        AttendanceRecord, User
    ).join(User).filter(
        AttendanceRecord.date >= from_date,
        AttendanceRecord.date <= to_date
    )

    # Loc theo NV neu co
    if user_id:
        query = query.filter(AttendanceRecord.user_id == user_id)

    records = query.order_by(
        AttendanceRecord.date.desc(),
        AttendanceRecord.actual_checkin
    ).all()

    # Thong ke
    total_records = len(records)
    late_count = sum(1 for r, u in records if r.is_late)
    early_bird_count = sum(1 for r, u in records if r.is_early_bird)

    # Danh sach NV de filter
    all_users = User.query.filter_by(status='active').order_by(User.full_name).all()

    return render_template('attendance/view.html',
                           records=records,
                           from_date=from_date,
                           to_date=to_date,
                           selected_user_id=user_id,
                           all_users=all_users,
                           total_records=total_records,
                           late_count=late_count,
                           early_bird_count=early_bird_count)


@bp.route('/my-attendance')
@login_required
def my_attendance():
    """Xem cham cong ca nhan"""
    # Loc theo thang
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    # Lay du lieu cham cong trong thang
    from datetime import date
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    records = AttendanceRecord.query.filter(
        AttendanceRecord.user_id == current_user.id,
        AttendanceRecord.date >= month_start,
        AttendanceRecord.date < month_end
    ).order_by(AttendanceRecord.date.desc()).all()

    # Thong ke
    total_hours = sum(r.total_work_hours for r in records)
    total_shifts = len(records)
    late_summary = get_monthly_late_summary(current_user.id, month, year)

    return render_template('attendance/my_attendance.html',
                           records=records,
                           month=month,
                           year=year,
                           total_hours=round(total_hours, 1),
                           total_shifts=total_shifts,
                           late_summary=late_summary)


@bp.route('/report')
@login_required
@manager_required
def report():
    """Bao cao cham cong"""
    # Loc theo thang
    month = request.args.get('month', type=int, default=datetime.now().month)
    year = request.args.get('year', type=int, default=datetime.now().year)

    from datetime import date
    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1)
    else:
        month_end = date(year, month + 1, 1)

    # Lay tat ca NV active
    users = User.query.filter_by(status='active', role=UserRole.STAFF).all()

    report_data = []
    for user in users:
        # Lay cham cong
        records = AttendanceRecord.query.filter(
            AttendanceRecord.user_id == user.id,
            AttendanceRecord.date >= month_start,
            AttendanceRecord.date < month_end
        ).all()

        total_hours = sum(r.total_work_hours for r in records)
        total_shifts = len(records)
        late_summary = get_monthly_late_summary(user.id, month, year)

        report_data.append({
            'user': user,
            'total_hours': round(total_hours, 1),
            'total_shifts': total_shifts,
            'late_count': late_summary['total_late'],
            'late_minutes': late_summary['total_minutes'],
            'total_penalty': late_summary['total_penalty']
        })

    # Sap xep theo gio lam (giam dan)
    report_data.sort(key=lambda x: x['total_hours'], reverse=True)

    return render_template('attendance/report.html',
                           report_data=report_data,
                           month=month,
                           year=year)


@bp.route('/process-late', methods=['GET', 'POST'])
@login_required
@manager_required
def process_late():
    """Xu ly di muon thu cong (GET hoac POST)"""
    if request.method == 'POST':
        date_str = request.form.get('date')
    else:
        date_str = request.args.get('date')

    if date_str:
        try:
            process_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            process_date = datetime.now().date()
    else:
        process_date = datetime.now().date()

    result = process_daily_attendance(process_date)

    if result['processed'] > 0:
        flash(f"Da xu ly {result['processed']} truong hop di muon.", 'success')
    else:
        flash("Khong co truong hop di muon can xu ly.", 'info')

    if result['errors']:
        for error in result['errors']:
            flash(error, 'warning')

    return redirect(url_for('attendance.view', date=date_str))
