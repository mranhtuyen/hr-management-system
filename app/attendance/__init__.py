from flask import Blueprint

bp = Blueprint('attendance', __name__)

from app.attendance import routes
