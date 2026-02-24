from flask import Blueprint, request, jsonify, send_file, current_app
import pandas as pd
import io
import base64
from datetime import datetime
import hashlib
import zipfile
import json
import os
import smtplib
from email.message import EmailMessage

from admin_auth import require_admin

admin_bp = Blueprint('admin', __name__)


def _stamp_slot_path(*, cert_kind: str, slot_index: int) -> str:
    cert_kind = str(cert_kind or '').strip().lower()
    slot_index = int(slot_index or 0)
    if cert_kind not in ('player', 'coach'):
        return ''
    if slot_index < 1 or slot_index > 6:
        return ''
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, 'assets', 'cert', 'stamps', cert_kind, f'{slot_index}.png')


def _ensure_parent_dir(fp: str):
    try:
        d = os.path.dirname(fp)
        if d:
            os.makedirs(d, exist_ok=True)
    except Exception:
        pass


@admin_bp.route('/api/admin/stamps/<string:cert_kind>/<int:slot_index>', methods=['GET'])
@require_admin()
def admin_get_stamp(cert_kind: str, slot_index: int):
    fp = _stamp_slot_path(cert_kind=cert_kind, slot_index=slot_index)
    if not fp or (not os.path.exists(fp)):
        return jsonify({'success': False, 'message': '未找到盖章文件'}), 404
    return send_file(fp, mimetype='image/png')


