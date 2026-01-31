"""
Module gui thong bao qua Zalo OA
(Placeholder - can dang ky Zalo OA Official Account)
"""

from flask import current_app
import requests


def send_zalo_message(user_id, message):
    """
    Gui tin nhan qua Zalo OA

    Args:
        user_id: Zalo user ID
        message: Noi dung tin nhan

    Returns:
        bool: Thanh cong hay khong
    """
    # TODO: Tich hop voi Zalo OA API
    # https://developers.zalo.me/docs/api/official-account-api

    try:
        access_token = current_app.config.get('ZALO_OA_ACCESS_TOKEN')
        if not access_token:
            current_app.logger.warning('Zalo OA access token not configured')
            return False

        # API endpoint
        url = 'https://openapi.zalo.me/v2.0/oa/message'

        headers = {
            'access_token': access_token,
            'Content-Type': 'application/json'
        }

        payload = {
            'recipient': {
                'user_id': user_id
            },
            'message': {
                'text': message
            }
        }

        # Hien tai chi log, chua gui thuc
        current_app.logger.info(f'[ZALO] To: {user_id} | Message: {message}')
        print(f'[ZALO] To: {user_id} | Message: {message}')

        # Uncomment de gui thuc:
        # response = requests.post(url, headers=headers, json=payload)
        # return response.status_code == 200

        return True

    except Exception as e:
        current_app.logger.error(f'Error sending Zalo message: {str(e)}')
        return False


def send_late_zalo(user, late_count, late_minutes, penalty):
    """
    Gui thong bao di muon qua Zalo
    """
    # TODO: Can luu tru zalo_user_id trong User model
    # Hien tai chua co nen chi log

    if late_count == 1:
        message = f"Ban di muon {late_minutes} phut. Lan 1, chua phat. Hay di dung gio nhe!"
    else:
        message = f"Ban di muon {late_minutes} phut. Lan {late_count}, phat {penalty:,.0f}d. De nghi di dung gio."

    print(f'[ZALO] To: {user.full_name} | {message}')
    return True
