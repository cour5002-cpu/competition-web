from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import base64
import os
from datetime import datetime
import re
import pandas as pd
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import json
import sys

from dotenv import load_dotenv

if __name__ == '__main__':
    sys.modules['app'] = sys.modules[__name__]

load_dotenv()

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'mysql+pymysql://root:password@localhost/competition_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_pre_ping': True,
    'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', '280') or 280),
    'pool_timeout': int(os.environ.get('DB_POOL_TIMEOUT', '30') or 30),
    'pool_size': int(os.environ.get('DB_POOL_SIZE', '5') or 5),
    'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', '10') or 10),
    'connect_args': {
        'connect_timeout': int(os.environ.get('DB_CONNECT_TIMEOUT', '10') or 10)
    }
}

# Initialize extensions
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Encryption key for sensitive data
_encryption_key_raw = os.environ.get('ENCRYPTION_KEY')
if _encryption_key_raw is None or str(_encryption_key_raw).strip() == '':
    import hashlib
    secret = str(app.config.get('SECRET_KEY', 'dev-secret-key') or '').encode('utf-8')
    digest = hashlib.sha256(secret).digest()
    ENCRYPTION_KEY = base64.urlsafe_b64encode(digest)
else:
    import hashlib
    raw = str(_encryption_key_raw).strip()
    candidate = raw.encode('utf-8')
    try:
        Fernet(candidate)
        ENCRYPTION_KEY = candidate
    except Exception:
        digest = hashlib.sha256(candidate).digest()
        ENCRYPTION_KEY = base64.urlsafe_b64encode(digest)

cipher_suite = Fernet(ENCRYPTION_KEY)

_old_keys_raw = str(os.environ.get('OLD_ENCRYPTION_KEYS', '') or '').strip()
_old_cipher_suites = []
if _old_keys_raw:
    for k in [p.strip() for p in _old_keys_raw.split(',') if p.strip()]:
        try:
            _old_cipher_suites.append(Fernet(k.encode('utf-8')))
        except Exception:
            pass

def encrypt_data(data):
    """Encrypt sensitive data"""
    if not data:
        return None
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(encrypted_data):
    """Decrypt sensitive data"""
    if not encrypted_data:
        return None
    try:
        return cipher_suite.decrypt(encrypted_data.encode()).decode()
    except Exception:
        for cs in _old_cipher_suites:
            try:
                return cs.decrypt(encrypted_data.encode()).decode()
            except Exception:
                continue
        raise

def mask_phone(phone):
    """Mask phone number for display"""
    if not phone or len(phone) != 11:
        return phone
    return phone[:3] + "****" + phone[-4:]

def mask_email(email):
    """Mask email for display"""
    if not email or '@' not in email:
        return email
    local, domain = email.split('@', 1)
    if len(local) <= 2:
        return email
    return local[0] + "*" * (len(local) - 2) + local[-1] + "@" + domain

# Import routes
from routes import api_bp
from admin_routes import admin_bp
from certificate_routes import certificate_bp