@admin_bp.route('/api/admin/stamps/<string:cert_kind>/<int:slot_index>', methods=['POST'])
@require_admin()
def admin_upload_stamp(cert_kind: str, slot_index: int):
    fp = _stamp_slot_path(cert_kind=cert_kind, slot_index=slot_index)
    if not fp:
        return jsonify({'success': False, 'message': '参数错误'}), 400

    f = request.files.get('file')
    if not f:
        return jsonify({'success': False, 'message': '缺少上传文件 file'}), 400

    try:
        _ensure_parent_dir(fp)
        if os.path.exists(fp):
            try:
                os.remove(fp)
            except Exception:
                pass
        f.save(fp)
        return jsonify({'success': True, 'message': '上传成功', 'path': f'assets/cert/stamps/{str(cert_kind).strip().lower()}/{slot_index}.png'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


_WX_ACCESS_TOKEN_CACHE = {
    'token': '',
    'expires_at_ts': 0
}


def _now_ts() -> int:
    try:
        return int(datetime.utcnow().timestamp())
    except Exception:
        return 0


def _wx_get_access_token():
    try:
        import json as _json
        import urllib.parse
        import urllib.request

        cur = str(_WX_ACCESS_TOKEN_CACHE.get('token', '') or '').strip()
        exp = int(_WX_ACCESS_TOKEN_CACHE.get('expires_at_ts', 0) or 0)
        if cur and exp and _now_ts() < exp:
            return {'success': True, 'token': cur, 'raw': None}

        appid = str(os.environ.get('WX_APPID', '') or '').strip()
        secret = str(os.environ.get('WX_SECRET', '') or '').strip()
        if not appid or not secret:
            return {'success': False, 'message': '服务器未配置 WX_APPID/WX_SECRET', 'raw': None}

        params = {
            'grant_type': 'client_credential',
            'appid': appid,
            'secret': secret
        }
        url = 'https://api.weixin.qq.com/cgi-bin/token?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        payload = _json.loads(raw or '{}')

        token = str(payload.get('access_token', '') or '').strip()
        expires_in = int(payload.get('expires_in', 0) or 0)
        if not token:
            errcode = payload.get('errcode')
            errmsg = payload.get('errmsg')
            msg = '获取微信 access_token 失败'
            if errcode is not None or errmsg:
                msg = f'获取微信 access_token 失败: {errcode} {errmsg}'.strip()
            return {'success': False, 'message': msg, 'raw': payload}

        # 提前 120 秒过期，避免临界失败
        _WX_ACCESS_TOKEN_CACHE['token'] = token
        _WX_ACCESS_TOKEN_CACHE['expires_at_ts'] = _now_ts() + max(0, expires_in - 120)
        return {'success': True, 'token': token, 'raw': payload}

    except Exception as e:
        return {'success': False, 'message': str(e), 'raw': None}


def _wx_send_audit_subscribe(openid: str, event_name: str, status_text: str, reviewed_at_dt, reason_text: str, page_path: str):
    try:
        import json as _json
        import urllib.request

        to_user = str(openid or '').strip()
        if not to_user:
            try:
                current_app.logger.info('wx_subscribe_send skipped: missing_openid')
            except Exception:
                pass
            return {'enabled': False, 'success': False, 'error': 'missing_openid'}

        template_id = str(os.environ.get('WX_SUBSCRIBE_AUDIT_TEMPLATE_ID', '') or '').strip()
        if not template_id:
            template_id = 'a1s7ioFW5JEliylSx1hGJSd35x01NrKTFadK54XnuHY'

        tok = _wx_get_access_token()
        if not tok.get('success'):
            try:
                current_app.logger.info('wx_subscribe_send failed: get_access_token_failed=%s', tok.get('message'))
            except Exception:
                pass
            return {'enabled': True, 'success': False, 'error': tok.get('message'), 'raw': tok.get('raw')}

        access_token = tok.get('token')

        reviewed_at_str = ''
        try:
            if reviewed_at_dt:
                reviewed_at_str = reviewed_at_dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            reviewed_at_str = ''
        if not reviewed_at_str:
            reviewed_at_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        event_val = str(event_name or '').strip() or '赛事报名'
        status_val = str(status_text or '').strip() or '已更新'
        reason_val = str(reason_text or '').strip() or '-'

        data = {
            # Note: keyword IDs must match the selected subscribe message template.
            # Current template keywords: 赛事名称、报名情况
            'thing4': {'value': event_val},
            'thing1': {'value': status_val},
            'time11': {'value': reviewed_at_str},
            'thing29': {'value': reason_val}
        }

        body = {
            'touser': to_user,
            'template_id': template_id,
            'page': str(page_path or '').strip() or 'pages/application-query/application-query',
            'data': data
        }

        url = f'https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}'
        req = urllib.request.Request(
            url,
            data=_json.dumps(body, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        payload = _json.loads(raw or '{}')
        errcode = payload.get('errcode')
        errmsg = payload.get('errmsg')
        ok = (errcode == 0) or (str(errcode) == '0')
        try:
            tail = to_user[-6:] if len(to_user) >= 6 else to_user
            current_app.logger.info(
                'wx_subscribe_send result: ok=%s openid_tail=%s errcode=%s errmsg=%s',
                bool(ok),
                tail,
                errcode,
                str(errmsg or '')
            )
        except Exception:
            pass
        return {
            'enabled': True,
            'success': bool(ok),
            'error': None if ok else f'{errcode} {errmsg}'.strip(),
            'raw': payload
        }
    except Exception as e:
        try:
            current_app.logger.info('wx_subscribe_send exception: %s', str(e))
        except Exception:
            pass
        return {'enabled': True, 'success': False, 'error': str(e)}


def _send_reject_notification_mail(application, reason: str):
    mode = str(os.environ.get('REJECT_NOTIFY_MODE', '') or '').strip().lower()
    if mode not in ['mail', 'email', 'smtp']:
        return {'enabled': False, 'success': False, 'error': None}

    host = str(os.environ.get('SMTP_HOST', '') or '').strip()
    port = int(str(os.environ.get('SMTP_PORT', '') or '587').strip() or 587)
    user = str(os.environ.get('SMTP_USER', '') or '').strip()
    password = str(os.environ.get('SMTP_PASSWORD', '') or '').strip()
    use_tls = str(os.environ.get('SMTP_TLS', '1') or '1').strip().lower() in ['1', 'true', 'yes', 'on']
    use_ssl = str(os.environ.get('SMTP_SSL', '') or '').strip().lower() in ['1', 'true', 'yes', 'on']
    timeout_s = int(str(os.environ.get('SMTP_TIMEOUT', '') or '10').strip() or 10)
    mail_from = str(os.environ.get('MAIL_FROM', '') or '').strip() or user

    to_addr = ''
    try:
        to_addr = str(getattr(application, 'contact_email', '') or '').strip()
    except Exception:
        to_addr = ''

    if (not host) or (not user) or (not password) or (not mail_from) or (not to_addr) or ('@' not in to_addr):
        return {'enabled': True, 'success': False, 'error': 'SMTP/收件人配置不完整或收件邮箱无效'}

    subject = str(os.environ.get('REJECT_NOTIFY_SUBJECT', '') or '').strip() or '报名审核结果：已退回'
    app_id = getattr(application, 'id', None)
    category = getattr(application, 'category', '') or ''
    task = getattr(application, 'task', '') or ''
    education_level = getattr(application, 'education_level', '') or ''
    school_name = getattr(application, 'school_name', '') or ''
    match_no = getattr(application, 'match_no', '') or ''
    contact_name = getattr(application, 'contact_name', '') or ''

    title = "-".join([x for x in [category, task, education_level] if x])

    tpl = str(os.environ.get('REJECT_NOTIFY_BODY', '') or '').strip()
    if tpl:
        try:
            tpl = tpl.replace('\\n', '\n')
            body = tpl.format_map({
                'username': contact_name or '',
                'title': title,
                'reason': reason
            })
        except Exception:
            body = ''
    else:
        body = ''

    if not body:
        lines = [
            f"您好，{contact_name}：" if contact_name else '您好：',
            '',
            '您的报名已被管理员退回，请根据退回原因修改后重新提交。',
            '',
            f"退回原因：{reason}",
            '',
            f"报名ID：{app_id}",
            f"参赛号：{match_no}" if match_no else None,
            f"赛别/项目：{category}",
            f"具体任务：{task}",
            f"组别/学段：{education_level}",
            f"学校：{school_name}" if school_name else None,
            '',
            '（此邮件由系统自动发送，请勿直接回复）'
        ]
        body = "\n".join([x for x in lines if x is not None])

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = mail_from
    msg['To'] = to_addr
    msg.set_content(body)

    try:
        if use_ssl or port == 465:
            with smtplib.SMTP_SSL(host, port, timeout=timeout_s) as smtp:
                smtp.login(user, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout_s) as smtp:
                if use_tls:
                    smtp.starttls()
                smtp.login(user, password)
                smtp.send_message(msg)
        return {'enabled': True, 'success': True, 'error': None}
    except Exception as e:
        return {'enabled': True, 'success': False, 'error': str(e)}


@admin_bp.route('/api/admin/login', methods=['POST'])
def admin_login():
    """管理员登录：账号密码 -> token"""
    try:
        from admin_auth import create_admin_token, verify_admin_credentials

        data = request.get_json() or {}
        username = str(data.get('username', '') or '').strip()
        password = str(data.get('password', '') or '').strip()

        if not username or not password:
            return jsonify({
                'success': False,
                'message': '缺少账号或密码'
            }), 400

        if not verify_admin_credentials(username, password):
            return jsonify({
                'success': False,
                'message': '账号或密码错误'
            }), 401

        token = create_admin_token({
            'role': 'admin',
            'username': username
        })

        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': token,
                'token_type': 'Bearer'
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'登录失败: {str(e)}'
        }), 500


@admin_bp.route('/api/admin/import-excellent-coaches', methods=['POST'])
@require_admin()
def import_excellent_coaches():
    """优秀辅导员导入接口（姓名 + 电话）"""
    try:
        from models import ExcellentCoach, ImportLog
        from app import db
        import hashlib

        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '请上传Excel文件'
            }), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '请选择文件'
            }), 400

        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'message': '仅支持Excel文件格式'
            }), 400

        try:
            df = pd.read_excel(file)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Excel文件读取失败: {str(e)}'
            }), 400

        def _pick_col(candidates):
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        name_col = _pick_col(['指导老师姓名', '指导老师', '老师姓名', '姓名', 'teacher_name'])
        phone_col = _pick_col(['指导老师电话', '指导老师手机号', '老师电话', '电话', '手机号', 'teacher_phone'])

        if not name_col or not phone_col:
            return jsonify({
                'success': False,
                'message': 'Excel文件缺少必要的列: 指导老师姓名 / 指导老师电话'
            }), 400

        total_count = len(df)
        success_count = 0
        failed_count = 0
        error_data = []

        # Excel 内部：电话唯一（同一老师电话不应重复）
        seen_phone_hash = set()

        for index, row in df.iterrows():
            try:
                teacher_name = str(row.get(name_col, '') or '').strip()
                teacher_phone = str(row.get(phone_col, '') or '').strip()

                if _is_blank_text(teacher_name) or _is_blank_text(teacher_phone):
                    error_data.append({
                        '行号': index + 2,
                        '指导老师姓名': teacher_name,
                        '指导老师电话': teacher_phone,
                        '错误原因': '姓名或电话为空'
                    })
                    failed_count += 1
                    continue

                phone_hash = hashlib.sha256(teacher_phone.encode()).hexdigest()
                if phone_hash in seen_phone_hash:
                    error_data.append({
                        '行号': index + 2,
                        '指导老师姓名': teacher_name,
                        '指导老师电话': teacher_phone,
                        '错误原因': '该电话在本次导入文件中重复'
                    })
                    failed_count += 1
                    continue
                seen_phone_hash.add(phone_hash)

                existing = ExcellentCoach.query.filter(ExcellentCoach.teacher_phone_hash == phone_hash).first()
                if existing:
                    existing.teacher_name = teacher_name
                    existing.teacher_phone = teacher_phone
                else:
                    coach = ExcellentCoach(
                        teacher_name=teacher_name
                    )
                    coach.teacher_phone = teacher_phone
                    db.session.add(coach)

                success_count += 1

            except Exception as e:
                error_data.append({
                    '行号': index + 2,
                    '指导老师姓名': row.get(name_col, ''),
                    '指导老师电话': row.get(phone_col, ''),
                    '错误原因': f'处理异常: {str(e)}'
                })
                failed_count += 1

        db.session.commit()

        error_log_content = None
        if error_data:
            error_log_content = create_error_excel(error_data)

        import_log = ImportLog(
            import_type='excellent_coach',
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            error_log_content=error_log_content
        )
        db.session.add(import_log)
        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'导入完成，成功 {success_count} 条，失败 {failed_count} 条',
            'data': {
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'error_log_available': error_log_content is not None,
                'import_log_id': import_log.id
            }
        })

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500

