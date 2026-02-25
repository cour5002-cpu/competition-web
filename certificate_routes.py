from flask import Blueprint, request, jsonify, send_file
import io
import json
import zipfile
from datetime import datetime
import os
import threading
import uuid

from PIL import Image

from admin_auth import require_admin
from user_auth import require_user

certificate_bp = Blueprint('certificate', __name__)


_CERT_CACHE_DIR = os.path.join(os.getcwd(), 'generated_certs')
_CERT_TASK_DIR = os.path.join(os.getcwd(), 'generated_cert_tasks')


def _ensure_dir(p: str):
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass


def _task_path(task_id: str) -> str:
    return os.path.join(_CERT_TASK_DIR, f"{task_id}.json")


def _write_json(path: str, payload: dict):
    try:
        folder = os.path.dirname(path)
        _ensure_dir(folder)
        tmp = f"{path}.tmp"
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        try:
            os.replace(tmp, path)
        except Exception:
            os.remove(tmp)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _read_json(path: str):
    try:
        if not os.path.exists(path):
            return None
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def _cache_pdf_path(kind: str, key: str) -> str:
    kind = str(kind or '').strip().lower()
    safe_key = _safe_filename_part(key)
    folder = os.path.join(_CERT_CACHE_DIR, kind)
    return os.path.join(folder, f"{safe_key}.pdf")


def _write_pdf_atomic(path: str, content: bytes) -> bool:
    try:
        folder = os.path.dirname(path)
        _ensure_dir(folder)
        tmp = f"{path}.tmp"
        with open(tmp, 'wb') as f:
            f.write(content)
        os.replace(tmp, path)
        return True
    except Exception:
        try:
            if os.path.exists(f"{path}.tmp"):
                os.remove(f"{path}.tmp")
        except Exception:
            pass
        return False


def _try_send_cached_pdf(path: str, download_name: str):
    try:
        if path and os.path.exists(path):
            return send_file(
                path,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=download_name
            )
    except Exception:
        return None
    return None


