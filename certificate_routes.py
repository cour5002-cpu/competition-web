from flask import Blueprint, request, jsonify, send_file
import io
import json
import zipfile
from datetime import datetime

from PIL import Image

from admin_auth import require_admin
from user_auth import require_user

certificate_bp = Blueprint('certificate', __name__)


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
        
        generator = CertificateGenerator()

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
        
        # 生成PDF
        pdf_content = generator.generate_certificate(application, template_config)
        
        # 创建文件响应
        participants = sorted(application.participants, key=lambda p: p.seq_no)
        name_part = "、".join([p.participant_name for p in participants]) if participants else ''
        filename = (
            f"{_safe_filename_part(application.match_no)}_"
            f"{_safe_filename_part(name_part)}_"
            f"{_safe_filename_part(application.category)}_"
            f"{_safe_filename_part(application.education_level)}_"
            f"{_safe_filename_part(application.award_level)}.pdf"
        )
        
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

        # 回滚：优秀辅导员证书走 coach.png（竖版）模板。
        # 文案：获奖级别固定显示“优秀辅导员”。
        try:
            template_config = dict(template_config or {})
        except Exception:
            template_config = template_config

        # 赛别：模板里自带“赛”字，这里不渲染末尾“赛”，并按“末字落点 x=750-800”做右对齐。
        try:
            cat = str(getattr(application, 'category', '') or '')
            if cat.endswith('赛'):
                setattr(application, 'category', cat[:-1])
        except Exception:
            pass

        try:
            texts = template_config.get('texts') if isinstance(template_config, dict) else None
            if isinstance(texts, list):
                for item in texts:
                    if isinstance(item, dict) and str(item.get('field', '') or '').strip() == 'category':
                        item['align'] = 'right'
                        item['width'] = int(item.get('width') or 500)
                        item['x'] = 780
                        item['x_anchor'] = 'right'
                        try:
                            item['y'] = float(item.get('y') or 0) + 10
                        except Exception:
                            pass
                        break
        except Exception:
            pass

        # “优秀辅导员”字号更大，并下移 50。
        try:
            texts = template_config.get('texts') if isinstance(template_config, dict) else None
            if isinstance(texts, list):
                for item in texts:
                    if not isinstance(item, dict):
                        continue
                    field = str(item.get('field', '') or '').strip()
                    fixed_text = str(item.get('text', '') or '').strip()
                    if field == 'award_level' or fixed_text == '优秀辅导员':
                        try:
                            item['font_size'] = int(float(item.get('font_size') or 0)) + 24
                        except Exception:
                            item['font_size'] = 140
                        try:
                            item['y'] = float(item.get('y') or 0) + 35
                        except Exception:
                            pass
                        # 回到 coach_preview_3 风格，并在此基础上再往内收一点（约 2px 体感）
                        # 单字微调（本轮）：仅“优”向右移 20px
                        item['glyph_dx'] = {
                            '优': 20,
                            '秀': 10,
                            '导': -10,
                            '员': -20,
                        }

                        # 在宽度范围内重新调整字间距：先回到一个温和值，后续再按你反馈微调
                        item['char_space'] = -1.2

                        # 略微缩小字号，避免两端外扩
                        try:
                            item['font_size'] = int(float(item.get('font_size') or 0))
                        except Exception:
                            pass
                        break
        except Exception:
            pass

        try:
            if str(request.args.get('debug_grid', '') or '').strip() in ('1', 'true', 'True'):
                template_config['debug_grid_overlay'] = {
                    'fine_step_px': 10,
                    'main_step_px': 50,
                    'fine_alpha': 0.18,
                    'main_alpha': 0.55,
                    'fine_line_width': 0.35,
                    'main_line_width': 0.9,
                    'label_font_size': 7,
                }
        except Exception:
            pass

        # 姓名/赛别字号互换
        try:
            texts = template_config.get('texts') if isinstance(template_config, dict) else None
            if isinstance(texts, list):
                name_item = None
                cat_item = None
                for item in texts:
                    if not isinstance(item, dict):
                        continue
                    field = str(item.get('field', '') or '').strip()
                    if field == 'contact_name':
                        name_item = item
                    elif field == 'category':
                        cat_item = item
                if isinstance(name_item, dict) and isinstance(cat_item, dict):
                    name_fs = name_item.get('font_size')
                    cat_fs = cat_item.get('font_size')
                    if name_fs is not None and cat_fs is not None:
                        name_item['font_size'] = cat_fs
                        cat_item['font_size'] = name_fs
        except Exception:
            pass

        # 确保模板里的 award_level 渲染为“优秀辅导员”
        try:
            setattr(application, 'award_level', '优秀辅导员')
        except Exception:
            pass

        # Coach stamps: 6 stamps centered-symmetric at bottom, y measured from bottom (final)
        try:
            if isinstance(template_config, dict):
                bg_abs = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets', 'cert', 'coach.png')
                bg_w, _bg_h = Image.open(bg_abs).size

                stamp_count = 6
                stamp_margin = 80
                stamp_gap = 20
                stamp_w = max(50, int((int(bg_w) - 2 * stamp_margin - stamp_gap * (stamp_count - 1)) / stamp_count))

                template_config['coord_unit'] = 'px'
                template_config['y_origin'] = 'top'
                template_config['use_background_size'] = True
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

        pdf_content = generator.generate_certificate(application, template_config)

        filename = (
            f"{_safe_filename_part(application.match_no)}_"
            f"{_safe_filename_part(coach.teacher_name)}_"
            f"{_safe_filename_part(application.category)}_"
            f"优秀辅导员.pdf"
        )

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

        generator = CertificateGenerator()
        coach_award_level = f"{application.award_level}-辅导员"

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
        pdf_content = generator.generate_certificate(application, template_config)

        teacher_name = getattr(application, 'teacher_name', '') or ''
        filename = (
            f"{_safe_filename_part(application.match_no)}_"
            f"{_safe_filename_part(teacher_name)}_"
            f"{_safe_filename_part(application.category)}_"
            f"{_safe_filename_part(coach_award_level)}.pdf"
        )
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
        from models import Application, CertificateTemplate
        from certificate_generator import CertificateGenerator
        
        data = request.get_json()
        application_ids = data.get('application_ids', [])
        
        if not application_ids:
            return jsonify({
                'success': False,
                'message': '请提供要生成证书的申请ID列表'
            }), 400
        
        # 获取所有申请记录
        applications = Application.query.filter(
            Application.id.in_(application_ids),
            Application.award_level.isnot(None)
        ).all()
        
        if not applications:
            return jsonify({
                'success': False,
                'message': '未找到有效的申请记录'
            }), 404
        
        generator = CertificateGenerator()
        generated = []
        errors = []
        
        for application in applications:
            try:
                match_no = _safe_filename_part(application.match_no)
                participants = sorted(application.participants, key=lambda p: p.seq_no)
                name_part = "、".join([p.participant_name for p in participants]) if participants else ''

                # 学生证书
                template_config, err = _pick_template_config(
                    CertificateTemplate,
                    generator,
                    category=application.category,
                    award_level=application.award_level,
                    fallback_award_level='一等奖'
                )
                if err:
                    raise ValueError(err)
                pdf_content = generator.generate_certificate(application, template_config)
                player_filename = (
                    f"{match_no}_"
                    f"{_safe_filename_part(name_part)}_"
                    f"{_safe_filename_part(application.category)}_"
                    f"{_safe_filename_part(application.education_level)}_"
                    f"{_safe_filename_part(application.award_level)}.pdf"
                )
                generated.append({
                    'application_id': application.id,
                    'kind': 'player',
                    'filename': player_filename,
                    'content': pdf_content
                })

                # 辅导员证书
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
                coach_pdf = generator.generate_certificate(application, coach_config)
                teacher_name = getattr(application, 'teacher_name', '') or ''
                coach_filename = (
                    f"{match_no}_"
                    f"{_safe_filename_part(teacher_name)}_"
                    f"{_safe_filename_part(application.category)}_"
                    f"{_safe_filename_part(coach_award_level)}.pdf"
                )
                generated.append({
                    'application_id': application.id,
                    'kind': 'coach',
                    'filename': coach_filename,
                    'content': coach_pdf
                })

            except Exception as e:
                errors.append({
                    'application_id': application.id,
                    'error': str(e)
                })

        if not generated:
            return jsonify({
                'success': False,
                'message': f'批量生成失败：全部生成失败（失败 {len(errors)} 个）',
                'data': {
                    'success_count': 0,
                    'error_count': len(errors),
                    'errors': errors
                }
            }), 500

        # 打包 zip（避免 bytes 进入 jsonify）
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
            for item in generated:
                zf.writestr(item['filename'], item['content'])

            manifest = {
                'total_requested': len(application_ids),
                'matched_with_award': len(applications),
                'success_count': len(generated),
                'error_count': len(errors),
                'errors': errors
            }
            zf.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))

        zip_buffer.seek(0)
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"证书批量生成_{ts}.zip"
        return send_file(
            zip_buffer,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'批量生成失败: {str(e)}'
        }), 500

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