# Register blueprints
app.register_blueprint(api_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(certificate_bp)


def _ensure_default_certificate_templates():
    try:
        with app.app_context():
            import models  # noqa: F401
            db.create_all()

            from models import CertificateTemplate

            def _has_texts(cfg: dict) -> bool:
                try:
                    return bool(isinstance(cfg, dict) and isinstance(cfg.get('texts'), list) and len(cfg.get('texts')) > 0)
                except Exception:
                    return False

            def _player_default_config():
                return {
                    'background_image': 'assets/cert/player.png',
                    'global_y_offset': -6,
                    'debug_points': False,
                    'texts': [
                        {
                            'field': 'participants_names',
                            'font': '宋体',
                            'font_size': 16,
                            'line_height': 18,
                            'wrap': True,
                            'max_lines': 2,
                            'align': 'center',
                            'direction': 'up',
                            'width': 25.05,
                            'x': 37.39,
                            'x_anchor': 'left',
                            'y': 128.37,
                            'y_offset': 6
                        },
                        {
                            'field': 'category',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 60,
                            'x': 60,
                            'x_anchor': 'center',
                            'y': 121,
                            'y_offset': 6
                        },
                        {
                            'field': 'education_level',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 60,
                            'x': 135,
                            'x_anchor': 'center',
                            'y': 121,
                            'y_offset': 6
                        },
                        {
                            'field': 'award_level',
                            'font': '华文楷体',
                            'font_size': 84,
                            'align': 'center',
                            'width': 150,
                            'x': 29.5,
                            'x_anchor': 'left',
                            'y': 74,
                            'y_offset': 2
                        }
                    ]
                }

            def _coach_default_config():
                return {
                    'background_image': 'assets/cert/coach.png',
                    'global_y_offset': -6,
                    'debug_points': False,
                    'texts': [
                        {
                            'field': 'teacher_name',
                            'font': '宋体',
                            'font_size': 16,
                            'line_height': 18,
                            'wrap': True,
                            'max_lines': 2,
                            'align': 'center',
                            'direction': 'up',
                            'width': 24.69,
                            'x': 52.96,
                            'x_anchor': 'left',
                            'y': 127.67,
                            'y_offset': 6.5
                        },
                        {
                            'field': 'category',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 80,
                            'x': 90,
                            'x_anchor': 'center',
                            'y': 121,
                            'y_offset': 6
                        },
                        {
                            'field': 'award_level',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 80,
                            'x': 90,
                            'x_anchor': 'center',
                            'y': 112,
                            'y_offset': 6
                        }
                    ]
                }

            existing_count = CertificateTemplate.query.count()
            if existing_count == 0:
                player = CertificateTemplate(
                    name='选手版-一等奖(默认)',
                    category='通用',
                    award_level='一等奖'
                )
                player.set_config(_player_default_config())

                coach = CertificateTemplate(
                    name='辅导员版-一等奖(默认)',
                    category='通用',
                    award_level='一等奖-辅导员'
                )
                coach.set_config(_coach_default_config())

                db.session.add(player)
                db.session.add(coach)
                db.session.commit()
                return

            templates = CertificateTemplate.query.all()
            dirty = False
            for t in templates:
                try:
                    cfg = t.get_config() or {}
                except Exception:
                    cfg = {}

                if _has_texts(cfg):
                    continue

                if str(getattr(t, 'award_level', '') or '').strip() == '一等奖':
                    t.set_config(_player_default_config())
                    dirty = True
                elif str(getattr(t, 'award_level', '') or '').strip() == '一等奖-辅导员':
                    t.set_config(_coach_default_config())
                    dirty = True

            if dirty:
                db.session.commit()
    except Exception:
        pass


_ensure_default_certificate_templates()

if __name__ == '__main__':
    with app.app_context():
        # Ensure models are registered before creating tables
        import models  # noqa: F401
        db.create_all()

        # Seed default certificate templates after DB reset (stored in DB, not filesystem)
        try:
            from models import CertificateTemplate

            existing_count = CertificateTemplate.query.count()
            if existing_count == 0:
                # Use award_level-only fallback in certificate_routes.py (any category)
                player = CertificateTemplate(
                    name='选手版-一等奖(默认)',
                    category='通用',
                    award_level='一等奖'
                )
                player.set_config({
                    'background_image': 'assets/cert/player.png',
                    'global_y_offset': -6,
                    'debug_points': False,
                    'texts': [
                        {
                            'field': 'participants_names',
                            'font': '宋体',
                            'font_size': 16,
                            'line_height': 18,
                            'wrap': True,
                            'max_lines': 2,
                            'align': 'center',
                            'direction': 'up',
                            'width': 25.05,
                            'x': 37.39,
                            'x_anchor': 'left',
                            'y': 128.37,
                            'y_offset': 6
                        },
                        {
                            'field': 'category',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 60,
                            'x': 60,
                            'x_anchor': 'center',
                            'y': 121,
                            'y_offset': 6
                        },
                        {
                            'field': 'education_level',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 60,
                            'x': 135,
                            'x_anchor': 'center',
                            'y': 121,
                            'y_offset': 6
                        },
                        {
                            'field': 'award_level',
                            'font': '华文楷体',
                            'font_size': 84,
                            'align': 'center',
                            'width': 150,
                            'x': 29.5,
                            'x_anchor': 'left',
                            'y': 74,
                            'y_offset': 2
                        }
                    ]
                })

                coach = CertificateTemplate(
                    name='辅导员版-一等奖(默认)',
                    category='通用',
                    award_level='一等奖-辅导员'
                )
                coach.set_config({
                    'background_image': 'assets/cert/coach.png',
                    'global_y_offset': -6,
                    'debug_points': False,
                    'texts': [
                        {
                            'field': 'teacher_name',
                            'font': '宋体',
                            'font_size': 16,
                            'line_height': 18,
                            'wrap': True,
                            'max_lines': 2,
                            'align': 'center',
                            'direction': 'up',
                            'width': 24.69,
                            'x': 52.96,
                            'x_anchor': 'left',
                            'y': 127.67,
                            'y_offset': 6.5
                        },
                        {
                            'field': 'category',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 80,
                            'x': 90,
                            'x_anchor': 'center',
                            'y': 121,
                            'y_offset': 6
                        },
                        {
                            'field': 'award_level',
                            'font': '宋体',
                            'font_size': 16,
                            'align': 'center',
                            'width': 80,
                            'x': 90,
                            'x_anchor': 'center',
                            'y': 112,
                            'y_offset': 6
                        }
                    ]
                })

                db.session.add(player)
                db.session.add(coach)
                db.session.commit()
        except Exception:
            pass
    app.run(debug=True, host='0.0.0.0', port=5001)
