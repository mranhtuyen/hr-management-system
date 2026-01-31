import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Database (SQLite for development, PostgreSQL for production)
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///hr_system.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload folders
    UPLOAD_FOLDER = 'uploads'
    EXPORT_FOLDER = 'exports'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size

    # Mail settings
    MAIL_SERVER = os.environ.get('MAIL_SERVER') or 'smtp.gmail.com'
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')

    # SMS (placeholder)
    SMS_API_KEY = os.environ.get('SMS_API_KEY')

    # Zalo OA (placeholder)
    ZALO_OA_ACCESS_TOKEN = os.environ.get('ZALO_OA_ACCESS_TOKEN')

    # Schedule config
    SCHEDULE_OPEN_DAY = 'friday'
    SCHEDULE_REMINDER_TIME = '12:00'
    SCHEDULE_DEADLINE = 'saturday_18:00'
    AUTO_SCHEDULE_TIME = 'sunday_08:00'

    # Attendance config
    LATE_GRACE_PERIOD = 5  # phut
    EARLY_BIRD_THRESHOLD = '06:55'

    # Penalties (VND)
    FIRST_LATE_PENALTY = 0
    SECOND_LATE_PENALTY = 50000
    THIRD_LATE_PENALTY = 100000

    # Meal support
    FULLTIME_THRESHOLD = 8  # gio
    MEAL_SUPPORT_AMOUNT = 25000  # VND