def _start_background_cert_task(*, application_ids, source: str = ''):
    task_id = uuid.uuid4().hex
    now = datetime.now().isoformat()
    payload = {
        'task_id': task_id,
        'source': str(source or ''),
        'status': 'queued',
        'created_at': now,
        'started_at': None,
        'finished_at': None,
        'progress': {
            'total_applications': int(len(application_ids or [])),
            'done_applications': 0,
            'generated_files': 0,
            'errors': 0
        },
        'application_ids': [int(x) for x in (application_ids or []) if str(x).strip().isdigit()],
        'error_details': []
    }
    _write_json(_task_path(task_id), payload)

    def _run():
        meta_path = _task_path(task_id)
        meta = _read_json(meta_path) or payload
        meta['status'] = 'running'
        meta['started_at'] = datetime.now().isoformat()
        _write_json(meta_path, meta)

        try:
            from app import app as flask_app
            from models import Application, CertificateTemplate
            from certificate_generator import CertificateGenerator

            with flask_app.app_context():
                ids = meta.get('application_ids') or []
                applications = Application.query.filter(
                    Application.id.in_(ids),
                    Application.award_level.isnot(None)
                ).all()

                generator = CertificateGenerator()

                total = len(applications)
                try:
                    meta['progress']['total_applications'] = int(total)
                except Exception:
                    pass
                _write_json(meta_path, meta)

                for idx, application in enumerate(applications):
                    try:
                        match_no = _safe_filename_part(application.match_no)
                        participants = sorted(application.participants, key=lambda p: p.seq_no)
                        name_part = "、".join([p.participant_name for p in participants]) if participants else ''

                        _normalize_application_for_cert(application)

                        template_config, err = _pick_template_config(
                            CertificateTemplate,
                            generator,
                            category=application.category,
                            award_level=application.award_level,
                            fallback_award_level='一等奖'
                        )
                        if err:
                            raise ValueError(err)
                        template_config = _apply_student_award_level_red(template_config)

                        player_pdf = generator.generate_certificate(application, template_config)
                        player_filename = (
                            f"{match_no}_"
                            f"{_safe_filename_part(name_part)}_"
                            f"{_safe_filename_part(application.category)}_"
                            f"{_safe_filename_part(application.education_level)}_"
                            f"{_safe_filename_part(application.award_level)}.pdf"
                        )
                        player_path = _cache_pdf_path('player', str(application.id))
                        if _write_pdf_atomic(player_path, player_pdf):
                            meta['progress']['generated_files'] = int(meta['progress'].get('generated_files', 0) or 0) + 1

                        coach_award_level = f"{application.award_level}-辅导员"
                        coach_config, coach_err = _pick_template_config(
                            CertificateTemplate,
                            generator,
                            category=application.category,
                            award_level=coach_award_level,
                            fallback_award_level='一等奖-辅导员'
                        )
                        if coach_err:
                            raise ValueError(coach_err)
                        try:
                            if isinstance(coach_config, dict):
                                coach_config['bg_width'] = 1240
                        except Exception:
                            pass
                        coach_config = _ensure_coach_title_red(coach_config)
                        coach_pdf = generator.generate_certificate(application, coach_config)
                        teacher_name = getattr(application, 'teacher_name', '') or ''
                        coach_filename = (
                            f"{match_no}_"
                            f"{_safe_filename_part(teacher_name)}_"
                            f"{_safe_filename_part(application.category)}_"
                            f"{_safe_filename_part(coach_award_level)}.pdf"
                        )
                        coach_path = _cache_pdf_path('coach', str(application.id))
                        if _write_pdf_atomic(coach_path, coach_pdf):
                            meta['progress']['generated_files'] = int(meta['progress'].get('generated_files', 0) or 0) + 1

                        manifest_path = os.path.join(_CERT_CACHE_DIR, 'manifests')
                        _ensure_dir(manifest_path)
                        _write_json(
                            os.path.join(manifest_path, f"{application.id}.json"),
                            {
                                'application_id': application.id,
                                'player_filename': player_filename,
                                'coach_filename': coach_filename,
                                'updated_at': datetime.now().isoformat()
                            }
                        )

                    except Exception as e:
                        meta['progress']['errors'] = int(meta['progress'].get('errors', 0) or 0) + 1
                        try:
                            meta['error_details'].append({'application_id': getattr(application, 'id', None), 'error': str(e)})
                            if len(meta['error_details']) > 50:
                                meta['error_details'] = meta['error_details'][-50:]
                        except Exception:
                            pass

                    try:
                        meta['progress']['done_applications'] = int(idx + 1)
                    except Exception:
                        pass
                    _write_json(meta_path, meta)

                meta['status'] = 'finished'
                meta['finished_at'] = datetime.now().isoformat()
                _write_json(meta_path, meta)

        except Exception as e:
            meta['status'] = 'failed'
            meta['finished_at'] = datetime.now().isoformat()
            meta['error_details'] = meta.get('error_details') or []
            try:
                meta['error_details'].append({'error': str(e)})
            except Exception:
                pass
            _write_json(meta_path, meta)

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    return task_id


