from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from enum import Enum

db = SQLAlchemy()


# ============================================================
# ENUMS
# ============================================================

class UserRole(str, Enum):
    STAFF = 'staff'
    MANAGER = 'manager'
    ADMIN = 'admin'


class EmploymentType(str, Enum):
    PART_TIME = 'part_time'
    FULL_TIME = 'full_time'


class ScheduleStatus(str, Enum):
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    APPROVED = 'approved'
    LOCKED = 'locked'


class ShiftType(str, Enum):
    MORNING = 'morning'      # 7h-12h
    AFTERNOON = 'afternoon'  # 12h-18h
    EVENING = 'evening'      # 18h-22h


class ViolationType(str, Enum):
    LATE = 'late'
    BROKEN_ITEM = 'broken_item'
    HYGIENE = 'hygiene'
    OTHER = 'other'


class RewardType(str, Enum):
    PUNCTUAL = 'punctual'
    SALES = 'sales'
    REVIEW = 'review'
    GAME = 'game'
    TEST = 'test'


class PayrollStatus(str, Enum):
    DRAFT = 'draft'
    APPROVED = 'approved'
    PAID = 'paid'


# ============================================================
# MODELS
# ============================================================

class User(UserMixin, db.Model):
    """Model nguoi dung - Nhan vien, Quan ly, Admin"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))

    # Thong tin bo sung
    cccd = db.Column(db.String(20))  # Can cuoc cong dan
    address_permanent = db.Column(db.String(255))  # Dia chi nguyen quan
    address_current = db.Column(db.String(255))  # Dia chi hien tai

    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.STAFF)
    employment_type = db.Column(db.Enum(EmploymentType), nullable=False, default=EmploymentType.PART_TIME)
    hourly_rate = db.Column(db.Float, nullable=False, default=30000)  # Luong gio (VND)
    salary_percentage = db.Column(db.Float, default=100.0)  # 90% thu viec, 100% chinh thuc
    meal_support_eligible = db.Column(db.Boolean, default=False)  # Duoc ho tro an ca

    # Thong tin thu viec
    is_probation = db.Column(db.Boolean, default=False)  # Dang thu viec
    probation_salary_rate = db.Column(db.Float, default=85.0)  # Ty le luong thu viec (%)
    probation_start_date = db.Column(db.Date)  # Ngay bat dau thu viec
    probation_end_date = db.Column(db.Date)  # Ngay ket thuc thu viec

    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    schedules = db.relationship('WorkSchedule', backref='user', lazy=True, foreign_keys='WorkSchedule.user_id')
    attendance_records = db.relationship('AttendanceRecord', backref='user', lazy=True)
    violations = db.relationship('Violation', backref='user', lazy=True, foreign_keys='Violation.user_id')
    rewards = db.relationship('Reward', backref='user', lazy=True)
    payrolls = db.relationship('Payroll', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == UserRole.ADMIN

    def is_manager(self):
        return self.role in [UserRole.ADMIN, UserRole.MANAGER]

    def __repr__(self):
        return f'<User {self.username}>'


class WorkSchedule(db.Model):
    """Lich lam viec hang tuan cua nhan vien"""
    __tablename__ = 'work_schedules'

    id = db.Column(db.Integer, primary_key=True)
    week_start_date = db.Column(db.Date, nullable=False)
    week_end_date = db.Column(db.Date, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    status = db.Column(db.Enum(ScheduleStatus), default=ScheduleStatus.DRAFT)
    submitted_at = db.Column(db.DateTime)
    approved_at = db.Column(db.DateTime)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relationships
    shifts = db.relationship('ScheduleShift', backref='schedule', lazy=True, cascade='all, delete-orphan')
    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<WorkSchedule {self.user_id} - Week {self.week_start_date}>'


class ScheduleShift(db.Model):
    """Chi tiet ca lam viec trong tuan"""
    __tablename__ = 'schedule_shifts'

    id = db.Column(db.Integer, primary_key=True)
    schedule_id = db.Column(db.Integer, db.ForeignKey('work_schedules.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.Enum(ShiftType), nullable=False)
    shift_start_time = db.Column(db.Time, nullable=False)
    shift_end_time = db.Column(db.Time, nullable=False)

    is_preferred = db.Column(db.Boolean, default=True)  # Nguyen vong cua NV
    is_confirmed = db.Column(db.Boolean, default=False)  # Da duoc duyet
    is_and_condition = db.Column(db.Boolean, default=False)  # "va" hay "hoac"

    # THEM 2 COT MOI de phan biet lich NV dang ky va lich he thong xep
    shift_source = db.Column(db.String(20), default='employee')  # 'employee' hoac 'system'
    draft_status = db.Column(db.String(20), default='final')     # 'draft' hoac 'final'

    def __repr__(self):
        return f'<ScheduleShift {self.date} - {self.shift_type.value}>'


class AttendanceRecord(db.Model):
    """Ban ghi cham cong hang ngay"""
    __tablename__ = 'attendance_records'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    shift_type = db.Column(db.Enum(ShiftType), nullable=False)

    scheduled_start = db.Column(db.Time, nullable=False)
    scheduled_end = db.Column(db.Time, nullable=False)
    actual_checkin = db.Column(db.Time)
    actual_checkout = db.Column(db.Time)

    late_minutes = db.Column(db.Integer, default=0)
    early_departure_minutes = db.Column(db.Integer, default=0)
    total_work_hours = db.Column(db.Float, default=0.0)

    is_late = db.Column(db.Boolean, default=False)
    is_early_bird = db.Column(db.Boolean, default=False)  # Di truoc 6h55

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<AttendanceRecord {self.user_id} - {self.date}>'


class Violation(db.Model):
    """Vi pham cua nhan vien (di muon, loi khac)"""
    __tablename__ = 'violations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    date = db.Column(db.Date, nullable=False)
    type = db.Column(db.Enum(ViolationType), nullable=False)
    description = db.Column(db.Text)
    penalty_amount = db.Column(db.Float, default=0.0)
    late_count_in_month = db.Column(db.Integer, default=0)  # Lan thu may trong thang

    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    approver = db.relationship('User', foreign_keys=[approved_by])

    def __repr__(self):
        return f'<Violation {self.user_id} - {self.type.value}>'


class Reward(db.Model):
    """Thuong cho nhan vien (guong mau, doanh so, review...)"""
    __tablename__ = 'rewards'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    week_start_date = db.Column(db.Date)
    type = db.Column(db.Enum(RewardType), nullable=False)
    description = db.Column(db.Text)
    reward_amount = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Reward {self.user_id} - {self.type.value}>'


class Payroll(db.Model):
    """Bang luong thang"""
    __tablename__ = 'payroll'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    month = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    total_work_hours = db.Column(db.Float, default=0.0)
    total_shifts = db.Column(db.Integer, default=0)
    late_count = db.Column(db.Integer, default=0)

    total_penalty = db.Column(db.Float, default=0.0)
    total_reward = db.Column(db.Float, default=0.0)
    meal_support_amount = db.Column(db.Float, default=0.0)
    advance_payment = db.Column(db.Float, default=0.0)  # Tien tam ung

    gross_salary = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)

    status = db.Column(db.Enum(PayrollStatus), default=PayrollStatus.DRAFT)
    approved_at = db.Column(db.DateTime)
    paid_at = db.Column(db.DateTime)

    # Unique constraint: 1 user chi co 1 payroll/thang
    __table_args__ = (
        db.UniqueConstraint('user_id', 'month', 'year', name='unique_user_month_year'),
    )

    def __repr__(self):
        return f'<Payroll {self.user_id} - {self.month}/{self.year}>'


class SystemConfig(db.Model):
    """Cau hinh he thong (muc phat, luong, deadline...)"""
    __tablename__ = 'system_config'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)

    @staticmethod
    def get_value(key, default=None):
        """Lay gia tri cau hinh theo key"""
        config = SystemConfig.query.filter_by(key=key).first()
        return config.value if config else default

    def __repr__(self):
        return f'<SystemConfig {self.key}>'


class Holiday(db.Model):
    """Ngay le (co he so luong 200% hoac 300%)"""
    __tablename__ = 'holidays'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True)
    name = db.Column(db.String(100), nullable=False)
    salary_multiplier = db.Column(db.Float, default=2.0)  # 200% hoac 300%

    def __repr__(self):
        return f'<Holiday {self.name} - {self.date}>'


class CustomerTraffic(db.Model):
    """Du lieu luong khach tu iPOS (de xep lich gio dong)"""
    __tablename__ = 'customer_traffic'

    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    hour_segment = db.Column(db.String(20), nullable=False)  # "9h-10h", "10h-11h"
    bill_count = db.Column(db.Integer, default=0)
    is_peak_hour = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<CustomerTraffic {self.date} - {self.hour_segment}>'


class Notification(db.Model):
    """Thong bao trong he thong"""
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50))  # 'late', 'schedule', 'payroll', 'reward', 'system'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

    def __repr__(self):
        return f'<Notification {self.user_id} - {self.title}>'


class ActivityLog(db.Model):
    """Log hoat dong cua user (dang nhap, them, sua, xoa)"""
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # 'login', 'create', 'update', 'delete'
    entity_type = db.Column(db.String(50))  # 'user', 'schedule', 'attendance', 'payroll'
    entity_id = db.Column(db.Integer)
    description = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='activity_logs')

    @staticmethod
    def log(user_id, action, entity_type=None, entity_id=None, description=None, ip_address=None):
        """Tao log moi"""
        log = ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description,
            ip_address=ip_address
        )
        db.session.add(log)
        db.session.commit()
        return log

    def __repr__(self):
        return f'<ActivityLog {self.user_id} - {self.action}>'


class ScheduleSettings(db.Model):
    """Cai dat lich dang ky"""
    __tablename__ = 'schedule_settings'

    id = db.Column(db.Integer, primary_key=True)
    deadline_day = db.Column(db.Integer, default=6)  # Thu 7 (0=Mon, 6=Sun)
    deadline_hour = db.Column(db.Integer, default=18)  # 18h
    deadline_minute = db.Column(db.Integer, default=0)
    late_registration_message = db.Column(db.Text, default='Ban da dang ky muon, Hay luu y.')
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    @staticmethod
    def get_settings():
        """Lay cai dat hien tai"""
        settings = ScheduleSettings.query.first()
        if not settings:
            settings = ScheduleSettings()
            db.session.add(settings)
            db.session.commit()
        return settings

    def __repr__(self):
        return f'<ScheduleSettings deadline={self.deadline_day} {self.deadline_hour}:{self.deadline_minute}>'
