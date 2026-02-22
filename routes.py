from flask import Blueprint, request, jsonify
import re
from datetime import datetime

from user_auth import require_user
from admin_auth import require_admin

# 创建蓝图
api_bp = Blueprint('api', __name__)


@api_bp.route('/api/user/me', methods=['GET'])
@require_user()
def user_me():
    """返回当前 user_token 对应的身份信息（用于测试/调试）"""
    payload = getattr(request, 'user_payload', {}) or {}
    return jsonify({
        'success': True,
        'data': {
            'role': payload.get('role'),
            'openid': payload.get('openid'),
            'nickname': payload.get('nickname'),
            'avatar_url': payload.get('avatar_url')
        }
    })


@api_bp.route('/api/wx/login', methods=['POST'])
def wx_login():
    """学生端微信登录：code -> openid -> token

    需要环境变量：WX_APPID / WX_SECRET
    """
    try:
        import json as _json
        import os
        import urllib.parse
        import urllib.request

        from user_auth import create_user_token

        data = request.get_json() or {}
        code = str(data.get('code', '') or '').strip()
        if not code:
            return jsonify({
                'success': False,
                'message': '缺少 code'
            }), 400

        # 可选：前端通过 uni.getUserProfile 获取的昵称/头像
        user_info = data.get('user_info') or {}
        nickname = ''
        avatar_url = ''
        try:
            if isinstance(user_info, dict):
                nickname = str(user_info.get('nickName', '') or '').strip()
                avatar_url = str(user_info.get('avatarUrl', '') or '').strip()
        except Exception:
            nickname = ''
            avatar_url = ''

        appid = os.environ.get('WX_APPID')
        secret = os.environ.get('WX_SECRET')
        if not appid or not secret:
            return jsonify({
                'success': False,
                'message': '服务器未配置 WX_APPID/WX_SECRET'
            }), 500

        params = {
            'appid': appid,
            'secret': secret,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        url = 'https://api.weixin.qq.com/sns/jscode2session?' + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=10) as resp:
            raw = resp.read().decode('utf-8')
        payload = _json.loads(raw or '{}')

        openid = payload.get('openid')
        if not openid:
            errcode = payload.get('errcode')
            errmsg = payload.get('errmsg')
            msg = '微信登录失败'
            if errcode is not None or errmsg:
                msg = f'微信登录失败: {errcode} {errmsg}'.strip()
            try:
                if str(errcode) == '40029':
                    appid_tail = str(appid)[-6:] if appid else ''
                    msg = (
                        f"微信登录失败: {errcode} {errmsg}。"
                        f"请检查后端环境变量 WX_APPID/WX_SECRET 是否与当前小程序 AppID 一致（后端 appid 尾号:{appid_tail}）。"
                    )
            except Exception:
                pass
            return jsonify({
                'success': False,
                'message': msg,
                'data': payload
            }), 400

        token = create_user_token({
            'role': 'user',
            'openid': openid,
            'nickname': nickname,
            'avatar_url': avatar_url
        })

        return jsonify({
            'success': True,
            'message': '登录成功',
            'data': {
                'token': token,
                'token_type': 'Bearer',
                'openid': openid,
                'nickname': nickname,
                'avatar_url': avatar_url
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'登录失败: {str(e)}'
        }), 500

def validate_phone(phone):
    """验证手机号格式"""
    return re.match(r'^1[3-9]\d{9}$', phone) is not None

def validate_email(email):
    """验证邮箱格式"""
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def validate_competition_rules(category, task, education_level, participant_count):
    """验证竞赛规则"""
    from config import COMPETITION_RULES  # 添加导入
    
    errors = []
    
    # 检查项目大类是否存在
    if category not in COMPETITION_RULES:
        errors.append(f"项目大类 '{category}' 不存在")
        return errors
    # 检查具体任务是否存在
    if task not in COMPETITION_RULES[category]:
        errors.append(f"项目任务 '{task}' 在 '{category}' 中不存在")
        return errors
    
    rule = COMPETITION_RULES[category][task]
    
    # 检查学段是否符合要求
    if education_level not in rule["allowed_levels"]:
        errors.append(f"'{category}-{task}' 仅允许学段: {', '.join(rule['allowed_levels'])}")
    
    # 检查人数是否符合要求
    if participant_count != rule["participant_count"]:
        errors.append(f"'{category}-{task}' 要求 {rule['participant_count']} 人，当前提交 {participant_count} 人")
    
    return errors


@api_bp.route('/api/excellent-coaches/query', methods=['GET'])
@require_user()
def query_excellent_coach():
    """优秀辅导员查询：按指导老师姓名 + 电话匹配，并返回可生成证书的信息"""
    try:
        import hashlib
        from models import ExcellentCoach, Application
        from app import db

        teacher_name = str(request.args.get('teacher_name', '') or '').strip()
        teacher_phone = str(request.args.get('teacher_phone', '') or '').strip()
        if not teacher_name or not teacher_phone:
            return jsonify({'success': False, 'message': '请填写指导老师姓名与电话'}), 400

        phone_hash = hashlib.sha256(teacher_phone.encode()).hexdigest()
        coach = ExcellentCoach.query.filter(
            ExcellentCoach.teacher_phone_hash == phone_hash,
            ExcellentCoach.teacher_name == teacher_name
        ).first()
        if not coach:
            return jsonify({'success': False, 'message': '未查询到证书'}), 404

        app = Application.query.filter(
            Application.teacher_phone_hash == phone_hash,
            Application.teacher_name == teacher_name,
            Application.award_level.isnot(None)
        ).order_by(Application.created_at.desc()).first()

        # 兼容历史数据：teacher_phone_hash 为空时，按 teacher_name 候选 + 解密手机号比对，并回填 hash
        if not app:
            candidates = Application.query.filter(
                Application.teacher_name == teacher_name,
                Application.award_level.isnot(None)
            ).order_by(Application.created_at.desc()).limit(50).all()
            for c in candidates:
                try:
                    if str(getattr(c, 'teacher_phone', '') or '').strip() == teacher_phone:
                        try:
                            if not getattr(c, 'teacher_phone_hash', None):
                                c.teacher_phone_hash = phone_hash
                                db.session.commit()
                        except Exception:
                            db.session.rollback()
                        app = c
                        break
                except Exception:
                    continue

        if not app:
            return jsonify({'success': False, 'message': '已找到优秀辅导员记录，但暂无获奖数据，无法生成证书'}), 404

        return jsonify({
            'success': True,
            'data': {
                'coach': {
                    **coach.to_dict(include_sensitive=False),
                    'coach_id': coach.id
                },
                'application': app.to_dict(include_sensitive=False)
            }
        })

    except Exception as e:
        return jsonify({'success': False, 'message': '查询失败', 'error': str(e)}), 500


@api_bp.route('/api/my-applications/<int:application_id>', methods=['GET'])
@require_user()
def get_my_application_detail(application_id):
    try:
        from app import app
        from models import Application

        with app.app_context():
            payload = getattr(request, 'user_payload', {}) or {}
            openid = str(payload.get('openid', '') or '').strip()

            application = Application.query.filter(
                Application.id == application_id,
                Application.openid == openid
            ).first()
            if not application:
                return jsonify({'success': False, 'message': '未找到报名记录'}), 404

            return jsonify({'success': True, 'data': application.to_dict(include_sensitive=True)})
    except Exception as e:
        return jsonify({'success': False, 'message': '获取数据失败', 'error': str(e)}), 500


@api_bp.route('/api/my-applications/<int:application_id>', methods=['PUT'])
@require_user()
def update_my_application(application_id):
    try:
        from app import app, db
        import hashlib
        from models import Application, ApplicationParticipant

        with app.app_context():
            payload = getattr(request, 'user_payload', {}) or {}
            openid = str(payload.get('openid', '') or '').strip()
            if not openid:
                return jsonify({'success': False, 'message': '未登录或登录已过期'}), 401

            application = Application.query.filter(
                Application.id == application_id,
                Application.openid == openid
            ).first()
            if not application:
                return jsonify({'success': False, 'message': '未找到报名记录'}), 404

            if application.status != 'rejected':
                return jsonify({'success': False, 'message': '仅允许退回状态的报名进行修改并再次提交'}), 400

            data = request.get_json() or {}

            try:
                if isinstance(data, dict):
                    for k in ['teacher_phone', 'leader_phone', 'participant_phone', 'participant_email']:
                        if k in data and data[k] is not None:
                            data[k] = str(data[k]).strip()
            except Exception:
                pass

            required_fields = [
                'category', 'task', 'education_level', 'participant_count',
                'school_name',
                'teacher_name', 'teacher_phone',
                'leader_name', 'leader_phone',
                'participant_phone', 'participant_email',
                'participants'
            ]

            missing_fields = []
            for field in required_fields:
                if field not in data or not data[field]:
                    missing_fields.append(field)
            if missing_fields:
                return jsonify({'success': False, 'message': '缺少必填字段', 'errors': missing_fields}), 400

            validation_errors = []
            if not validate_phone(data['teacher_phone']):
                validation_errors.append('teacher_phone: 手机号格式不正确，应为11位数字')
            if not validate_phone(data['leader_phone']):
                validation_errors.append('leader_phone: 手机号格式不正确，应为11位数字')
            if not validate_phone(data['participant_phone']):
                validation_errors.append('participant_phone: 手机号格式不正确，应为11位数字')
            if not validate_email(data['participant_email']):
                validation_errors.append('participant_email: 邮箱格式不正确')

            rule_errors = validate_competition_rules(
                data['category'],
                data['task'],
                data['education_level'],
                data['participant_count']
            )
            validation_errors.extend(rule_errors)

            participants = data['participants']
            if not isinstance(participants, list) or len(participants) != data['participant_count']:
                validation_errors.append(f'participants: 需要提供 {data["participant_count"]} 名选手信息')
            for i, participant in enumerate(participants):
                if not isinstance(participant, dict) or 'participant_name' not in participant or not participant['participant_name']:
                    validation_errors.append(f'participants[{i}]: 选手姓名不能为空')

            if validation_errors:
                return jsonify({'success': False, 'message': '数据验证失败', 'errors': validation_errors}), 400

            contact_name = ''
            try:
                if isinstance(participants, list) and len(participants) > 0:
                    contact_name = (participants[0] or {}).get('participant_name', '')
            except Exception:
                contact_name = ''

            if not contact_name:
                return jsonify({'success': False, 'message': '数据验证失败', 'errors': ['contact_name: 联系人姓名无法自动生成，请确保已填写选手1姓名']}), 400

            phone_hash = hashlib.sha256(data['participant_phone'].encode()).hexdigest()
            existing_application = Application.query.filter(
                Application.contact_phone_hash == phone_hash,
                Application.status.in_(['pending', 'approved']),
                Application.id != application.id
            ).first()
            if existing_application:
                return jsonify({'success': False, 'message': '您已有待审核或已通过的报名记录，请勿重复提交'}), 400

            application.category = data['category']
            application.task = data['task']
            application.education_level = data['education_level']
            application.participant_count = data['participant_count']
            application.school_name = data['school_name']
            application.school_region = data.get('school_region', '')
            application.school_city = data.get('school_city', '')
            application.school_district = data.get('school_district', '')
            application.teacher_name = data['teacher_name']
            application.leader_name = data['leader_name']
            application.contact_name = contact_name

            application.teacher_phone = data['teacher_phone']
            application.leader_phone = data['leader_phone']
            application.participant_phone = data['participant_phone']
            application.participant_email = data['participant_email']
            application.contact_phone = data['participant_phone']
            application.contact_email = data['participant_email']

            application.status = 'pending'
            application.rejected_reason = None
            application.reviewed_at = None
            application.reviewed_by = None

            ApplicationParticipant.query.filter(ApplicationParticipant.application_id == application.id).delete()
            for i, participant in enumerate(participants):
                db.session.add(ApplicationParticipant(
                    application_id=application.id,
                    seq_no=i + 1,
                    participant_name=participant['participant_name']
                ))

            db.session.commit()

            return jsonify({'success': True, 'message': '已再次提交，请等待审核', 'data': application.to_dict(include_sensitive=True)})
    except Exception as e:
        from app import db
        db.session.rollback()
        return jsonify({'success': False, 'message': '系统错误，请稍后重试', 'error': str(e)}), 500

@api_bp.route('/api/register', methods=['POST'])
@require_user()
def register():
    """学生端报名接口"""
    try:
        # 延迟导入以避免循环依赖
        from app import app, db
        import hashlib
        from models import Application, ApplicationParticipant
        from config import COMPETITION_RULES
        
        with app.app_context():  # 添加应用上下文
            data = request.get_json()

            # 兼容前端可能传 number/带空格的情况：统一转为字符串再做校验/加密/哈希
            try:
                if isinstance(data, dict):
                    for k in ['teacher_phone', 'leader_phone', 'participant_phone', 'participant_email']:
                        if k in data and data[k] is not None:
                            data[k] = str(data[k]).strip()
            except Exception:
                pass
            
            # 必填字段检查
            required_fields = [
                'category', 'task', 'education_level', 'participant_count',
                'school_name',
                'teacher_name', 'teacher_phone',
                'leader_name', 'leader_phone',
                'participant_phone', 'participant_email',
                'participants'
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in data or not data[field]:
                    missing_fields.append(field)
            
            if missing_fields:
                return jsonify({
                    'success': False,
                    'message': '缺少必填字段',
                    'errors': missing_fields
                }), 400
            
            # 格式验证
            validation_errors = []
            
            # 手机号验证
            if not validate_phone(data['teacher_phone']):
                validation_errors.append('teacher_phone: 手机号格式不正确，应为11位数字')

            if not validate_phone(data['leader_phone']):
                validation_errors.append('leader_phone: 手机号格式不正确，应为11位数字')

            if not validate_phone(data['participant_phone']):
                validation_errors.append('participant_phone: 手机号格式不正确，应为11位数字')
            
            # 邮箱验证
            if not validate_email(data['participant_email']):
                validation_errors.append('participant_email: 邮箱格式不正确')
            
            # 竞赛规则验证
            rule_errors = validate_competition_rules(
                data['category'], 
                data['task'], 
                data['education_level'], 
                data['participant_count']
            )
            validation_errors.extend(rule_errors)
            
            # 选手信息验证
            participants = data['participants']
            if not isinstance(participants, list) or len(participants) != data['participant_count']:
                validation_errors.append(f'participants: 需要提供 {data["participant_count"]} 名选手信息')
            
            for i, participant in enumerate(participants):
                if not isinstance(participant, dict) or 'participant_name' not in participant or not participant['participant_name']:
                    validation_errors.append(f'participants[{i}]: 选手姓名不能为空')
            
            if validation_errors:
                return jsonify({
                    'success': False,
                    'message': '数据验证失败',
                    'errors': validation_errors
                }), 400

            # 联系人信息：不再让用户重复填写
            # 约定：联系人手机号/邮箱 = 参赛人手机号/邮箱；联系人姓名 = 选手1姓名
            contact_name = ''
            try:
                if isinstance(participants, list) and len(participants) > 0:
                    contact_name = (participants[0] or {}).get('participant_name', '')
            except Exception:
                contact_name = ''

            if not contact_name:
                return jsonify({
                    'success': False,
                    'message': '数据验证失败',
                    'errors': ['contact_name: 联系人姓名无法自动生成，请确保已填写选手1姓名']
                }), 400
            
            # 检查是否已有待审核或已通过的记录
            phone_hash = hashlib.sha256(data['participant_phone'].encode()).hexdigest()
            existing_application = Application.query.filter(
                Application.contact_phone_hash == phone_hash,
                Application.status.in_(['pending', 'approved'])
            ).first()
            
            if existing_application:
                return jsonify({
                    'success': False,
                    'message': '您已有待审核或已通过的报名记录，请勿重复提交'
                }), 400
            
            # 创建新的报名记录
            payload = getattr(request, 'user_payload', {}) or {}
            openid = str(payload.get('openid', '') or '').strip() or None
            application = Application(
                openid=openid,
                category=data['category'],
                task=data['task'],
                education_level=data['education_level'],
                participant_count=data['participant_count'],
                school_name=data['school_name'],
                school_region=data.get('school_region', ''),
                school_city=data.get('school_city', ''),
                school_district=data.get('school_district', ''),
                teacher_name=data['teacher_name'],
                leader_name=data['leader_name'],
                contact_name=contact_name,
                status='pending'
            )

            application.teacher_phone = data['teacher_phone']
            application.leader_phone = data['leader_phone']
            application.participant_phone = data['participant_phone']
            application.participant_email = data['participant_email']
            application.contact_phone = data['participant_phone']
            application.contact_email = data['participant_email']
            
            db.session.add(application)
            db.session.flush()  # 获取application.id
            
            # 添加选手信息
            for i, participant in enumerate(participants):
                participant_record = ApplicationParticipant(
                    application_id=application.id,
                    seq_no=i + 1,
                    participant_name=participant['participant_name']
                )
                db.session.add(participant_record)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': '报名成功，请等待审核',
                'data': application.to_dict(include_sensitive=True)
            }), 201
            
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '系统错误，请稍后重试',
            'error': str(e)
        }), 500

