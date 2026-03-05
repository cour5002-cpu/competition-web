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
                    'background_fit': 'contain',
                    'coord_unit': 'px',
                    'y_origin': 'top',
                    'use_background_size': True,
                    'global_y_offset': 0,
                    'debug_points': False,
                    'texts': [
                        {
                            # 赛别：x=676-839, y=447-479 (top-origin px)
                            'field': 'category',
                            'font': '宋体',
                            'font_size': 24,
                            'align': 'center',
                            'width': 163,
                            'x': 676,
                            'x_anchor': 'left',
                            'y': 468,
                        },
                        {
                            # 组别：x=874-1093, y=447-479
                            'field': 'education_level',
                            'font': '宋体',
                            'font_size': 24,
                            'align': 'center',
                            'width': 219,
                            'x': 874,
                            'x_anchor': 'left',
                            'y': 468,
                        },
                        {
                            # 奖项级别：y=483-620，要求水平居中显示
                            'field': 'award_level',
                            'font': '华文楷体',
                            'font_size': 84,
                            'align': 'center',
                            'width': 1187,
                            'x': 37,
                            'x_anchor': 'left',
                            'y': 560,
                        },
                        {
                            # 选手姓名（截图中位于标题下方居中，先用可配置的大居中框）
                            'field': 'participants_names',
                            'font': '宋体',
                            'font_size': 28,
                            'align': 'center',
                            'width': 1187,
                            'x': 37,
                            'x_anchor': 'left',
                            'y': 410,
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

                # Repair layout defaults for player template to avoid blank areas.
                try:
                    if str(getattr(t, 'award_level', '') or '').strip() == '一等奖':
                        need_reset = False
                        if not isinstance(cfg, dict):
                            need_reset = True
                        else:
                            if str(cfg.get('coord_unit', '') or '').strip().lower() != 'px':
                                need_reset = True
                            if str(cfg.get('y_origin', '') or '').strip().lower() != 'top':
                                need_reset = True
                            if not bool(cfg.get('use_background_size')):
                                need_reset = True
                            if not cfg.get('background_image'):
                                need_reset = True
                            if not (isinstance(cfg.get('texts'), list) and len(cfg.get('texts')) >= 3):
                                need_reset = True

                            # Ensure the centered boxes are aligned with x=37..1224.
                            try:
                                texts = cfg.get('texts') if isinstance(cfg, dict) else None
                                if isinstance(texts, list):
                                    for it in texts:
                                        if not isinstance(it, dict):
                                            continue
                                        f = str(it.get('field', '') or '').strip()
                                        if f in ('award_level', 'participants_names'):
                                            if int(it.get('x', -9999) or 0) != 37:
                                                need_reset = True
                                            if int(it.get('width', -9999) or 0) != 1187:
                                                need_reset = True
                            except Exception:
                                pass

                        if need_reset:
                            t.set_config(_player_default_config())
                            dirty = True
                        else:
                            # Template structure is OK; still sync key layout fields to latest numbers.
                            try:
                                cfg2 = dict(cfg or {})
                                texts = cfg2.get('texts') if isinstance(cfg2.get('texts'), list) else []
                                changed = False

                                def _sync_item(field_name: str, patch: dict):
                                    nonlocal changed
                                    for it in texts:
                                        if not isinstance(it, dict):
                                            continue
                                        if str(it.get('field', '') or '').strip() != field_name:
                                            continue
                                        for k, v in patch.items():
                                            if it.get(k) != v:
                                                it[k] = v
                                                changed = True
                                        return

                                # Sync based on user-provided px coordinates.
                                _sync_item('category', {
                                    'font_size': 24,
                                    'width': 163,
                                    'x': 676,
                                    'x_anchor': 'left',
                                    'y': 468,
                                })
                                _sync_item('education_level', {
                                    'font_size': 24,
                                    'width': 219,
                                    'x': 874,
                                    'x_anchor': 'left',
                                    'y': 468,
                                })
                                _sync_item('award_level', {
                                    'width': 1187,
                                    'x': 37,
                                    'x_anchor': 'left',
                                    'y': 560,
                                })
                                # NOTE: reportlab drawString y is baseline; nudge down slightly.
                                _sync_item('participants_names', {
                                    'font_size': 28,
                                    'width': 1187,
                                    'x': 37,
                                    'x_anchor': 'left',
                                    'y': 420,
                                })

                                if changed:
                                    cfg2['texts'] = texts
                                    t.set_config(cfg2)
                                    dirty = True
                            except Exception:
                                pass
                except Exception:
                    pass

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
