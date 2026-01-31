from app import create_app, db
from app.models import User, WorkSchedule, ScheduleShift, AttendanceRecord, Violation, Reward, Payroll, SystemConfig, Holiday, CustomerTraffic

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'User': User,
        'WorkSchedule': WorkSchedule,
        'ScheduleShift': ScheduleShift,
        'AttendanceRecord': AttendanceRecord,
        'Violation': Violation,
        'Reward': Reward,
        'Payroll': Payroll,
        'SystemConfig': SystemConfig,
        'Holiday': Holiday,
        'CustomerTraffic': CustomerTraffic
    }


@app.cli.command('seed')
def seed_data():
    """Tao du lieu mau cho he thong"""
    from app.models import UserRole, EmploymentType

    # Tao admin account
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            full_name='Quan Tri Vien',
            phone='0901234567',
            email='admin@example.com',
            role=UserRole.ADMIN,
            employment_type=EmploymentType.FULL_TIME,
            hourly_rate=50000,
            salary_percentage=100.0,
            meal_support_eligible=True
        )
        admin.set_password('admin123')
        db.session.add(admin)

    # Tao manager account
    manager = User.query.filter_by(username='manager').first()
    if not manager:
        manager = User(
            username='manager',
            full_name='Quan Ly',
            phone='0902345678',
            email='manager@example.com',
            role=UserRole.MANAGER,
            employment_type=EmploymentType.FULL_TIME,
            hourly_rate=45000,
            salary_percentage=100.0,
            meal_support_eligible=True
        )
        manager.set_password('manager123')
        db.session.add(manager)

    # Tao nhan vien mau
    for i in range(1, 6):
        username = f'staff{i}'
        staff = User.query.filter_by(username=username).first()
        if not staff:
            staff = User(
                username=username,
                full_name=f'Nhan Vien {i}',
                phone=f'090345678{i}',
                email=f'staff{i}@example.com',
                role=UserRole.STAFF,
                employment_type=EmploymentType.PART_TIME if i <= 3 else EmploymentType.FULL_TIME,
                hourly_rate=30000,
                salary_percentage=90.0 if i == 1 else 100.0,  # staff1 la thu viec
                meal_support_eligible=(i > 3)  # Full-time moi duoc ho tro an ca
            )
            staff.set_password('staff123')
            db.session.add(staff)

    # Tao cau hinh he thong mac dinh
    default_configs = [
        ('late_grace_period', '5', 'So phut cho phep di muon (khong phat)'),
        ('first_late_penalty', '0', 'Tien phat lan di muon thu 1'),
        ('second_late_penalty', '50000', 'Tien phat lan di muon thu 2'),
        ('third_late_penalty', '100000', 'Tien phat lan di muon thu 3+'),
        ('meal_support_amount', '25000', 'Tien ho tro an ca/ngay'),
        ('fulltime_threshold', '8', 'So gio toi thieu de tinh full-time'),
        ('schedule_open_day', 'friday', 'Ngay mo dang ky lich'),
        ('schedule_deadline', 'saturday_18:00', 'Han chot dang ky lich'),
    ]

    for key, value, description in default_configs:
        config = SystemConfig.query.filter_by(key=key).first()
        if not config:
            config = SystemConfig(key=key, value=value, description=description)
            db.session.add(config)

    db.session.commit()
    print('Da tao du lieu mau thanh cong!')
    print('Tai khoan mac dinh:')
    print('  - Admin: admin / admin123')
    print('  - Manager: manager / manager123')
    print('  - Staff: staff1-5 / staff123')


if __name__ == '__main__':
    app.run(debug=True)
