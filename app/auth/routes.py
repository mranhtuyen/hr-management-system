from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app.auth import bp
from app.auth.forms import LoginForm, RegisterForm, ChangePasswordForm, EditUserForm
from app.models import User, UserRole, EmploymentType, db
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
            role=UserRole(form.role.data),
            employment_type=EmploymentType(form.employment_type.data),
            hourly_rate=form.hourly_rate.data,
            salary_percentage=form.salary_percentage.data,
            meal_support_eligible=form.meal_support_eligible.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

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
        user.role = UserRole(form.role.data)
        user.employment_type = EmploymentType(form.employment_type.data)
        user.hourly_rate = form.hourly_rate.data
        user.salary_percentage = form.salary_percentage.data
        user.meal_support_eligible = form.meal_support_eligible.data
        user.status = form.status.data

        db.session.commit()
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
