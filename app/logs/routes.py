from flask import render_template, request
from flask_login import login_required
from datetime import datetime, timedelta
from app.logs import bp
from app.auth.routes import admin_required
from app.models import ActivityLog, User, db


@bp.route('/')
@login_required
@admin_required
def index():
    """Xem lich su hoat dong"""
    # Loc theo ngay
    date_str = request.args.get('date')
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            filter_date = datetime.now().date()
    else:
        filter_date = datetime.now().date()

    # Loc theo action
    action_filter = request.args.get('action', '')

    # Loc theo user
    user_filter = request.args.get('user_id', type=int)

    # Query
    query = db.session.query(ActivityLog, User).join(User).filter(
        ActivityLog.created_at >= datetime.combine(filter_date, datetime.min.time()),
        ActivityLog.created_at < datetime.combine(filter_date + timedelta(days=1), datetime.min.time())
    )

    if action_filter:
        query = query.filter(ActivityLog.action == action_filter)

    if user_filter:
        query = query.filter(ActivityLog.user_id == user_filter)

    logs = query.order_by(ActivityLog.created_at.desc()).all()

    # Lay danh sach users de filter
    users = User.query.order_by(User.full_name).all()

    return render_template('logs/index.html',
                           logs=logs,
                           filter_date=filter_date,
                           action_filter=action_filter,
                           user_filter=user_filter,
                           users=users)


@bp.route('/all')
@login_required
@admin_required
def all_logs():
    """Xem tat ca log (phan trang)"""
    page = request.args.get('page', 1, type=int)
    per_page = 50

    # Loc theo action
    action_filter = request.args.get('action', '')

    # Loc theo user
    user_filter = request.args.get('user_id', type=int)

    # Query
    query = db.session.query(ActivityLog, User).join(User)

    if action_filter:
        query = query.filter(ActivityLog.action == action_filter)

    if user_filter:
        query = query.filter(ActivityLog.user_id == user_filter)

    # Pagination
    pagination = query.order_by(ActivityLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    logs = pagination.items

    # Lay danh sach users de filter
    users = User.query.order_by(User.full_name).all()

    return render_template('logs/all.html',
                           logs=logs,
                           pagination=pagination,
                           action_filter=action_filter,
                           user_filter=user_filter,
                           users=users)