@api_bp.route('/api/applications', methods=['GET'])
@require_admin()
def get_applications():
    """获取报名列表（管理员用）"""
    try:
        from app import app, db
        from models import Application
        
        with app.app_context():
            page = request.args.get('page', 1, type=int)
            per_page = request.args.get('per_page', 20, type=int)
            status = request.args.get('status')
            
            query = Application.query
            
            if status:
                query = query.filter(Application.status == status)
            
            applications = query.order_by(Application.created_at.desc()).paginate(
                page=page, per_page=per_page, error_out=False
            )
            
            return jsonify({
                'success': True,
                'data': {
                    'applications': [app.to_dict(include_sensitive=True) for app in applications.items],
                    'total': applications.total,
                    'pages': applications.pages,
                    'current_page': page
                }
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取数据失败',
            'error': str(e)
        }), 500


@api_bp.route('/api/application/by-match-no', methods=['GET'])
@require_user()
def get_application_by_match_no():
    """按参赛号查询报名/获奖信息（学生端用）"""
    try:
        from app import app
        from models import Application

        with app.app_context():
            match_no = str(request.args.get('match_no', '') or '').strip()
            if not match_no:
                return jsonify({'success': False, 'message': '请提供参赛号'}), 400

            application = Application.query.filter(
                Application.match_no == match_no,
                Application.award_level.isnot(None)
            ).first()
            if not application:
                return jsonify({'success': False, 'message': '未找到该参赛号对应的记录'}), 404

            return jsonify({'success': True, 'data': application.to_dict()})
    except Exception as e:
        return jsonify({'success': False, 'message': '获取数据失败', 'error': str(e)}), 500