def _build_centered_stamp_images(*, cert_kind: str, count: int, width: float, height: float, gap: float, y: float, unit: str, y_origin: str, y_anchor: str, keep_aspect: bool, dx: float = 0):
    cert_kind = str(cert_kind or '').strip().lower()
    count = int(count or 0)
    if cert_kind not in ('player', 'coach') or count <= 0:
        return []

    try:
        total_w = float(width) * count + float(gap) * (count - 1)
        start_x = -total_w / 2.0
    except Exception:
        start_x = 0.0

    stamps = []
    for i in range(count):
        x = start_x + i * (float(width) + float(gap)) + float(dx or 0)
        # Each stamp uses its own file path so it can be replaced independently.
        # Files are managed by admin endpoints under assets/cert/stamps/<kind>/<idx>.png
        img_path = f"assets/cert/stamps/{cert_kind}/{i + 1}.png"
        stamps.append({
            'image': img_path,
            'fallback_images': [
                'assets/cert/测试盖章.png',
                'assets/cert/test.png',
            ],
            'center_x': True,
            'x': x,
            'width': width,
            'height': height,
            'unit': unit,
            'y_origin': y_origin,
            'y': y,
            'y_anchor': y_anchor,
            'keep_aspect': bool(keep_aspect),
        })
    return stamps


def _pick_template_config(CertificateTemplate, generator, *, category, award_level, fallback_award_level=None):
    """Pick template config with fallbacks.

    Priority:
    1) exact match: category + award_level
    2) any category + award_level
    3) exact match: category + fallback_award_level (optional)
    4) any category + fallback_award_level (optional)
    """
    template = CertificateTemplate.query.filter(
        CertificateTemplate.category == category,
        CertificateTemplate.award_level == award_level
    ).first()

    if not template:
        template = CertificateTemplate.query.filter(
            CertificateTemplate.award_level == award_level
        ).first()

    if (not template) and fallback_award_level:
        template = CertificateTemplate.query.filter(
            CertificateTemplate.category == category,
            CertificateTemplate.award_level == fallback_award_level
        ).first()

    if (not template) and fallback_award_level:
        template = CertificateTemplate.query.filter(
            CertificateTemplate.award_level == fallback_award_level
        ).first()

    if template:
        return template.get_config(), None

    # 最后兜底：仍然找不到，返回明确错误（不再悄悄用默认模板导致“错版”）
    if fallback_award_level:
        return None, f"未找到证书模板: {category} - {award_level}（或兜底 {fallback_award_level}）"
    return None, f"未找到证书模板: {category} - {award_level}"


def _safe_filename_part(val: str) -> str:
    s = str(val or '').strip()
    if not s:
        return 'NA'
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|', '\n', '\r', '\t']:
        s = s.replace(ch, '_')
    return s


def _assert_user_owns_application(application):
    payload = getattr(request, 'user_payload', {}) or {}
    openid = str(payload.get('openid', '') or '').strip()
    if not openid:
        return False
    return bool(application and application.openid and application.openid == openid)


def _find_awarded_application_for_coach(*, teacher_name: str, teacher_phone_hash: str):
    from models import Application
    if not teacher_name or not teacher_phone_hash:
        return None
    return Application.query.filter(
        Application.teacher_name == teacher_name,
        Application.teacher_phone_hash == teacher_phone_hash,
        Application.award_level.isnot(None)
    ).order_by(Application.created_at.desc()).first()


def _strip_category_sai_suffix(application):
    try:
        cat = str(getattr(application, 'category', '') or '')
        if cat.endswith('赛'):
            setattr(application, 'category', cat[:-1])
    except Exception:
        pass


def _strip_task_sai_suffix(application):
    try:
        task = str(getattr(application, 'task', '') or '')
        if task.endswith('赛'):
            setattr(application, 'task', task[:-1])
    except Exception:
        pass


def _normalize_application_for_cert(application):
    _strip_category_sai_suffix(application)
    _strip_task_sai_suffix(application)


def _apply_student_award_level_red(template_config):
    try:
        template_config = dict(template_config or {})
        texts = template_config.get('texts')
        if isinstance(texts, list):
            for item in texts:
                if not isinstance(item, dict):
                    continue
                field = str(item.get('field', '') or '').strip()
                fixed_text = str(item.get('text', '') or '').strip()
                if field == 'award_level':
                    item['color'] = '#D0021B'
                    continue
                if fixed_text:
                    if fixed_text.endswith('等奖') or fixed_text == '优秀奖':
                        item['color'] = '#D0021B'
        return template_config
    except Exception:
        return template_config


