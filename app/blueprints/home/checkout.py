from flask import Blueprint, session, request, redirect, render_template, url_for, flash 
from werkzeug.utils import secure_filename
from app.db import get_db_connection
from datetime import datetime
from app.config import config
import os




checkout_bp = Blueprint('checkout', __name__) #建立藍圖