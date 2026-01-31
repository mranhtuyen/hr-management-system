from flask import Blueprint

bp = Blueprint('payroll', __name__)

from app.payroll import routes
