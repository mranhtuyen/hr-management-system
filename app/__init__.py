import os
from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect
from config import Config

from app.models import db

migrate = Migrate()
login_manager = LoginManager()
mail = Mail()
csrf = CSRFProtect()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Vui long dang nhap de tiep tuc.'
    login_manager.login_message_category = 'warning'

    # Import models
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints
    from app.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.dashboard import bp as dashboard_bp
    app.register_blueprint(dashboard_bp, url_prefix='/dashboard')

    from app.schedule import bp as schedule_bp
    app.register_blueprint(schedule_bp, url_prefix='/schedule')

    from app.attendance import bp as attendance_bp
    app.register_blueprint(attendance_bp, url_prefix='/attendance')

    from app.payroll import bp as payroll_bp
    app.register_blueprint(payroll_bp, url_prefix='/payroll')

    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Create upload/export folders
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    os.makedirs(app.config.get('EXPORT_FOLDER', 'exports'), exist_ok=True)

    # Start background scheduler (only in production or main process)
    if not app.debug or os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        try:
            from app.scheduler.jobs import start_scheduler
            start_scheduler(app)
        except Exception as e:
            app.logger.warning(f'Could not start scheduler: {e}')

    return app
