"""
Module Background Jobs su dung APScheduler

Cac job tu dong:
1. Mo dang ky lich (Thu 6, 8h)
2. Nhac nho dang ky (Thu 7, 12h)
3. Khoa dang ky (Thu 7, 18h)
4. Xep lich tu dong (Chu Nhat, 8h)
5. Xu ly cham cong hang ngay (19h)
6. Tinh luong dau thang (Ngay 1, 8h)
"""

from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()


def start_scheduler(app):
    """Khoi dong scheduler voi Flask app context"""

    # Job 1: Mo dang ky lich (Thu 6, 8h sang)
    scheduler.add_job(
        func=lambda: run_with_context(app, open_schedule_registration),
        trigger='cron',
        day_of_week='fri',
        hour=8,
        minute=0,
        id='open_schedule_registration',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Job 2: Nhac nho dang ky (Thu 7, 12h trua)
    scheduler.add_job(
        func=lambda: run_with_context(app, remind_schedule_registration),
        trigger='cron',
        day_of_week='sat',
        hour=12,
        minute=0,
        id='remind_schedule_registration',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Job 3: Khoa dang ky (Thu 7, 18h)
    scheduler.add_job(
        func=lambda: run_with_context(app, close_schedule_registration),
        trigger='cron',
        day_of_week='sat',
        hour=18,
        minute=0,
        id='close_schedule_registration',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Job 4: Xep lich tu dong (Chu Nhat, 8h sang)
    scheduler.add_job(
        func=lambda: run_with_context(app, auto_generate_weekly_schedule),
        trigger='cron',
        day_of_week='sun',
        hour=8,
        minute=0,
        id='auto_generate_schedule',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Job 5: Xu ly cham cong hang ngay (19h)
    scheduler.add_job(
        func=lambda: run_with_context(app, process_daily_attendance_job),
        trigger='cron',
        hour=19,
        minute=0,
        id='process_daily_attendance',
        replace_existing=True,
        misfire_grace_time=3600
    )

    # Job 6: Tinh luong dau thang (Ngay 1, 8h sang)
    scheduler.add_job(
        func=lambda: run_with_context(app, calculate_monthly_payrolls_job),
        trigger='cron',
        day=1,
        hour=8,
        minute=0,
        id='calculate_monthly_payrolls',
        replace_existing=True,
        misfire_grace_time=3600
    )

    scheduler.start()
    app.logger.info('Background scheduler started')


def run_with_context(app, func):
    """Chay function trong Flask app context"""
    with app.app_context():
        try:
            func()
        except Exception as e:
            app.logger.error(f'Scheduler job error: {str(e)}')


def open_schedule_registration():
    """Mo dang ky lich va gui thong bao"""
    from app.models import User, UserRole
    from app.notifications.email_sender import send_schedule_registration_email

    print(f'[{datetime.now()}] Opening schedule registration...')

    # Lay tat ca nhan vien active
    users = User.query.filter_by(status='active', role=UserRole.STAFF).all()

    # Gui email thong bao
    send_schedule_registration_email(users)

    print(f'[{datetime.now()}] Sent registration email to {len(users)} users')


def remind_schedule_registration():
    """Gui nhac nho cho NV chua dang ky"""
    from app.models import User, WorkSchedule, UserRole, ScheduleStatus
    from app.notifications.email_sender import send_schedule_reminder_email
    from app.notifications.sms_sender import send_schedule_reminder_sms

    print(f'[{datetime.now()}] Checking schedule registration...')

    # Tinh ngay dau tuan sau
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)

    # Lay NV da dang ky
    registered_user_ids = [
        s.user_id for s in WorkSchedule.query.filter(
            WorkSchedule.week_start_date == next_monday,
            WorkSchedule.status.in_([ScheduleStatus.SUBMITTED, ScheduleStatus.APPROVED])
        ).all()
    ]

    # Lay NV chua dang ky
    not_registered = User.query.filter(
        User.status == 'active',
        User.role == UserRole.STAFF,
        ~User.id.in_(registered_user_ids) if registered_user_ids else True
    ).all()

    # Gui nhac nho
    if not_registered:
        send_schedule_reminder_email(not_registered)
        for user in not_registered:
            send_schedule_reminder_sms(user)

    print(f'[{datetime.now()}] Sent reminder to {len(not_registered)} users')


def close_schedule_registration():
    """Khoa dang ky lich"""
    from app.models import WorkSchedule, ScheduleStatus, db

    print(f'[{datetime.now()}] Closing schedule registration...')

    # Tinh ngay dau tuan sau
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)

    # Khoa tat ca lich draft
    drafts = WorkSchedule.query.filter(
        WorkSchedule.week_start_date == next_monday,
        WorkSchedule.status == ScheduleStatus.DRAFT
    ).all()

    for schedule in drafts:
        schedule.status = ScheduleStatus.LOCKED

    db.session.commit()
    print(f'[{datetime.now()}] Locked {len(drafts)} draft schedules')


def auto_generate_weekly_schedule():
    """Chay thuat toan xep lich tu dong"""
    from app.schedule.auto_scheduler import auto_generate_schedule

    print(f'[{datetime.now()}] Generating weekly schedule...')

    # Tinh ngay dau tuan sau
    today = datetime.now().date()
    days_until_monday = (7 - today.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    next_monday = today + timedelta(days=days_until_monday)

    try:
        result = auto_generate_schedule(next_monday)
        print(f'[{datetime.now()}] Schedule generated: {result}')
    except Exception as e:
        print(f'[{datetime.now()}] Error generating schedule: {str(e)}')


def process_daily_attendance_job():
    """Xu ly cham cong va di muon hang ngay"""
    from app.attendance.late_checker import process_daily_attendance

    print(f'[{datetime.now()}] Processing daily attendance...')

    today = datetime.now().date()
    result = process_daily_attendance(today)

    print(f'[{datetime.now()}] Processed {result["processed"]} late records')


def calculate_monthly_payrolls_job():
    """Tinh luong cho tat ca NV"""
    from app.payroll.calculator import calculate_all_payrolls
    from app.notifications.email_sender import send_payslip_email
    from app.models import User

    print(f'[{datetime.now()}] Calculating monthly payrolls...')

    # Tinh cho thang truoc
    today = datetime.now()
    if today.month == 1:
        month = 12
        year = today.year - 1
    else:
        month = today.month - 1
        year = today.year

    payrolls = calculate_all_payrolls(month, year)

    # Gui email phieu luong
    for payroll in payrolls:
        user = User.query.get(payroll.user_id)
        if user:
            send_payslip_email(user, payroll)

    print(f'[{datetime.now()}] Calculated payroll for {len(payrolls)} users')