@admin_bp.route('/api/admin/stats/applications', methods=['GET'])
@require_admin()
def admin_stats_applications():
    try:
        from models import Application
        from app import db
        from sqlalchemy import func

        dimension = str(request.args.get('dimension', '') or '').strip().lower() or 'school'
        status = str(request.args.get('status', '') or '').strip()
        category = str(request.args.get('category', '') or '').strip()
        top_n = request.args.get('top_n', 20, type=int)

        if dimension not in ['school', 'education_level']:
            return jsonify({'success': False, 'message': 'dimension 仅支持 school 或 education_level'}), 400

        if dimension == 'school':
            dim_col = Application.school_name
        else:
            dim_col = Application.education_level

        q = db.session.query(dim_col.label('label'), func.count(Application.id).label('count'))
        if status:
            q = q.filter(Application.status == status)
        if category:
            q = q.filter(Application.category == category)

        q = q.group_by(dim_col).order_by(func.count(Application.id).desc())
        if top_n and top_n > 0:
            q = q.limit(top_n)

        rows = q.all()
        items = []
        for r in rows:
            label = r.label if r.label is not None and str(r.label).strip() != '' else '未填写'
            items.append({'label': str(label), 'count': int(r.count)})

        return jsonify({'success': True, 'data': {'dimension': dimension, 'items': items}})

    except Exception as e:
        return jsonify({'success': False, 'message': f'统计失败: {str(e)}'}), 500

