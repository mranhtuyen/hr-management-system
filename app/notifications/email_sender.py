"""
Module gui email thong bao
"""

from flask import current_app, render_template_string
from flask_mail import Message
from app import mail


def send_email(to, subject, body, html=None):
    """
    Gui email

    Args:
        to: Email nguoi nhan (string hoac list)
        subject: Tieu de
        body: Noi dung text
        html: Noi dung HTML (optional)
    """
    try:
        msg = Message(
            subject=subject,
            recipients=[to] if isinstance(to, str) else to,
            body=body,
            html=html
        )
        mail.send(msg)
        return True
    except Exception as e:
        current_app.logger.error(f'Error sending email: {str(e)}')
        return False


def send_schedule_registration_email(users):
    """
    Gui email nhac dang ky lich lam viec

    Args:
        users: List User objects
    """
    subject = "[HR] Mo dang ky lich lam viec tuan sau"

    body = """
Xin chao,

He thong da mo dang ky lich lam viec cho tuan sau.

Vui long dang nhap va dang ky lich lam viec truoc 18h Thu Bay.

Link dang ky: {url}

Tran trong,
HR Management System
    """

    for user in users:
        if user.email:
            try:
                send_email(user.email, subject, body)
            except Exception as e:
                current_app.logger.error(f'Error sending to {user.email}: {str(e)}')


def send_schedule_reminder_email(users):
    """
    Gui email nhac nho NV chua dang ky lich

    Args:
        users: List User objects chua dang ky
    """
    subject = "[HR] NHAC NHO: Ban chua dang ky lich lam viec"

    body = """
Xin chao {name},

Ban CHUA DANG KY lich lam viec cho tuan sau.

Han cuoi dang ky: 18h Thu Bay hom nay.

Vui long dang ky ngay de tranh bi xep lich tu dong.

Tran trong,
HR Management System
    """

    for user in users:
        if user.email:
            try:
                personalized_body = body.format(name=user.full_name)
                send_email(user.email, subject, personalized_body)
            except Exception as e:
                current_app.logger.error(f'Error sending reminder to {user.email}: {str(e)}')


def send_schedule_confirmed_email(user, week_start, shifts):
    """
    Gui email xac nhan lich lam viec

    Args:
        user: User object
        week_start: Ngay dau tuan
        shifts: List ScheduleShift objects
    """
    if not user.email:
        return False

    subject = f"[HR] Lich lam viec tuan {week_start.strftime('%d/%m/%Y')}"

    shift_lines = []
    for shift in shifts:
        day_names = ['Thu 2', 'Thu 3', 'Thu 4', 'Thu 5', 'Thu 6', 'Thu 7', 'CN']
        day_name = day_names[shift.date.weekday()]
        shift_lines.append(
            f"- {day_name} ({shift.date.strftime('%d/%m')}): "
            f"{shift.shift_start_time.strftime('%H:%M')} - {shift.shift_end_time.strftime('%H:%M')}"
        )

    body = f"""
Xin chao {user.full_name},

Lich lam viec cua ban tuan {week_start.strftime('%d/%m/%Y')} da duoc xac nhan:

{chr(10).join(shift_lines)}

Vui long di lam dung gio.

Tran trong,
HR Management System
    """

    return send_email(user.email, subject, body)


def send_late_notification(user, late_count, late_minutes, penalty):
    """
    Gui email thong bao di muon

    Args:
        user: User object
        late_count: Lan di muon thu may trong thang
        late_minutes: So phut muon
        penalty: Tien phat
    """
    if not user.email:
        return False

    if late_count == 1:
        subject = "[HR] Nhac nho di muon"
        body = f"""
Xin chao {user.full_name},

Ban da di muon {late_minutes} phut.

Day la lan dau trong thang nen chua bi phat.
Hay co gang di lam dung gio!

Tran trong,
HR Management System
        """
    else:
        subject = f"[HR] Canh bao di muon lan {late_count}"
        body = f"""
Xin chao {user.full_name},

Ban da di muon {late_minutes} phut.

Day la lan thu {late_count} trong thang.
Tien phat: {penalty:,.0f} VND

De nghi ban tuan thu di lam dung gio.

Tran trong,
HR Management System
        """

    return send_email(user.email, subject, body)


def send_payslip_email(user, payroll):
    """
    Gui email phieu luong

    Args:
        user: User object
        payroll: Payroll object
    """
    if not user.email:
        return False

    subject = f"[HR] Phieu luong thang {payroll.month}/{payroll.year}"

    body = f"""
Xin chao {user.full_name},

Phieu luong thang {payroll.month}/{payroll.year} cua ban:

- Tong gio lam: {payroll.total_work_hours} gio
- So ca lam: {payroll.total_shifts} ca
- Luong gop: {payroll.gross_salary:,.0f} VND
- Tien an ca: {payroll.meal_support_amount:,.0f} VND
- Tien thuong: {payroll.total_reward:,.0f} VND
- Tien phat: {payroll.total_penalty:,.0f} VND
- Tam ung: {payroll.advance_payment:,.0f} VND

THUC LINH: {payroll.net_salary:,.0f} VND

Vui long dang nhap he thong de xem chi tiet va tai phieu luong PDF.

Tran trong,
HR Management System
    """

    return send_email(user.email, subject, body)
