from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import bp
from app.auth.forms import LoginForm, RegisterForm, ChangePasswordForm, EditUserForm
from app.models import User, UserRole, EmploymentType, ActivityLog, db
from functools import wraps


def admin_required(f):
    """Decorator yeu cau quyen Admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Ban khong co quyen truy cap trang nay.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


def manager_required(f):
    """Decorator yeu cau quyen Manager hoac Admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_manager():
            flash('Ban khong co quyen truy cap trang nay.', 'danger')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """Trang dang nhap"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if user.status != 'active':
                flash('Tai khoan da bi vo hieu hoa. Vui long lien he quan tri vien.', 'danger')
                return render_template('auth/login.html', form=form)

            login_user(user, remember=form.remember_me.data)
            # Log dang nhap
            ActivityLog.log(
                user_id=user.id,
                action='login',
                description=f'{user.full_name} da dang nhap',
                ip_address=request.remote_addr
            )
            next_page = request.args.get('next')
            flash(f'Xin chao, {user.full_name}!', 'success')
            return redirect(next_page) if next_page else redirect(url_for('dashboard.index'))
        else:
            flash('Ten dang nhap hoac mat khau khong dung.', 'danger')

    return render_template('auth/login.html', form=form)


@bp.route('/logout')
@login_required
def logout():
    """Dang xuat"""
    logout_user()
    flash('Ban da dang xuat thanh cong.', 'success')
    return redirect(url_for('auth.login'))


@bp.route('/register', methods=['GET', 'POST'])
@login_required
@admin_required
def register():
    """Tao tai khoan moi (chi Admin)"""
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            full_name=form.full_name.data,
            email=form.email.data,
            phone=form.phone.data,
            cccd=form.cccd.data,
            address_permanent=form.address_permanent.data,
            address_current=form.address_current.data,
            role=UserRole(form.role.data),
            employment_type=EmploymentType(form.employment_type.data),
            hourly_rate=form.hourly_rate.data,
            salary_percentage=form.salary_percentage.data,
            meal_support_eligible=form.meal_support_eligible.data,
            is_probation=form.is_probation.data,
            probation_salary_rate=form.probation_salary_rate.data,
            probation_start_date=form.probation_start_date.data,
            probation_end_date=form.probation_end_date.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Log tao user
        ActivityLog.log(
            user_id=current_user.id,
            action='create',
            entity_type='user',
            entity_id=user.id,
            description=f'Tao tai khoan cho {user.full_name}',
            ip_address=request.remote_addr
        )

        flash(f'Da tao tai khoan cho {user.full_name} thanh cong!', 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/register.html', form=form)


@bp.route('/users')
@login_required
@admin_required
def users():
    """Danh sach tat ca users"""
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template('auth/users.html', users=all_users)


@bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Chinh sua thong tin user"""
    user = User.query.get_or_404(user_id)
    form = EditUserForm(obj=user)

    if form.validate_on_submit():
        user.full_name = form.full_name.data
        user.email = form.email.data
        user.phone = form.phone.data
        user.cccd = form.cccd.data
        user.address_permanent = form.address_permanent.data
        user.address_current = form.address_current.data
        user.role = UserRole(form.role.data)
        user.employment_type = EmploymentType(form.employment_type.data)
        user.hourly_rate = form.hourly_rate.data
        user.salary_percentage = form.salary_percentage.data
        user.meal_support_eligible = form.meal_support_eligible.data
        user.is_probation = form.is_probation.data
        user.probation_salary_rate = form.probation_salary_rate.data
        user.probation_start_date = form.probation_start_date.data
        user.probation_end_date = form.probation_end_date.data
        user.status = form.status.data

        # Doi mat khau neu co nhap
        if form.new_password.data:
            user.set_password(form.new_password.data)
            flash('Da doi mat khau thanh cong!', 'info')

        db.session.commit()

        # Log cap nhat
        ActivityLog.log(
            user_id=current_user.id,
            action='update',
            entity_type='user',
            entity_id=user.id,
            description=f'Cap nhat thong tin {user.full_name}',
            ip_address=request.remote_addr
        )

        flash(f'Da cap nhat thong tin {user.full_name} thanh cong!', 'success')
        return redirect(url_for('auth.users'))

    # Pre-fill form
    form.role.data = user.role.value
    form.employment_type.data = user.employment_type.value
    form.status.data = user.status

    return render_template('auth/edit_user.html', form=form, user=user)


@bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@admin_required
def reset_password(user_id):
    """Reset mat khau user (Admin)"""
    user = User.query.get_or_404(user_id)
    new_password = 'password123'  # Mat khau mac dinh
    user.set_password(new_password)
    db.session.commit()

    flash(f'Da reset mat khau cho {user.full_name}. Mat khau moi: {new_password}', 'success')
    return redirect(url_for('auth.users'))


@bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Kich hoat / Vo hieu hoa tai khoan user"""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Khong the vo hieu hoa tai khoan cua chinh minh.', 'danger')
        return redirect(url_for('auth.users'))

    old_status = user.status
    if user.status == 'active':
        user.status = 'inactive'
        flash(f'Da vo hieu hoa tai khoan {user.full_name}.', 'warning')
    else:
        user.status = 'active'
        flash(f'Da kich hoat lai tai khoan {user.full_name}.', 'success')

    db.session.commit()

    # Log thay doi trang thai
    ActivityLog.log(
        user_id=current_user.id,
        action='update',
        entity_type='user',
        entity_id=user.id,
        description=f'Thay doi trang thai {user.full_name}: {old_status} -> {user.status}',
        ip_address=request.remote_addr
    )

    return redirect(url_for('auth.users'))


@bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Xoa tai khoan user"""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash('Khong the xoa tai khoan cua chinh minh.', 'danger')
        return redirect(url_for('auth.users'))

    user_name = user.full_name

    # Log truoc khi xoa
    ActivityLog.log(
        user_id=current_user.id,
        action='delete',
        entity_type='user',
        entity_id=user.id,
        description=f'Xoa tai khoan {user_name}',
        ip_address=request.remote_addr
    )

    db.session.delete(user)
    db.session.commit()

    flash(f'Da xoa tai khoan {user_name}.', 'success')
    return redirect(url_for('auth.users'))


@bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """Doi mat khau"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('Mat khau cu khong dung.', 'danger')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Doi mat khau thanh cong!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('auth/change_password.html', form=form)


@bp.route('/profile')
@login_required
def profile():
    """Xem thong tin ca nhan"""
    return render_template('auth/profile.html', user=current_user)