@admin_bp.route('/api/admin/me', methods=['GET'])
@require_admin()
def admin_me():
    """用于测试 token 有效性"""
    try:
        payload = getattr(request, 'admin_payload', {}) or {}
        return jsonify({
            'success': True,
            'data': payload
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'获取信息失败: {str(e)}'
        }), 500


@admin_bp.route('/api/admin/application/by-match-no', methods=['GET'])
@require_admin()
def admin_get_application_by_match_no():
    """管理员按参赛号查询报名/获奖信息（用于管理端/调试）"""
    try:
        from models import Application

        match_no = str(request.args.get('match_no', '') or '').strip()
        if not match_no:
            return jsonify({'success': False, 'message': '请提供参赛号'}), 400

        application = Application.query.filter(Application.match_no == match_no).first()
        if not application:
            return jsonify({'success': False, 'message': '未找到该参赛号对应的记录'}), 404

        return jsonify({'success': True, 'data': application.to_dict(include_sensitive=True)})

    except Exception as e:
        return jsonify({'success': False, 'message': '获取数据失败', 'error': str(e)}), 500


@admin_bp.route('/api/admin/applications', methods=['GET'])
@require_admin()
def admin_list_applications():
    """报名列表（管理员）：分页 + 筛选"""
    try:
        from models import Application

        def _school_initial(name: str) -> str:
            try:
                from pypinyin import lazy_pinyin, Style
                s = str(name or '').strip()
                if not s:
                    return ''
                letters = lazy_pinyin(s, style=Style.FIRST_LETTER)
                return ''.join([str(x or '') for x in letters]).upper()
            except Exception:
                return ''

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        status = str(request.args.get('status', '') or '').strip()
        category = str(request.args.get('category', '') or '').strip()
        education_level = str(request.args.get('education_level', '') or '').strip()
        school_name = str(request.args.get('school_name', '') or '').strip()
        school_initial = str(request.args.get('school_initial', '') or '').strip().upper()
        match_no = str(request.args.get('match_no', '') or '').strip()

        query = Application.query

        if status:
            query = query.filter(Application.status == status)
        if category:
            query = query.filter(Application.category == category)
        if education_level:
            query = query.filter(Application.education_level == education_level)
        if school_name:
            query = query.filter(Application.school_name.like(f"%{school_name}%"))
        if match_no:
            query = query.filter(Application.match_no == match_no)

        if school_initial:
            ids = []
            for row in query.with_entities(Application.id, Application.school_name).yield_per(500):
                if _school_initial(row.school_name).startswith(school_initial):
                    ids.append(row.id)
            if not ids:
                return jsonify({
                    'success': True,
                    'data': {
                        'applications': [],
                        'total': 0,
                        'pages': 0,
                        'current_page': page
                    }
                })
            query = query.filter(Application.id.in_(ids))

        applications = query.order_by(Application.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        return jsonify({
            'success': True,
            'data': {
                'applications': [a.to_dict(include_sensitive=True) for a in applications.items],
                'total': applications.total,
                'pages': applications.pages,
                'current_page': page
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': '获取报名列表失败', 'error': str(e)}), 500


@admin_bp.route('/api/admin/applications/<int:application_id>', methods=['GET'])
@require_admin()
def admin_get_application_detail(application_id):
    """报名详情（管理员）"""
    try:
        from models import Application

        application = Application.query.get(application_id)
        if not application:
            return jsonify({'success': False, 'message': '未找到申请记录'}), 404

        return jsonify({'success': True, 'data': application.to_dict(include_sensitive=True)})

    except Exception as e:
        return jsonify({'success': False, 'message': '获取报名详情失败', 'error': str(e)}), 500


@admin_bp.route('/api/admin/applications/<int:application_id>/approve', methods=['POST'])
@require_admin()
def admin_approve_application(application_id):
    """审核通过（管理员）"""
    try:
        from app import db
        from models import Application

        application = Application.query.get(application_id)
        if not application:
            return jsonify({'success': False, 'message': '未找到申请记录'}), 404

        payload = getattr(request, 'admin_payload', {}) or {}
        reviewer = str(payload.get('username', '') or '').strip() or None

        application.status = 'approved'
        application.rejected_reason = None
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = reviewer

        db.session.commit()

        event_name = '-'.join([
            str(getattr(application, 'category', '') or '').strip(),
            str(getattr(application, 'task', '') or '').strip(),
        ]).strip('-')

        subscribe = _wx_send_audit_subscribe(
            getattr(application, 'openid', None),
            event_name,
            '审核通过',
            getattr(application, 'reviewed_at', None),
            '报名成功',
            'pages/application-query/application-query'
        )

        data = application.to_dict(include_sensitive=True)
        data['subscribe'] = subscribe
        return jsonify({'success': True, 'message': '审核通过', 'data': data})

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({'success': False, 'message': f'审核通过失败: {str(e)}'}), 500


@admin_bp.route('/api/admin/applications/<int:application_id>/reject', methods=['POST'])
@require_admin()
def admin_reject_application(application_id):
    """审核退回（管理员）"""
    try:
        from app import db
        from models import Application

        data = request.get_json() or {}
        reason = str(data.get('reason', '') or '').strip()
        if not reason:
            return jsonify({'success': False, 'message': '请提供退回原因'}), 400

        application = Application.query.get(application_id)
        if not application:
            return jsonify({'success': False, 'message': '未找到申请记录'}), 404

        payload = getattr(request, 'admin_payload', {}) or {}
        reviewer = str(payload.get('username', '') or '').strip() or None

        application.status = 'rejected'
        application.rejected_reason = reason
        application.reviewed_at = datetime.utcnow()
        application.reviewed_by = reviewer

        db.session.commit()

        notify = _send_reject_notification_mail(application, reason)
        event_name = '-'.join([
            str(getattr(application, 'category', '') or '').strip(),
            str(getattr(application, 'task', '') or '').strip(),
        ]).strip('-')

        subscribe = _wx_send_audit_subscribe(
            getattr(application, 'openid', None),
            event_name,
            '审核未通过',
            getattr(application, 'reviewed_at', None),
            reason,
            'pages/application-query/application-query'
        )
        data = application.to_dict(include_sensitive=True)
        data['notify'] = notify
        data['subscribe'] = subscribe
        return jsonify({'success': True, 'message': '已退回', 'data': data})

    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({'success': False, 'message': f'退回失败: {str(e)}'}), 500


@admin_bp.route('/api/admin/applications/export', methods=['GET'])
@require_admin()
def admin_export_applications():
    """导出报名列表（管理员）：按筛选导出 Excel"""
    try:
        from models import Application

        def _school_initial(name: str) -> str:
            try:
                from pypinyin import lazy_pinyin, Style
                s = str(name or '').strip()
                if not s:
                    return ''
                letters = lazy_pinyin(s, style=Style.FIRST_LETTER)
                return ''.join([str(x or '') for x in letters]).upper()
            except Exception:
                return ''

        status = str(request.args.get('status', '') or '').strip()
        category = str(request.args.get('category', '') or '').strip()
        education_level = str(request.args.get('education_level', '') or '').strip()
        school_name = str(request.args.get('school_name', '') or '').strip()
        school_initial = str(request.args.get('school_initial', '') or '').strip().upper()
        match_no = str(request.args.get('match_no', '') or '').strip()

        query = Application.query
        if status:
            query = query.filter(Application.status == status)
        if category:
            query = query.filter(Application.category == category)
        if education_level:
            query = query.filter(Application.education_level == education_level)
        if school_name:
            query = query.filter(Application.school_name.like(f"%{school_name}%"))
        if match_no:
            query = query.filter(Application.match_no == match_no)

        if school_initial:
            ids = []
            for row in query.with_entities(Application.id, Application.school_name).yield_per(500):
                if _school_initial(row.school_name).startswith(school_initial):
                    ids.append(row.id)
            if not ids:
                export_df = pd.DataFrame([])
                excel_file = io.BytesIO()
                export_df.to_excel(excel_file, index=False)
                excel_file.seek(0)
                return send_file(
                    excel_file,
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name='applications.xlsx'
                )
            query = query.filter(Application.id.in_(ids))

        items = query.order_by(Application.created_at.desc()).all()

        rows = []
        for a in items:
            d = a.to_dict(include_sensitive=True)
            match_no_val = d.get('match_no')
            if _is_blank_text(match_no_val):
                match_no_val = ''
            rows.append({
                '报名ID': d.get('id'),
                '参赛号': match_no_val,
                '项目大类': d.get('category'),
                '具体任务': d.get('task'),
                '学段': d.get('education_level'),
                '人数': d.get('participant_count'),
                '学校名称': d.get('school_name'),
                '指导老师': d.get('teacher_name'),
                '指导老师手机号': d.get('teacher_phone'),
                '领队': d.get('leader_name'),
                '参赛人手机号': d.get('participant_phone'),
                '参赛人邮箱': d.get('participant_email'),
                '联系人姓名': d.get('contact_name'),
                '联系人手机号': d.get('contact_phone'),
                '联系人邮箱': d.get('contact_email'),
                '获奖等级': d.get('award_level'),
                '状态': d.get('status'),
                '退回原因': d.get('rejected_reason'),
                '创建时间': d.get('created_at'),
                '更新时间': d.get('updated_at')
            })

        df = pd.DataFrame(rows)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='报名列表', index=False)
        output.seek(0)

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"报名列表导出_{ts}.xlsx"
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500


@admin_bp.route('/api/admin/applications/by-phone', methods=['GET'])
@require_admin()
def admin_get_applications_by_phone():
    """管理员按手机号查询报名记录（用于 Apifox 调试，避免学生端接口 require_user 限制）"""
    try:
        from models import Application

        phone = str(request.args.get('phone', '') or '').strip()
        if not phone:
            return jsonify({'success': False, 'message': '请提供手机号'}), 400

        phone_hash = hashlib.sha256(phone.encode()).hexdigest()
        applications = Application.query.filter(
            Application.contact_phone_hash == phone_hash
        ).order_by(Application.created_at.desc()).all()

        return jsonify({'success': True, 'data': [a.to_dict(include_sensitive=True) for a in applications]})

    except Exception as e:
        return jsonify({'success': False, 'message': '获取数据失败', 'error': str(e)}), 500

def create_error_excel(error_data):
    """创建包含错误信息的Excel文件"""
    df = pd.DataFrame(error_data)
    
    # 创建Excel文件
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='导入错误记录', index=False)
    
    output.seek(0)
    return base64.b64encode(output.getvalue()).decode('utf-8')


def _safe_filename_part(val: str) -> str:
    s = str(val or '').strip()
    if not s:
        return 'NA'
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']:
        s = s.replace(ch, '_')
    return s

def _cell_to_str(value):
    try:
        if pd.isna(value):
            return ''
    except Exception:
        pass
    return str(value).strip() if value is not None else ''

def _is_blank_text(s):
    txt = str(s or '').strip()
    if not txt:
        return True
    low = txt.lower()
    return low in ['nan', 'none', 'null', 'undefined']


def _make_template_excel(columns: list[str], sample_rows: list[dict] | None = None, sheet_name: str = '模板'):
    df = pd.DataFrame(sample_rows or [], columns=columns)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
    output.seek(0)
    return output


@admin_bp.route('/api/admin/download-template/match-no', methods=['GET'])
@require_admin()
def admin_download_template_match_no():
    output = _make_template_excel(
        ['参赛号', '手机号'],
        sample_rows=[{'参赛号': 'A001', '手机号': '13800138000'}],
        sheet_name='参赛号导入模板'
    )
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='参赛号导入模板.xlsx'
    )


@admin_bp.route('/api/admin/download-template/awards', methods=['GET'])
@require_admin()
def admin_download_template_awards():
    output = _make_template_excel(
        ['参赛号', '获奖等级'],
        sample_rows=[{'参赛号': 'A001', '获奖等级': '一等奖'}],
        sheet_name='获奖导入模板'
    )
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='获奖导入模板.xlsx'
    )


