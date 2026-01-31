"""
Common forms
"""

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms import StringField, TextAreaField, FloatField, DateField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional
from app.models import ViolationType, RewardType


class ViolationForm(FlaskForm):
    """Form tao vi pham"""
    user_id = SelectField('Nhan vien', coerce=int, validators=[DataRequired()])
    date = DateField('Ngay', validators=[DataRequired()])
    type = SelectField('Loai vi pham', choices=[
        (ViolationType.LATE.value, 'Di muon'),
        (ViolationType.BROKEN_ITEM.value, 'Lam vo do'),
        (ViolationType.HYGIENE.value, 'Ve sinh'),
        (ViolationType.OTHER.value, 'Khac')
    ])
    description = TextAreaField('Mo ta', validators=[Optional()])
    penalty_amount = FloatField('Tien phat (VND)', validators=[DataRequired()], default=0)
    submit = SubmitField('Luu')


class RewardForm(FlaskForm):
    """Form tao thuong"""
    user_id = SelectField('Nhan vien', coerce=int, validators=[DataRequired()])
    type = SelectField('Loai thuong', choices=[
        (RewardType.PUNCTUAL.value, 'Guong mau'),
        (RewardType.SALES.value, 'Doanh so'),
        (RewardType.REVIEW.value, 'Review'),
        (RewardType.GAME.value, 'Game'),
        (RewardType.TEST.value, 'Test')
    ])
    description = TextAreaField('Mo ta', validators=[Optional()])
    reward_amount = FloatField('Tien thuong (VND)', validators=[DataRequired()], default=0)
    submit = SubmitField('Luu')


class HolidayForm(FlaskForm):
    """Form them ngay le"""
    date = DateField('Ngay', validators=[DataRequired()])
    name = StringField('Ten ngay le', validators=[DataRequired()])
    salary_multiplier = FloatField('He so luong', validators=[DataRequired()], default=2.0)
    submit = SubmitField('Luu')


class ImportExcelForm(FlaskForm):
    """Form import file Excel"""
    file = FileField('File Excel', validators=[
        FileRequired(),
        FileAllowed(['xlsx', 'xls'], 'Chi chap nhan file Excel!')
    ])
    submit = SubmitField('Import')


class SystemConfigForm(FlaskForm):
    """Form cau hinh he thong"""
    late_grace_period = FloatField('So phut cho phep di muon', default=5)
    first_late_penalty = FloatField('Phat lan 1 (VND)', default=0)
    second_late_penalty = FloatField('Phat lan 2 (VND)', default=50000)
    third_late_penalty = FloatField('Phat lan 3+ (VND)', default=100000)
    meal_support_amount = FloatField('Tien an ca/ngay (VND)', default=25000)
    fulltime_threshold = FloatField('Gio toi thieu full-time', default=8)
    submit = SubmitField('Luu cau hinh')