def _strip_coach_title_texts(template_config):
    try:
        template_config = dict(template_config or {})
        texts = template_config.get('texts')
        if not isinstance(texts, list):
            return template_config
        filtered = []
        for item in texts:
            if not isinstance(item, dict):
                filtered.append(item)
                continue
            field = str(item.get('field', '') or '').strip()
            fixed_text = str(item.get('text', '') or '').strip()
            if field == 'award_level':
                continue
            if fixed_text == '优秀辅导员':
                continue
            filtered.append(item)
        template_config['texts'] = filtered
        return template_config
    except Exception:
        return template_config


def _ensure_coach_title_red(template_config):
    try:
        template_config = dict(template_config or {})
        texts = template_config.get('texts')
        if not isinstance(texts, list):
            texts = []

        filtered = []
        for item in texts:
            if not isinstance(item, dict):
                filtered.append(item)
                continue
            field = str(item.get('field', '') or '').strip()
            fixed_text = str(item.get('text', '') or '').strip()
            if field == 'award_level':
                continue
            if fixed_text == '优秀辅导员':
                continue
            filtered.append(item)

        filtered.append({
            'text': '优秀辅导员',
            'font': '华文楷体',
            'font_size': 145,
            'align': 'center',
            'glyph_dx': {'优': 20, '秀': 10, '导': -10, '员': -20},
            'char_space': -1.2,
            'color': '#D0021B',
            'width': int(template_config.get('page_width') or template_config.get('bg_width') or 1240),
            'x': 0,
            'x_anchor': 'left',
            'y': 1465,
        })

        template_config['texts'] = filtered
        return template_config
    except Exception:
        return template_config

@certificate_bp.route('/api/certificate/generate/<int:application_id>', methods=['GET'])
@require_user()
def generate_certificate(application_id):
    """生成证书PDF"""
    try:
        from models import Application, CertificateTemplate
        from certificate_generator import CertificateGenerator
        
        # 获取申请记录
        application = Application.query.get(application_id)
        if not application:
            return jsonify({
                'success': False,
                'message': '未找到申请记录'
            }), 404
        
        if not application.award_level:
            return jsonify({
                'success': False,
                'message': '该记录暂无获奖信息，无法生成证书'
            }), 400
        
        participants = sorted(application.participants, key=lambda p: p.seq_no)
        name_part = "、".join([p.participant_name for p in participants]) if participants else ''
        filename = (
            f"{_safe_filename_part(application.match_no)}_"
            f"{_safe_filename_part(name_part)}_"
            f"{_safe_filename_part(application.category)}_"
            f"{_safe_filename_part(application.education_level)}_"
            f"{_safe_filename_part(application.award_level)}.pdf"
        )

        cached_path = _cache_pdf_path('player', str(application.id))
        cached_resp = _try_send_cached_pdf(cached_path, filename)
        if cached_resp is not None:
            return cached_resp

        generator = CertificateGenerator()

        _normalize_application_for_cert(application)

        # 选手证书：甲方未提供二/三等奖模板前，统一使用“一等奖”模板
        template_config, err = _pick_template_config(
            CertificateTemplate,
            generator,
            category=application.category,
            award_level=application.award_level,
            fallback_award_level='一等奖'
        )
        if err:
            return jsonify({
                'success': False,
                'message': err
            }), 404

        template_config = _apply_student_award_level_red(template_config)

        # Student stamps (final): always inject 6 stamps at the bottom.
        # Do NOT depend on a specific background_image value, because templates may vary.
        # IMPORTANT: Do NOT override the template coordinate system (coord_unit/y_origin).
        # Otherwise mm-based templates will render texts off-page and appear as "no text".
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            bg_rel = str((template_config or {}).get('background_image', '') or '').strip()
            bg_abs = ''
            if bg_rel and (not os.path.isabs(bg_rel)):
                bg_abs = os.path.join(base_dir, bg_rel)
            elif bg_rel:
                bg_abs = bg_rel

            bg_w = None
            if bg_abs and os.path.exists(bg_abs):
                try:
                    bg_w, _bg_h = Image.open(bg_abs).size
                except Exception:
                    bg_w = None

            stamp_count = 6
            stamp_margin = 80
            stamp_gap = 30
            if bg_w:
                stamp_w = max(60, int((int(bg_w) - 2 * stamp_margin - stamp_gap * (stamp_count - 1)) / stamp_count))
            else:
                # Safe fallback when background image is unknown/unreadable.
                stamp_w = 120

            template_config = dict(template_config or {})
            template_config.update({
                'stamp_images': _build_centered_stamp_images(
                    cert_kind='player',
                    count=stamp_count,
                    width=stamp_w,
                    height=stamp_w,
                    gap=stamp_gap,
                    y=140,
                    unit='px',
                    y_origin='bottom',
                    y_anchor='center',
                    keep_aspect=True,
                    dx=68,
                ),
            })
        except Exception:
            pass
        
        pdf_content = generator.generate_certificate(application, template_config)
        _write_pdf_atomic(cached_path, pdf_content)
        
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'生成证书失败: {str(e)}'
        }), 500


