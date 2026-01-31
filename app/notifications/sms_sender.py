"""
Module gui SMS thong bao
(Placeholder - can tich hop voi SMS Gateway thuc te)
"""

from flask import current_app


def send_sms(phone, message):
    """
    Gui SMS

    Args:
        phone: So dien thoai
        message: Noi dung tin nhan

    Returns:
        bool: Thanh cong hay khong
    """
    # TODO: Tich hop voi SMS Gateway (Twilio, Nexmo, VNPT, Viettel...)
    # Hien tai chi log ra console

    try:
        current_app.logger.info(f'[SMS] To: {phone} | Message: {message}')
        print(f'[SMS] To: {phone} | Message: {message}')
        return True
    except Exception as e:
        current_app.logger.error(f'Error sending SMS: {str(e)}')
        return False


def send_late_sms(user, late_count, late_minutes, penalty):
    """
    Gui SMS thong bao di muon

    Args:
        user: User object
        late_count: Lan di muon thu may
        late_minutes: So phut muon
        penalty: Tien phat
    """
    if not user.phone:
        return False

    if late_count == 1:
        message = f"[HR] Ban di muon {late_minutes} phut. Lan 1, chua phat. Hay di dung gio!"
    else:
        message = f"[HR] Ban di muon {late_minutes} phut. Lan {late_count}, phat {penalty:,.0f}d. De nghi di dung gio."

    return send_sms(user.phone, message)


def send_schedule_reminder_sms(user):
    """
    Gui SMS nhac dang ky lich
    """
    if not user.phone:
        return False

    message = "[HR] Ban chua dang ky lich tuan sau. Han cuoi: 18h Thu 7. Vui long dang ky ngay!"
    return send_sms(user.phone, message)


def send_schedule_confirmed_sms(user, shift_count):
    """
    Gui SMS xac nhan lich
    """
    if not user.phone:
        return False

    message = f"[HR] Lich lam viec tuan sau da xac nhan. Ban co {shift_count} ca. Xem chi tiet tren he thong."
    return send_sms(user.phone, message)