@admin_bp.route('/api/admin/download-template/excellent-coaches', methods=['GET'])
@require_admin()
def admin_download_template_excellent_coaches():
    output = _make_template_excel(
        ['指导老师姓名', '指导老师电话'],
        sample_rows=[{'指导老师姓名': '张三', '指导老师电话': '13800138000'}],
        sheet_name='优秀辅导员导入模板'
    )
    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='优秀辅导员导入模板.xlsx'
    )

@admin_bp.route('/api/admin/import-match-no', methods=['POST'])
@require_admin()
def import_match_no():
    """参赛号导入接口"""
    try:
        from models import Application, ImportLog
        from app import db
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '请上传Excel文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '请选择文件'
            }), 400
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'message': '仅支持Excel文件格式'
            }), 400
        
        # 读取Excel文件
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Excel文件读取失败: {str(e)}'
            }), 400
        
        # 列名兼容（按需求模板/常见表头）
        def _pick_col(candidates):
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        match_no_col = _pick_col(['参赛号', '参赛编号', '参赛ID', 'match_no'])
        if not match_no_col:
            return jsonify({
                'success': False,
                'message': 'Excel文件缺少必要的列: 参赛号'
            }), 400

        phone_col = _pick_col(['手机号', '选手手机号', '参赛人手机号', '参赛手机号', '电话', '手机'])
        if not phone_col:
            return jsonify({
                'success': False,
                'message': 'Excel文件缺少必要的列: 手机号'
            }), 400
        
        total_count = len(df)
        success_count = 0
        failed_count = 0
        error_data = []
        updated_application_ids = []

        # 同一批次导入：参赛号唯一性（Excel 内部不能重复）
        seen_match_no = set()
        
        # 逐行处理
        for index, row in df.iterrows():
            try:
                match_no = _cell_to_str(row.get(match_no_col, ''))
                phone = _cell_to_str(row.get(phone_col, ''))

                if _is_blank_text(match_no):
                    error_data.append({
                        '行号': index + 2,  # Excel行号从2开始
                        '手机号': phone,
                        '参赛号': match_no,
                        '错误原因': '参赛号为空'
                    })
                    failed_count += 1
                    continue

                # Excel 内部重复参赛号
                if match_no in seen_match_no:
                    error_data.append({
                        '行号': index + 2,
                        '手机号': phone,
                        '参赛号': match_no,
                        '错误原因': '参赛号在本次导入文件中重复'
                    })
                    failed_count += 1
                    continue

                seen_match_no.add(match_no)

                if _is_blank_text(phone):
                    error_data.append({
                        '行号': index + 2,
                        '手机号': phone,
                        '参赛号': match_no,
                        '错误原因': '手机号为空'
                    })
                    failed_count += 1
                    continue

                phone_hash = hashlib.sha256(phone.encode()).hexdigest()
                application = Application.query.filter(
                    Application.contact_phone_hash == phone_hash
                ).order_by(Application.created_at.desc()).first()

                if application is None:
                    error_data.append({
                        '行号': index + 2,
                        '手机号': phone,
                        '参赛号': match_no,
                        '错误原因': '未找到匹配的报名记录'
                    })
                    failed_count += 1
                    continue

                if getattr(application, 'status', None) == 'rejected':
                    error_data.append({
                        '行号': index + 2,
                        '手机号': phone,
                        '参赛号': match_no,
                        '错误原因': '该报名已退回(rejected)，不分配参赛号'
                    })
                    failed_count += 1
                    continue

                # 数据库唯一性：同一个参赛号不能分配给不同报名
                existing = Application.query.filter(Application.match_no == match_no).first()
                if existing and getattr(existing, 'id', None) != getattr(application, 'id', None):
                    error_data.append({
                        '行号': index + 2,
                        '手机号': phone,
                        '参赛号': match_no,
                        '错误原因': f'参赛号已被其他报名占用(报名ID={existing.id})'
                    })
                    failed_count += 1
                    continue

                # 更新参赛号
                application.match_no = match_no
                success_count += 1
                
            except Exception as e:
                error_data.append({
                    '行号': index + 2,
                    '手机号': row.get(phone_col, '') if phone_col else row.get('手机号', ''),
                    '参赛号': row.get(match_no_col, ''),
                    '错误原因': f'处理异常: {str(e)}'
                })
                failed_count += 1
        
        # 提交事务
        db.session.commit()
        
        # 创建导入日志
        error_log_content = None
        if error_data:
            error_log_content = create_error_excel(error_data)
        
        import_log = ImportLog(
            import_type='match_no',
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            error_log_content=error_log_content
        )
        db.session.add(import_log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'导入完成，成功 {success_count} 条，失败 {failed_count} 条',
            'data': {
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'error_log_available': error_log_content is not None,
                'import_log_id': import_log.id
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500

@admin_bp.route('/api/admin/import-awards', methods=['POST'])
@require_admin()
def import_awards():
    """获奖信息导入接口"""
    try:
        from models import Application, ImportLog
        from app import db
        from config import AWARD_LEVELS
        import os
        
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'message': '请上传Excel文件'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'message': '请选择文件'
            }), 400
        
        if not file.filename.endswith(('.xlsx', '.xls')):
            return jsonify({
                'success': False,
                'message': '仅支持Excel文件格式'
            }), 400
        
        # 读取Excel文件
        try:
            df = pd.read_excel(file)
        except Exception as e:
            return jsonify({
                'success': False,
                'message': f'Excel文件读取失败: {str(e)}'
            }), 400
        
        # 检查必要的列
        required_columns = ['参赛号', '获奖等级']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({
                'success': False,
                'message': f'Excel文件缺少必要的列: {", ".join(missing_columns)}'
            }), 400
        
        total_count = len(df)
        success_count = 0
        failed_count = 0
        error_data = []
        updated_application_ids = []
        
        # 逐行处理
        for index, row in df.iterrows():
            try:
                match_no = _cell_to_str(row['参赛号'])
                award_level = _cell_to_str(row['获奖等级'])

                if _is_blank_text(match_no) or _is_blank_text(award_level):
                    error_data.append({
                        '行号': index + 2,
                        '参赛号': match_no,
                        '获奖等级': award_level,
                        '错误原因': '参赛号或获奖等级为空'
                    })
                    failed_count += 1
                    continue

                if AWARD_LEVELS and award_level not in AWARD_LEVELS:
                    error_data.append({
                        '行号': index + 2,
                        '参赛号': match_no,
                        '获奖等级': award_level,
                        '错误原因': f'获奖等级不合法（允许：{",".join(AWARD_LEVELS)}）'
                    })
                    failed_count += 1
                    continue
                
                # 优先使用参赛号匹配
                application = Application.query.filter(
                    Application.match_no == match_no
                ).first()
                
                if not application:
                    error_data.append({
                        '行号': index + 2,
                        '参赛号': match_no,
                        '获奖等级': award_level,
                        '错误原因': '未找到匹配的参赛号'
                    })
                    failed_count += 1
                    continue
                
                # 更新获奖信息
                application.award_level = award_level
                success_count += 1
                updated_application_ids.append(application.id)
                
            except Exception as e:
                error_data.append({
                    '行号': index + 2,
                    '参赛号': row.get('参赛号', ''),
                    '获奖等级': row.get('获奖等级', ''),
                    '错误原因': f'处理异常: {str(e)}'
                })
                failed_count += 1
        
        # 提交事务
        db.session.commit()
        
        # 创建导入日志
        error_log_content = None
        if error_data:
            error_log_content = create_error_excel(error_data)
        
        import_log = ImportLog(
            import_type='award',
            total_count=total_count,
            success_count=success_count,
            failed_count=failed_count,
            error_log_content=error_log_content
        )
        db.session.add(import_log)
        db.session.commit()

        auto_generate = str(request.args.get('auto_generate', '') or '').strip() in ['1', 'true', 'True', 'yes', 'on']
        if auto_generate and updated_application_ids:
            try:
                from certificate_routes import _start_background_cert_task

                task_id = _start_background_cert_task(
                    application_ids=updated_application_ids,
                    source=f'award-import:{import_log.id}'
                )

                return jsonify({
                    'success': True,
                    'message': f'导入完成，成功 {success_count} 条，失败 {failed_count} 条；证书已开始后台生成',
                    'data': {
                        'total_count': total_count,
                        'success_count': success_count,
                        'failed_count': failed_count,
                        'error_log_available': error_log_content is not None,
                        'import_log_id': import_log.id,
                        'task_id': task_id
                    }
                })

            except Exception as e:
                return jsonify({
                    'success': False,
                    'message': f'导入成功，但证书批量生成失败: {str(e)}',
                    'data': {
                        'import_log_id': import_log.id
                    }
                }), 500

        return jsonify({
            'success': True,
            'message': f'导入完成，成功 {success_count} 条，失败 {failed_count} 条',
            'data': {
                'total_count': total_count,
                'success_count': success_count,
                'failed_count': failed_count,
                'error_log_available': error_log_content is not None,
                'import_log_id': import_log.id
            }
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'导入失败: {str(e)}'
        }), 500

