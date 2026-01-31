from flask_wtf import FlaskForm
from wtforms import SubmitField, SelectField, BooleanField, FieldList, FormField
from wtforms.validators import Optional
from app.models import ShiftType


class ShiftPreferenceForm(FlaskForm):
    """Form chon ca lam viec cho 1 ngay"""
    class Meta:
        csrf = False  # Disable CSRF for nested form

    morning = BooleanField('Ca Sang (7h-12h)')
    afternoon = BooleanField('Ca Chieu (12h-18h)')
    evening = BooleanField('Ca Toi (18h-22h)')
    is_and_condition = BooleanField('Muon lam CA (neu chon 2 ca tro len)')


class WeeklyScheduleForm(FlaskForm):
    """Form dang ky lich lam viec tuan"""
    # 7 ngay trong tuan
    monday = FormField(ShiftPreferenceForm, label='Thu 2')
    tuesday = FormField(ShiftPreferenceForm, label='Thu 3')
    wednesday = FormField(ShiftPreferenceForm, label='Thu 4')
    thursday = FormField(ShiftPreferenceForm, label='Thu 5')
    friday = FormField(ShiftPreferenceForm, label='Thu 6')
    saturday = FormField(ShiftPreferenceForm, label='Thu 7')
    sunday = FormField(ShiftPreferenceForm, label='Chu Nhat')

    submit = SubmitField('Gui dang ky')


class ScheduleReviewForm(FlaskForm):
    """Form duyet lich lam viec"""
    action = SelectField('Hanh dong', choices=[
        ('approve', 'Duyet'),
        ('reject', 'Tu choi')
    ])
    submit = SubmitField('Xac nhan')