@certificate_bp.route('/api/certificate/generate-excellent-coach/<int:coach_id>', methods=['GET'])
@require_user()
def generate_excellent_coach_certificate(coach_id):
    """生成优秀辅导员证书PDF（学生端查询后下载）"""
    try:
        from models import ExcellentCoach, CertificateTemplate
        from certificate_generator import CertificateGenerator

        coach = ExcellentCoach.query.get(coach_id)
        if not coach:
            return jsonify({'success': False, 'message': '未找到优秀辅导员记录'}), 404

        application = _find_awarded_application_for_coach(
            teacher_name=coach.teacher_name,
            teacher_phone_hash=coach.teacher_phone_hash
        )
        if not application:
            return jsonify({'success': False, 'message': '暂无获奖数据，无法生成证书'}), 404

        try:
            setattr(application, 'teacher_name', coach.teacher_name)
        except Exception:
            pass

        filename = (
            f"{_safe_filename_part(application.match_no)}_"
            f"{_safe_filename_part(coach.teacher_name)}_"
            f"{_safe_filename_part(application.category)}_"
            f"优秀辅导员.pdf"
        )

        cached_path = _cache_pdf_path('excellent_coach', str(coach.id))
        cached_resp = _try_send_cached_pdf(cached_path, filename)
        if cached_resp is not None:
            return cached_resp

        generator = CertificateGenerator()

        coach_award_level = f"{application.award_level}-辅导员"

        template_config, err = _pick_template_config(
            CertificateTemplate,
            generator,
            category=application.category,
            award_level=coach_award_level,
            fallback_award_level='一等奖-辅导员'
        )
        if err:
            return jsonify({'success': False, 'message': err}), 404

        try:
            template_config = dict(template_config or {})
        except Exception:
            template_config = template_config

        try:
            cat = str(getattr(application, 'category', '') or '')
            if cat.endswith('赛'):
                setattr(application, 'category', cat[:-1])
        except Exception:
            pass

        try:
            if isinstance(template_config, dict):
                bg_w = 1240
                try:
                    bg_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'cert', 'coach.png')
                    bg_w, _bg_h = Image.open(bg_abs).size
                except Exception:
                    bg_w = 1240

                stamp_count = 6
                stamp_margin = 80
                stamp_gap = 20
                stamp_w = max(50, int((int(bg_w) - 2 * stamp_margin - stamp_gap * (stamp_count - 1)) / stamp_count))

                template_config['background_image'] = 'assets/cert/coach.png'
                template_config['coord_unit'] = 'px'
                template_config['y_origin'] = 'top'
                template_config['use_background_size'] = True
                template_config['global_y_offset'] = 0

                # Final coach texts layout (must match coach_final_with_test_stamp_*.pdf)
                template_config['texts'] = [
                    {
                        'field': 'teacher_name',
                        'font': '宋体',
                        'font_size': 34,
                        'align': 'center',
                        'width': 150,
                        'x': 320,
                        'x_anchor': 'left',
                        'y': 1080,
                    },
                    {
                        'field': 'category',
                        'font': '宋体',
                        'font_size': 52,
                        'align': 'right',
                        'width': 500,
                        'x': 780,
                        'x_anchor': 'right',
                        'y': 1280,
                    },
                ]

                template_config['stamp_images'] = _build_centered_stamp_images(
                    cert_kind='coach',
                    count=stamp_count,
                    width=stamp_w,
                    height=stamp_w,
                    gap=stamp_gap,
                    y=170,
                    unit='px',
                    y_origin='bottom',
                    y_anchor='center',
                    keep_aspect=True,
                    dx=70,
                )
        except Exception:
            pass

        try:
            if isinstance(template_config, dict):
                try:
                    bg_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'cert', 'coach.png')
                    bg_w, _bg_h = Image.open(bg_abs).size
                    template_config['bg_width'] = int(bg_w)
                except Exception:
                    pass
        except Exception:
            pass

        template_config = _ensure_coach_title_red(template_config)

        pdf_content = generator.generate_certificate(application, template_config)
        _write_pdf_atomic(cached_path, pdf_content)

        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({'success': False, 'message': f'生成辅导员证书失败: {str(e)}'}), 500

