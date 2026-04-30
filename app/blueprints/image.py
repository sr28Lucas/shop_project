from flask import Blueprint, send_from_directory
from app.config import config
import os


image_bp = Blueprint('image', __name__)



@image_bp.route('/<filename>')
def route_image(filename):
    upload_path = os.path.abspath(config.UPLOAD_FOLDER)
    return send_from_directory(upload_path, filename)