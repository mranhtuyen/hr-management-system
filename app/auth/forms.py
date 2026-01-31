from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, FloatField
from wtforms.validators import DataRequired, Email, EqualTo, ValidationError, Optional
from app.models import User, UserRole, EmploymentType


class LoginForm(FlaskForm):
    """Form dang nhap"""
    username = StringField('Ten dang nhap', validators=[DataRequired()])
    password = PasswordField('Mat khau', validators=[DataRequired()])
    remember_me = BooleanField('Ghi nho dang nhap')
    submit = SubmitField('Dang nhap')


class RegisterForm(FlaskForm):
    """Form tao tai khoan moi (chi Admin dung)"""
    username = StringField('Ten dang nhap', validators=[DataRequired()])
    full_name = StringField('Ho va ten', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('So dien thoai', validators=[Optional()])
    password = PasswordField('Mat khau', validators=[DataRequired()])
    password2 = PasswordField('Xac nhan mat khau', validators=[DataRequired(), EqualTo('password')])

    role = SelectField('Vai tro', choices=[
        (UserRole.STAFF.value, 'Nhan vien'),
        (UserRole.MANAGER.value, 'Quan ly'),
        (UserRole.ADMIN.value, 'Admin')
    ])

    employment_type = SelectField('Loai nhan vien', choices=[
        (EmploymentType.PART_TIME.value, 'Part-time'),
        (EmploymentType.FULL_TIME.value, 'Full-time')
    ])

    hourly_rate = FloatField('Luong theo gio (VND)', validators=[DataRequired()], default=30000)
    salary_percentage = FloatField('Ty le luong (%)', validators=[DataRequired()], default=100.0)
    meal_support_eligible = BooleanField('Duoc ho tro an ca')

    submit = SubmitField('Tao tai khoan')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Ten dang nhap da ton tai. Vui long chon ten khac.')


class ChangePasswordForm(FlaskForm):
    """Form doi mat khau"""
    old_password = PasswordField('Mat khau cu', validators=[DataRequired()])
    new_password = PasswordField('Mat khau moi', validators=[DataRequired()])
    new_password2 = PasswordField('Xac nhan mat khau moi', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Doi mat khau')


class EditUserForm(FlaskForm):
    """Form chinh sua thong tin user"""
    full_name = StringField('Ho va ten', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('So dien thoai', validators=[Optional()])

    role = SelectField('Vai tro', choices=[
        (UserRole.STAFF.value, 'Nhan vien'),
        (UserRole.MANAGER.value, 'Quan ly'),
        (UserRole.ADMIN.value, 'Admin')
    ])

    employment_type = SelectField('Loai nhan vien', choices=[
        (EmploymentType.PART_TIME.value, 'Part-time'),
        (EmploymentType.FULL_TIME.value, 'Full-time')
    ])

    hourly_rate = FloatField('Luong theo gio (VND)', validators=[DataRequired()])
    salary_percentage = FloatField('Ty le luong (%)', validators=[DataRequired()])
    meal_support_eligible = BooleanField('Duoc ho tro an ca')
    status = SelectField('Trang thai', choices=[
        ('active', 'Dang lam viec'),
        ('inactive', 'Da nghi viec')
    ])

    submit = SubmitField('Cap nhat')