@api_bp.route('/api/applications/by-phone', methods=['GET'])
@require_user()
def get_applications_by_phone():
    """按手机号查询报名状态（学生端用）"""
    try:
        from app import app
        import hashlib
        from models import Application

        with app.app_context():
            phone = str(request.args.get('phone', '') or '').strip()
            if not phone:
                return jsonify({'success': False, 'message': '请提供手机号'}), 400

            payload = getattr(request, 'user_payload', {}) or {}
            openid = str(payload.get('openid', '') or '').strip()

            phone_hash = hashlib.sha256(phone.encode()).hexdigest()
            applications = Application.query.filter(
                Application.contact_phone_hash == phone_hash,
                Application.openid == openid
            ).order_by(Application.created_at.desc()).all()

            return jsonify({'success': True, 'data': [a.to_dict() for a in applications]})
    except Exception as e:
        return jsonify({'success': False, 'message': '获取数据失败', 'error': str(e)}), 500

@api_bp.route('/api/my-applications', methods=['GET'])
@require_user()
def get_my_applications():
    """获取我的报名记录"""
    try:
        from app import app, db
        from models import Application
        
        with app.app_context():
            match_no = request.args.get('match_no')
            if not match_no:
                return jsonify({
                    'success': False,
                    'message': '请提供参赛号'
                }), 400

            match_no = str(match_no).strip()

            applications = Application.query.filter(
                Application.match_no == match_no,
                Application.award_level.isnot(None)
            ).order_by(Application.created_at.desc()).all()
            
            return jsonify({
                'success': True,
                'data': [app.to_dict() for app in applications]
            })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取数据失败',
            'error': str(e)
        }), 500

@api_bp.route('/api/competition-rules', methods=['GET'])
def get_competition_rules():
    """获取竞赛规则"""
    from config import COMPETITION_RULES
    return jsonify({
        'success': True,
        'data': COMPETITION_RULES
    })