@admin_bp.route('/api/admin/download-error-log/<int:log_id>', methods=['GET'])
@require_admin()
def download_error_log(log_id):
    """下载错误日志Excel文件"""
    try:
        from models import ImportLog
        
        import_log = ImportLog.query.get(log_id)
        if not import_log or not import_log.error_log_content:
            return jsonify({
                'success': False,
                'message': '错误日志不存在'
            }), 404
        
        # 解码Base64内容
        excel_content = base64.b64decode(import_log.error_log_content)
        
        # 创建文件响应
        return send_file(
            io.BytesIO(excel_content),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'导入错误日志_{import_log.import_type}_{import_log.created_at.strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'下载失败: {str(e)}'
        }), 500


@admin_bp.route('/api/admin/download-awards-zip/<int:log_id>', methods=['GET'])
@require_admin()
def download_awards_zip(log_id):
    """下载获奖导入生成的证书压缩包"""
    try:
        import os
        from models import ImportLog

        import_log = ImportLog.query.get(log_id)
        if not import_log:
            return jsonify({'success': False, 'message': '导入记录不存在'}), 404
        if import_log.import_type != 'award':
            return jsonify({'success': False, 'message': '导入类型不匹配'}), 400

        folder = os.path.join(os.getcwd(), 'generated_zips')
        zip_path = os.path.join(folder, f"award_import_{import_log.id}.zip")
        if not os.path.exists(zip_path):
            return jsonify({'success': False, 'message': '压缩包不存在或已被清理，请重新生成'}), 404

        ts = import_log.created_at.strftime('%Y%m%d_%H%M%S') if import_log.created_at else datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"获奖导入_证书批量生成_{ts}.zip"
        return send_file(
            zip_path,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'}), 500

@admin_bp.route('/api/admin/import-logs', methods=['GET'])
@require_admin()
def get_import_logs():
    """获取导入日志列表"""
    try:
        from models import ImportLog
        
        logs = ImportLog.query.order_by(ImportLog.created_at.desc()).all()
        
        return jsonify({
            'success': True,
            'data': [log.to_dict() for log in logs]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取日志失败',
            'error': str(e)
        }), 500