@certificate_bp.route('/api/certificate/generate-coach/<int:application_id>', methods=['GET'])
@require_admin()
def generate_coach_certificate(application_id):
    """生成辅导员证书PDF（使用 award_level + '-辅导员' 模板）"""
    try:
        from models import Application, CertificateTemplate
        from certificate_generator import CertificateGenerator

        application = Application.query.get(application_id)
        if not application:
            return jsonify({
                'success': False,
                'message': '未找到申请记录'
            }), 404

        if not application.award_level:
            return jsonify({
                'success': False,
                'message': '该记录暂无获奖信息，无法生成证书'
            }), 400

        teacher_name = getattr(application, 'teacher_name', '') or ''
        coach_award_level = f"{application.award_level}-辅导员"
        filename = (
            f"{_safe_filename_part(application.match_no)}_"
            f"{_safe_filename_part(teacher_name)}_"
            f"{_safe_filename_part(application.category)}_"
            f"{_safe_filename_part(coach_award_level)}.pdf"
        )

        cached_path = _cache_pdf_path('coach', str(application.id))
        cached_resp = _try_send_cached_pdf(cached_path, filename)
        if cached_resp is not None:
            return cached_resp

        generator = CertificateGenerator()
        coach_award_level = coach_award_level

        # 辅导员证书：甲方未提供其他模板前，统一使用“一等奖-辅导员”模板
        template_config, err = _pick_template_config(
            CertificateTemplate,
            generator,
            category=application.category,
            award_level=coach_award_level,
            fallback_award_level='一等奖-辅导员'
        )
        if err:
            return jsonify({
                'success': False,
                'message': err
            }), 404

        try:
            template_config = dict(template_config or {})
        except Exception:
            template_config = template_config

        try:
            cat = str(getattr(application, 'category', '') or '')
            if cat.endswith('赛'):
                setattr(application, 'category', cat[:-1])
        except Exception:
            pass

        try:
            if isinstance(template_config, dict):
                bg_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'cert', 'coach.png')
                bg_w, _bg_h = Image.open(bg_abs).size

                stamp_count = 6
                stamp_margin = 80
                stamp_gap = 20
                stamp_w = max(50, int((int(bg_w) - 2 * stamp_margin - stamp_gap * (stamp_count - 1)) / stamp_count))

                template_config['background_image'] = 'assets/cert/coach.png'
                template_config['coord_unit'] = 'px'
                template_config['y_origin'] = 'top'
                template_config['use_background_size'] = True
                template_config['global_y_offset'] = 0

                template_config['texts'] = [
                    {
                        'field': 'teacher_name',
                        'font': '宋体',
                        'font_size': 34,
                        'align': 'center',
                        'width': 150,
                        'x': 320,
                        'x_anchor': 'left',
                        'y': 1080,
                    },
                    {
                        'field': 'category',
                        'font': '宋体',
                        'font_size': 52,
                        'align': 'right',
                        'width': 500,
                        'x': 780,
                        'x_anchor': 'right',
                        'y': 1280,
                    },
                ]

                template_config['stamp_images'] = _build_centered_stamp_images(
                    cert_kind='coach',
                    count=stamp_count,
                    width=stamp_w,
                    height=stamp_w,
                    gap=stamp_gap,
                    y=170,
                    unit='px',
                    y_origin='bottom',
                    y_anchor='center',
                    keep_aspect=True,
                    dx=70,
                )
        except Exception:
            pass

        try:
            if isinstance(template_config, dict):
                try:
                    bg_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'cert', 'coach.png')
                    bg_w, _bg_h = Image.open(bg_abs).size
                    template_config['bg_width'] = int(bg_w)
                except Exception:
                    pass
        except Exception:
            pass

        template_config = _ensure_coach_title_red(template_config)

        pdf_content = generator.generate_certificate(application, template_config)

        _write_pdf_atomic(cached_path, pdf_content)
        return send_file(
            io.BytesIO(pdf_content),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=filename
        )

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'生成辅导员证书失败: {str(e)}'
        }), 500

@certificate_bp.route('/api/certificate/batch-generate', methods=['POST'])
@require_admin()
def batch_generate_certificates():
    """批量生成证书"""
    try:
        data = request.get_json()
        application_ids = data.get('application_ids', [])
        
        if not application_ids:
            return jsonify({
                'success': False,
                'message': '请提供要生成证书的申请ID列表'
            }), 400
        
        task_id = _start_background_cert_task(application_ids=application_ids, source='batch-generate')
        return jsonify({
            'success': True,
            'message': '已开始后台生成证书，请稍后在“下载证书ZIP”页面下载',
            'data': {
                'task_id': task_id
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'批量生成失败: {str(e)}'
        }), 500


@certificate_bp.route('/api/admin/certificate-tasks/<string:task_id>', methods=['GET'])
@require_admin()
def get_certificate_task(task_id):
    try:
        meta = _read_json(_task_path(task_id))
        if not meta:
            return jsonify({'success': False, 'message': '任务不存在'}), 404
        return jsonify({'success': True, 'data': meta})
    except Exception as e:
        return jsonify({'success': False, 'message': f'查询失败: {str(e)}'}), 500


@certificate_bp.route('/api/admin/certificates/download-zip', methods=['GET'])
@require_admin()
def download_cached_certificates_zip():
    try:
        kind = str(request.args.get('kind', '') or '').strip().lower()
        task_id = str(request.args.get('task_id', '') or '').strip()

        kinds = ['player', 'coach', 'excellent_coach']
        if kind:
            if kind not in kinds:
                return jsonify({'success': False, 'message': 'kind 参数不合法'}), 400
            kinds = [kind]

        selected_ids = None
        if task_id:
            meta = _read_json(_task_path(task_id))
            if meta and isinstance(meta.get('application_ids'), list):
                selected_ids = [str(x) for x in meta.get('application_ids')]

        zip_buffer = io.BytesIO()
        found = 0
        with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for k in kinds:
                folder = os.path.join(_CERT_CACHE_DIR, k)
                if not os.path.exists(folder):
                    continue
                for fn in os.listdir(folder):
                    if not fn.lower().endswith('.pdf'):
                        continue
                    key = fn[:-4]
                    if selected_ids is not None and k in ('player', 'coach'):
                        if key not in selected_ids:
                            continue
                    fp = os.path.join(folder, fn)
                    if not os.path.isfile(fp):
                        continue
                    arcname = f"{k}/{fn}"
                    try:
                        zf.write(fp, arcname)
                        found += 1
                    except Exception:
                        continue

            zf.writestr('manifest.json', json.dumps({
                'found': found,
                'kind': kind or 'all',
                'task_id': task_id or None,
                'generated_at': datetime.now().isoformat()
            }, ensure_ascii=False, indent=2))

        if found <= 0:
            return jsonify({'success': False, 'message': '当前没有可下载的已生成证书'}), 404

        zip_buffer.seek(0)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        suffix = kind if kind else 'all'
        filename = f"证书已生成缓存_{suffix}_{ts}.zip"
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        return jsonify({'success': False, 'message': f'下载失败: {str(e)}'}), 500

@certificate_bp.route('/api/certificate/templates', methods=['GET'])
def get_certificate_templates():
    """获取证书模板列表"""
    try:
        from models import CertificateTemplate
        
        templates = CertificateTemplate.query.all()
        
        return jsonify({
            'success': True,
            'data': [{
                'id': template.id,
                'name': template.name,
                'category': template.category,
                'award_level': template.award_level,
                'config': template.get_config(),
                'created_at': template.created_at.isoformat() if template.created_at else None,
                'updated_at': template.updated_at.isoformat() if template.updated_at else None
            } for template in templates]
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': '获取模板失败',
            'error': str(e)
        }), 500

@certificate_bp.route('/api/certificate/templates', methods=['POST'])
def create_certificate_template():
    """创建证书模板"""
    try:
        from models import CertificateTemplate
        from app import db
        
        data = request.get_json()
        
        required_fields = ['name', 'category', 'award_level', 'config']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'message': f'缺少必填字段: {", ".join(missing_fields)}'
            }), 400
        
        # 检查是否已存在相同的模板
        existing_template = CertificateTemplate.query.filter(
            CertificateTemplate.category == data['category'],
            CertificateTemplate.award_level == data['award_level']
        ).first()
        
        if existing_template:
            return jsonify({
                'success': False,
                'message': f'已存在 {data["category"]} - {data["award_level"]} 的模板'
            }), 400
        
        # 创建新模板
        template = CertificateTemplate(
            name=data['name'],
            category=data['category'],
            award_level=data['award_level']
        )
        template.set_config(data['config'])
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '模板创建成功',
            'data': {
                'id': template.id,
                'name': template.name,
                'category': template.category,
                'award_level': template.award_level
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '创建模板失败',
            'error': str(e)
        }), 500

@certificate_bp.route('/api/certificate/templates/<int:template_id>', methods=['PUT'])
def update_certificate_template(template_id):
    """更新证书模板"""
    try:
        from models import CertificateTemplate
        from app import db
        
        template = CertificateTemplate.query.get(template_id)
        if not template:
            return jsonify({
                'success': False,
                'message': '模板不存在'
            }), 404
        
        data = request.get_json()
        
        if 'name' in data:
            template.name = data['name']
        
        if 'config' in data:
            template.set_config(data['config'])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '模板更新成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '更新模板失败',
            'error': str(e)
        }), 500

@certificate_bp.route('/api/certificate/templates/<int:template_id>', methods=['DELETE'])
def delete_certificate_template(template_id):
    """删除证书模板"""
    try:
        from models import CertificateTemplate
        from app import db
        
        template = CertificateTemplate.query.get(template_id)
        if not template:
            return jsonify({
                'success': False,
                'message': '模板不存在'
            }), 404
        
        db.session.delete(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': '模板删除成功'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': '删除模板失败',
            'error': str(e)
        }), 500
