from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import black, white
from reportlab.lib.colors import Color
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
import io
import json
import math
import os

class CertificateGenerator:
    def __init__(self):
        self.page_width, self.page_height = A4
        self.register_fonts()
    
    def register_fonts(self):
        """注册中文字体"""
        self.font_aliases = {
            '黑体': 'SimHei',
            '宋体': 'SimSun',
            '幼圆': 'YouYuan',
            '华文楷体': 'STKaiti',
            'CJK': 'STSong',
            'SimHei': 'SimHei',
            'SimSun': 'SimSun',
            'YouYuan': 'YouYuan',
            'STKaiti': 'STKaiti',
            'STSong': 'STSong',
            'Helvetica': 'Helvetica'
        }

        self.registered_fonts = set(['Helvetica'])
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
            self.registered_fonts.add('STSong-Light')
        except Exception:
            pass

        base_dir = os.path.dirname(os.path.abspath(__file__))
        fonts_dir = os.path.join(base_dir, 'assets', 'fonts')
        candidates = [
            ('SimHei', ['simhei.ttf', 'SimHei.ttf', 'SimHei.TTF']),
            ('SimSun', ['simsun.ttc', 'SimSun.ttc', 'simsun.ttf', 'SimSun.ttf', 'simsunb.ttf', 'SimSunB.ttf', 'SIMSUNB.TTF']),
            ('YouYuan', ['youyuan.ttf', 'YouYuan.ttf', 'youyuan.ttc', 'YouYuan.ttc', 'SIMYOU.TTF', 'SimYou.ttf', 'simyou.ttf']),
            ('STKaiti', ['stkaiti.ttf', 'STKaiti.ttf', 'stkaiti.ttc', 'STKaiti.ttc', 'STKAITI.TTF', 'stkaiti.ttf']),
        ]

        for font_name, filenames in candidates:
            for fn in filenames:
                fp = os.path.join(fonts_dir, fn)
                if os.path.exists(fp):
                    try:
                        if fp.lower().endswith('.ttc'):
                            pdfmetrics.registerFont(TTFont(font_name, fp, subfontIndex=0))
                        else:
                            pdfmetrics.registerFont(TTFont(font_name, fp))
                        self.registered_fonts.add(font_name)
                        break
                    except Exception:
                        continue

        self.font_name = 'SimHei' if 'SimHei' in self.registered_fonts else 'Helvetica'
        self.cjk_fallback_font = 'STSong-Light' if 'STSong-Light' in self.registered_fonts else self.font_name

    def resolve_font_name(self, font_name):
        if not font_name:
            return self.font_name
        resolved = self.font_aliases.get(font_name, font_name)
        if resolved in self.registered_fonts:
            return resolved
        if self.cjk_fallback_font in self.registered_fonts:
            return self.cjk_fallback_font
        return self.font_name

    def px_to_pt(self, px):
        try:
            return float(px) * 0.75
        except Exception:
            return px

    def _px_top_to_pt_bottom(self, y_from_top_px: float, page_height_pt: float) -> float:
        return float(page_height_pt) - self.px_to_pt(y_from_top_px)

    def draw_debug_grid(self, canvas_obj, step_px=100, color=None, line_width=0.5, label=True, label_font_size=7):
        step_pt = self.px_to_pt(step_px)
        if not step_pt or step_pt <= 0:
            return

        if color is None:
            color = Color(1, 0, 0, alpha=0.25)

        canvas_obj.saveState()
        try:
            canvas_obj.setStrokeColor(color)
            canvas_obj.setFillColor(Color(1, 0, 0, alpha=0.65))
            canvas_obj.setLineWidth(line_width)

            # vertical lines
            x = 0.0
            while x <= self.page_width + 0.01:
                canvas_obj.line(x, 0, x, self.page_height)
                if label:
                    canvas_obj.setFont('Helvetica', label_font_size)
                    px_val = int(round(x / 0.75))
                    canvas_obj.drawString(x + 2, self.page_height - 10, f"x={px_val}px")
                x += step_pt

            # horizontal lines
            y = 0.0
            while y <= self.page_height + 0.01:
                canvas_obj.line(0, y, self.page_width, y)
                if label:
                    canvas_obj.setFont('Helvetica', label_font_size)
                    px_val = int(round(y / 0.75))
                    canvas_obj.drawString(2, y + 2, f"y={px_val}px")
                y += step_pt
        finally:
            canvas_obj.restoreState()

    def draw_debug_grid_overlay(self, canvas_obj, config: dict):
        try:
            fine_step = float((config or {}).get('fine_step_px', 10) or 10)
            main_step = float((config or {}).get('main_step_px', 50) or 50)
            fine_alpha = float((config or {}).get('fine_alpha', 0.18) or 0.18)
            main_alpha = float((config or {}).get('main_alpha', 0.45) or 0.45)
            fine_lw = float((config or {}).get('fine_line_width', 0.35) or 0.35)
            main_lw = float((config or {}).get('main_line_width', 0.8) or 0.8)
            label_fs = float((config or {}).get('label_font_size', 7) or 7)
        except Exception:
            fine_step, main_step = 10, 50
            fine_alpha, main_alpha = 0.18, 0.45
            fine_lw, main_lw = 0.35, 0.8
            label_fs = 7

        self.draw_debug_grid(
            canvas_obj,
            step_px=fine_step,
            color=Color(0.2, 0.2, 0.2, alpha=fine_alpha),
            line_width=fine_lw,
            label=False,
            label_font_size=label_fs,
        )
        self.draw_debug_grid(
            canvas_obj,
            step_px=main_step,
            color=Color(0.15, 0.15, 0.15, alpha=main_alpha),
            line_width=main_lw,
            label=True,
            label_font_size=label_fs,
        )

    def draw_debug_point(self, canvas_obj, x, y, radius=3.0, color=None, label=None, label_font_size=7):
        canvas_obj.saveState()
        try:
            if color is None:
                color = Color(1, 0, 0, alpha=0.9)
            canvas_obj.setStrokeColor(color)
            canvas_obj.setFillColor(color)
            # crosshair
            canvas_obj.setLineWidth(1)
            canvas_obj.line(x - radius * 2, y, x + radius * 2, y)
            canvas_obj.line(x, y - radius * 2, x, y + radius * 2)
            canvas_obj.circle(x, y, radius, stroke=1, fill=0)

            if label:
                canvas_obj.setFont('Helvetica', float(label_font_size))
                canvas_obj.drawString(x + radius * 2 + 1, y + radius * 2 + 1, str(label))
        finally:
            canvas_obj.restoreState()

    def draw_debug_box(self, canvas_obj, x, y, width, height=10, y_shift=0, color=None, line_width=0.8):
        canvas_obj.saveState()
        try:
            if color is None:
                color = Color(1, 0, 0, alpha=0.6)
            canvas_obj.setStrokeColor(color)
            canvas_obj.setLineWidth(float(line_width))
            canvas_obj.rect(x, y + y_shift, width, height, stroke=1, fill=0)
        finally:
            canvas_obj.restoreState()

    def get_field_text(self, application, field_name):
        if not field_name:
            return ""
        field_name = str(field_name).strip()

        def _norm(v):
            if v is None:
                return ""
            try:
                import math
                if isinstance(v, float) and math.isnan(v):
                    return ""
            except Exception:
                pass
            try:
                import pandas as pd
                if pd.isna(v):
                    return ""
            except Exception:
                pass
            s = str(v)
            if s.strip().lower() == 'nan':
                return ""
            return s

        # 兼容历史/第三方模板字段名：统一映射到选手姓名
        participant_field_aliases = {
            'participants_names',
            'participant_names',
            'participant_name',
            'name',
            'winner_name',
            'winners',
            'student_name',
            'student_names',
        }
        if field_name in participant_field_aliases:
            if application.participant_count > 1:
                participants = sorted(application.participants, key=lambda p: p.seq_no)
                names = [p.participant_name for p in participants]
                return "、".join(names)
            return application.participants[0].participant_name if application.participants else ""
        if field_name == 'contact_name':
            return _norm(getattr(application, 'contact_name', '') or '')
        if field_name == 'category_task':
            return _norm(f"{application.category} - {application.task}")
        if field_name == 'award_level':
            return _norm(application.award_level or "")
        if field_name == 'education_level':
            v = _norm(getattr(application, 'education_level', '') or '')
            try:
                return v[:-1] if isinstance(v, str) and v.endswith('组') else v
            except Exception:
                return v
        return _norm(getattr(application, field_name, '') or '')

    def draw_text(self, canvas_obj, text, x, y, width, font_name=None, font_size=12, align='center'):
        if text is None:
            return
        try:
            import math
            if isinstance(text, float) and math.isnan(text):
                return
        except Exception:
            pass
        text = str(text)
        if text.strip().lower() == 'nan':
            return
        font_name = self.resolve_font_name(font_name)
        font_size = float(font_size)
        canvas_obj.setFont(font_name, font_size)

        def _get_char_space_pt() -> float:
            try:
                # reportlab stores this on canvas as a private attr
                for k in ('_charSpace', 'charSpace'):
                    v = getattr(canvas_obj, k, None)
                    if v is not None:
                        return float(v)
            except Exception:
                pass
            return 0.0

        def _effective_text_width(t: str) -> float:
            base = float(canvas_obj.stringWidth(t, font_name, font_size))
            cs = _get_char_space_pt()
            n = len(t) if isinstance(t, str) else 0
            if n <= 1 or cs == 0:
                return base
            return base + cs * float(n - 1)

        def _draw_text_with_glyph_dx(*, t: str, x0: float, y0: float, box_w: float, a: str, glyph_dx_pt: dict):
            cs = _get_char_space_pt()
            chars = list(t)
            if not chars:
                return

            # base (unshifted) text width includes char spacing
            base_w = 0.0
            for idx, ch in enumerate(chars):
                base_w += float(canvas_obj.stringWidth(ch, font_name, font_size))
                if idx < len(chars) - 1:
                    base_w += cs

            if a == 'left':
                start_shift = 0.0
            elif a == 'right':
                start_shift = float(box_w) - float(base_w)
            else:
                start_shift = (float(box_w) - float(base_w)) / 2.0

            adv = 0.0
            for idx, ch in enumerate(chars):
                dx = float(glyph_dx_pt.get(ch, 0.0) or 0.0)
                canvas_obj.drawString(float(x0) + float(start_shift) + float(adv) + float(dx), float(y0), ch)
                adv += float(canvas_obj.stringWidth(ch, font_name, font_size))
                if idx < len(chars) - 1:
                    adv += cs

        glyph_dx = getattr(self, '_current_glyph_dx', None)
        if isinstance(glyph_dx, dict) and glyph_dx:
            _draw_text_with_glyph_dx(
                t=text,
                x0=float(x),
                y0=float(y),
                box_w=float(width),
                a=str(align or 'center'),
                glyph_dx_pt=glyph_dx,
            )
            return

        if align == 'left':
            canvas_obj.drawString(x, y, text)
            return
        if align == 'right':
            text_width = _effective_text_width(text)
            canvas_obj.drawString(x + width - text_width, y, text)
            return

        text_width = _effective_text_width(text)
        centered_x = x + (width - text_width) / 2
        canvas_obj.drawString(centered_x, y, text)

    def draw_wrapped_text(self, canvas_obj, text, x, y, width, font_name=None, font_size=12, align='left', line_height=None, max_lines=None, direction='up'):
        if text is None:
            return
        text = str(text)
        font_name = self.resolve_font_name(font_name)
        font_size = float(font_size)
        if line_height is None:
            line_height = font_size * 1.25

        canvas_obj.setFont(font_name, font_size)

        def _get_char_space_pt() -> float:
            try:
                for k in ('_charSpace', 'charSpace'):
                    v = getattr(canvas_obj, k, None)
                    if v is not None:
                        return float(v)
            except Exception:
                pass
            return 0.0

        def _effective_text_width(t: str) -> float:
            base = float(canvas_obj.stringWidth(t, font_name, font_size))
            cs = _get_char_space_pt()
            n = len(t) if isinstance(t, str) else 0
            if n <= 1 or cs == 0:
                return base
            return base + cs * float(n - 1)

        tokens, joiner = self._split_wrap_tokens(text)
        if not tokens:
            return

        lines = []
        current = ''
        for token in tokens:
            candidate = token if not current else f"{current}{joiner}{token}"
            if _effective_text_width(candidate) <= width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = token
        if current:
            lines.append(current)

        if max_lines is not None:
            lines = lines[: int(max_lines)]

        for i, line in enumerate(lines):
            dy = (i * line_height) if direction == 'up' else (-i * line_height)
            self.draw_text(canvas_obj, line, x, y + dy, width, font_name=font_name, font_size=font_size, align=align)

    def _split_wrap_tokens(self, text):
        text = (text or '').strip()
        if not text:
            return [], '、'
        if '、' in text:
            tokens = [t.strip() for t in text.split('、') if t.strip()]
            return tokens, '、'
        if '，' in text:
            tokens = [t.strip() for t in text.split('，') if t.strip()]
            return tokens, '，'
        if ',' in text:
            tokens = [t.strip() for t in text.split(',') if t.strip()]
            return tokens, ', '
        if ' ' in text:
            tokens = [t.strip() for t in text.split(' ') if t.strip()]
            return tokens, ' '
        return [text], '、'

    def calculate_font_size(self, text, max_width, max_font_size=24, min_font_size=8, font_name=None):
        """
        根据文字长度和文本框宽度动态计算字号
        如果文字过长，自动缩小字号
        """
        if not text:
            return max_font_size
        
        # 从最大字号开始测试
        font_name = self.resolve_font_name(font_name)
        max_font_size = int(max_font_size)
        min_font_size = int(min_font_size)
        for font_size in range(max_font_size, min_font_size - 1, -1):
            # 设置字体并计算文字宽度
            canvas_obj = canvas.Canvas(io.BytesIO(), pagesize=A4)
            canvas_obj.setFont(font_name, font_size)
            text_width = canvas_obj.stringWidth(text, font_name, font_size)
            canvas_obj.save()
            
            # 如果文字宽度不超过最大宽度，返回当前字号
            if text_width <= max_width:
                return font_size
        
        # 如果最小字号仍然放不下，返回最小字号
        return min_font_size

    def draw_centered_text(self, canvas_obj, text, x, y, width, max_font_size=24, min_font_size=8, font_name=None):
        """
        在指定位置居中绘制文字，字号自适应
        """
        if not text:
            return
        
        # 计算合适的字号
        font_name = self.resolve_font_name(font_name)

        font_size = self.calculate_font_size(text, width, max_font_size, min_font_size, font_name=font_name)
        
        # 设置字体
        canvas_obj.setFont(font_name, font_size)
        
        # 计算文字宽度
        text_width = canvas_obj.stringWidth(text, font_name, font_size)
        
        # 计算居中位置
        centered_x = x + (width - text_width) / 2
        
        # 绘制文字
        canvas_obj.drawString(centered_x, y, text)

    def generate_certificate(self, application, template_config):
        """
        生成证书PDF
        :param application: Application对象
        :param template_config: 证书模板配置（字典格式）
        """
        # 创建PDF文件
        buffer = io.BytesIO()

        # Optional: use background PNG native size as PDF pagesize to avoid distortion.
        page_size = A4
        background_image = template_config.get('background_image')
        use_background_size = bool(template_config.get('use_background_size'))
        bg_path = None
        if background_image:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            bg_path = os.path.join(base_dir, background_image) if not os.path.isabs(background_image) else background_image
            if use_background_size and bg_path and os.path.exists(bg_path):
                try:
                    img_probe = ImageReader(bg_path)
                    iw_px, ih_px = img_probe.getSize()
                    page_size = (self.px_to_pt(iw_px), self.px_to_pt(ih_px))
                except Exception:
                    page_size = A4

        canvas_obj = canvas.Canvas(buffer, pagesize=page_size)
        old_page_w, old_page_h = self.page_width, self.page_height
        try:
            self.page_width, self.page_height = page_size

            # 绘制背景图（可选）
            if bg_path and os.path.exists(bg_path):
                try:
                    img = ImageReader(bg_path)
                    canvas_obj.drawImage(img, 0, 0, width=self.page_width, height=self.page_height, mask='auto')
                except Exception:
                    pass

            # Optional stamp overlay
            try:
                coord_unit = str(template_config.get('coord_unit', 'mm') or 'mm').lower()
                y_origin = str(template_config.get('y_origin', 'bottom') or 'bottom').lower()

                def _to_pt(v):
                    if v is None:
                        return 0.0
                    if coord_unit == 'px':
                        return float(self.px_to_pt(v))
                    return float(v) * mm

                def _resolve_path(p):
                    if not p:
                        return ''
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    return os.path.join(base_dir, p) if not os.path.isabs(str(p)) else str(p)

                def _resolve_existing_path(primary_path, fallback_images=None):
                    resolved = _resolve_path(primary_path)
                    if resolved and os.path.exists(resolved):
                        return resolved
                    if isinstance(fallback_images, (list, tuple)):
                        for fp in fallback_images:
                            rr = _resolve_path(fp)
                            if rr and os.path.exists(rr):
                                return rr
                    return ''

                def _draw_one_stamp(*, path, x, y, width_pt=None, height_pt=None, y_anchor='bottom', keep_aspect=False):
                    stamp_path = _resolve_path(path)
                    if not stamp_path or not os.path.exists(stamp_path):
                        return

                    stamp_img = ImageReader(stamp_path)
                    w_pt = width_pt
                    h_pt = height_pt
                    if w_pt is None or h_pt is None:
                        iw_px, ih_px = stamp_img.getSize()
                        if w_pt is None:
                            w_pt = self.px_to_pt(iw_px)
                        if h_pt is None:
                            h_pt = self.px_to_pt(ih_px)

                    draw_w_pt = float(w_pt)
                    draw_h_pt = float(h_pt)
                    draw_x = float(x)
                    y_anchor = str(y_anchor or 'bottom').lower()
                    if keep_aspect and width_pt is not None and height_pt is not None:
                        try:
                            iw_px, ih_px = stamp_img.getSize()
                            iw_pt = float(self.px_to_pt(iw_px))
                            ih_pt = float(self.px_to_pt(ih_px))
                            if iw_pt > 0 and ih_pt > 0 and float(w_pt) > 0 and float(h_pt) > 0:
                                s = min(float(w_pt) / iw_pt, float(h_pt) / ih_pt)
                                draw_w_pt = iw_pt * s
                                draw_h_pt = ih_pt * s
                        except Exception:
                            draw_w_pt = float(w_pt)
                            draw_h_pt = float(h_pt)

                        if y_anchor == 'center':
                            box_bottom = float(y) - float(h_pt) / 2.0
                        else:
                            box_bottom = float(y)

                        draw_x = float(x) + (float(w_pt) - float(draw_w_pt)) / 2.0
                        sy = box_bottom + (float(h_pt) - float(draw_h_pt)) / 2.0
                        canvas_obj.drawImage(stamp_img, float(draw_x), float(sy), width=float(draw_w_pt), height=float(draw_h_pt), mask='auto')
                        return

                    sy = float(y)
                    if y_anchor == 'center':
                        sy = sy - float(h_pt) / 2.0

                    canvas_obj.drawImage(stamp_img, float(x), float(sy), width=float(w_pt), height=float(h_pt), mask='auto')

                # 1) New: stamp_repeat (centered symmetric)
                stamp_repeat = template_config.get('stamp_repeat') or None
                if isinstance(stamp_repeat, dict) and stamp_repeat.get('image'):
                    local_unit = str(stamp_repeat.get('unit', coord_unit) or coord_unit).lower()
                    local_y_origin = str(stamp_repeat.get('y_origin', y_origin) or y_origin).lower()

                    def _to_pt_local(v):
                        if v is None:
                            return 0.0
                        if local_unit == 'px':
                            return float(self.px_to_pt(v))
                        return float(v) * mm

                    count = int(stamp_repeat.get('count', 1) or 1)
                    count = max(1, min(count, 20))

                    sw = stamp_repeat.get('width', template_config.get('stamp_width'))
                    sh = stamp_repeat.get('height', template_config.get('stamp_height'))
                    sw_pt = _to_pt_local(sw) if sw is not None else None
                    sh_pt = _to_pt_local(sh) if sh is not None else None

                    gap = stamp_repeat.get('gap', 0)
                    gap_pt = _to_pt_local(gap) if gap is not None else 0.0

                    sy_raw = float(stamp_repeat.get('y', template_config.get('stamp_y', 0)) or 0)
                    sy_anchor = str(stamp_repeat.get('y_anchor', template_config.get('stamp_y_anchor', 'bottom')) or 'bottom').lower()
                    if local_unit == 'px' and local_y_origin == 'top':
                        sy = self._px_top_to_pt_bottom(sy_raw, self.page_height)
                    else:
                        sy = _to_pt_local(sy_raw)

                    total_w = (float(sw_pt or 0) * count) + (float(gap_pt) * (count - 1))
                    start_x = (float(self.page_width) - float(total_w)) / 2.0

                    for i in range(count):
                        sx = start_x + i * (float(sw_pt or 0) + float(gap_pt))
                        keep_aspect = bool(stamp_repeat.get('keep_aspect') or template_config.get('stamp_keep_aspect'))
                        _draw_one_stamp(
                            path=stamp_repeat.get('image'),
                            x=sx,
                            y=sy,
                            width_pt=sw_pt,
                            height_pt=sh_pt,
                            y_anchor=sy_anchor
                            , keep_aspect=keep_aspect
                        )

                # 2) New: stamp_images list (each item may have own x/y)
                stamp_images = template_config.get('stamp_images') or []
                if isinstance(stamp_images, list) and stamp_images:
                    for item in stamp_images:
                        try:
                            fallback_images = None
                            if isinstance(item, dict):
                                if item.get('fallback_image'):
                                    fallback_images = [item.get('fallback_image')]
                                elif item.get('fallback_images'):
                                    fallback_images = item.get('fallback_images')

                            path = item.get('image') or item.get('path')
                            stamp_path = _resolve_existing_path(path, fallback_images=fallback_images)
                            if not stamp_path:
                                continue

                            local_unit = str(item.get('unit', coord_unit) or coord_unit).lower()
                            local_y_origin = str(item.get('y_origin', y_origin) or y_origin).lower()

                            def _to_pt_local(v):
                                if v is None:
                                    return 0.0
                                if local_unit == 'px':
                                    return float(self.px_to_pt(v))
                                return float(v) * mm

                            sw = item.get('width', template_config.get('stamp_width'))
                            sh = item.get('height', template_config.get('stamp_height'))
                            sw_pt = _to_pt_local(sw) if sw is not None else None
                            sh_pt = _to_pt_local(sh) if sh is not None else None

                            stamp_center_x = bool(item.get('center_x', template_config.get('stamp_center_x')))
                            if stamp_center_x:
                                base_sx = (float(self.page_width) - float(sw_pt or 0)) / 2.0
                                dx = _to_pt_local(item.get('x', 0))
                                sx = float(base_sx) + float(dx)
                            else:
                                sx = _to_pt_local(item.get('x', template_config.get('stamp_x', 0)))

                            sy_raw = float(item.get('y', template_config.get('stamp_y', 0)) or 0)
                            sy_anchor = str(item.get('y_anchor', template_config.get('stamp_y_anchor', 'bottom')) or 'bottom').lower()
                            if local_unit == 'px' and local_y_origin == 'top':
                                sy = self._px_top_to_pt_bottom(sy_raw, self.page_height)
                            else:
                                sy = _to_pt_local(sy_raw)

                            keep_aspect = bool(item.get('keep_aspect') or template_config.get('stamp_keep_aspect'))
                            _draw_one_stamp(
                                path=stamp_path,
                                x=sx,
                                y=sy,
                                width_pt=sw_pt,
                                height_pt=sh_pt,
                                y_anchor=sy_anchor,
                                keep_aspect=keep_aspect,
                            )

                        except Exception:
                            continue

                # 3) Backward compat: single stamp_image
                stamp_image = template_config.get('stamp_image')
                if stamp_image:
                    sw = template_config.get('stamp_width')
                    sh = template_config.get('stamp_height')
                    sw_pt = _to_pt(sw) if sw is not None else None
                    sh_pt = _to_pt(sh) if sh is not None else None

                    stamp_center_x = bool(template_config.get('stamp_center_x'))
                    if stamp_center_x:
                        sx = (float(self.page_width) - float(sw_pt or 0)) / 2.0
                    else:
                        sx = _to_pt(template_config.get('stamp_x', 0))

                    sy_raw = float(template_config.get('stamp_y', 0) or 0)
                    sy_anchor = str(template_config.get('stamp_y_anchor', 'bottom') or 'bottom').lower()
                    if coord_unit == 'px' and y_origin == 'top':
                        sy = self._px_top_to_pt_bottom(sy_raw, self.page_height)
                    else:
                        sy = _to_pt(sy_raw)

                    keep_aspect = bool(template_config.get('stamp_keep_aspect'))
                    _draw_one_stamp(path=stamp_image, x=sx, y=sy, width_pt=sw_pt, height_pt=sh_pt, y_anchor=sy_anchor, keep_aspect=keep_aspect)
            except Exception:
                pass

            debug_grid = template_config.get('debug_grid')
            if debug_grid:
                try:
                    step_px = float(debug_grid.get('step_px', 100))
                    alpha = float(debug_grid.get('alpha', 0.25))
                    lw = float(debug_grid.get('line_width', 0.5))
                    label = bool(debug_grid.get('label', True))
                    label_font_size = float(debug_grid.get('label_font_size', 7))
                    self.draw_debug_grid(
                        canvas_obj,
                        step_px=step_px,
                        color=Color(1, 0, 0, alpha=alpha),
                        line_width=lw,
                        label=label,
                        label_font_size=label_font_size,
                    )
                except Exception:
                    pass

            debug_canvas_grid = template_config.get('debug_canvas_grid')
            if debug_canvas_grid:
                try:
                    step = float(debug_canvas_grid.get('step', 50)) * mm
                    xs = [i for i in self._frange(0, self.page_width, step)]
                    ys = [i for i in self._frange(0, self.page_height, step)]
                    canvas_obj.saveState()
                    canvas_obj.setStrokeColor(Color(1, 0, 0, alpha=float(debug_canvas_grid.get('alpha', 0.15))))
                    canvas_obj.setLineWidth(float(debug_canvas_grid.get('line_width', 0.3)))
                    canvas_obj.grid(xs, ys)
                    canvas_obj.restoreState()
                except Exception:
                    pass

            # 设置背景色（可选）
            if template_config.get('background_color'):
                canvas_obj.setFillColor(template_config['background_color'])
                canvas_obj.rect(0, 0, self.page_width, self.page_height, fill=1)

            # 设置文字颜色
            text_color = template_config.get('text_color', black)
            canvas_obj.setFillColor(text_color)

            # 新版：按texts渲染（支持固定文本/动态字段/对齐/字号）
            if template_config.get('texts'):
                coord_unit = str(template_config.get('coord_unit', 'mm') or 'mm').lower()
                y_origin = str(template_config.get('y_origin', 'bottom') or 'bottom').lower()
                global_y_offset = float(template_config.get('global_y_offset', 0)) * mm if coord_unit == 'mm' else self.px_to_pt(float(template_config.get('global_y_offset', 0) or 0))

                def _to_pt(v):
                    if v is None:
                        return 0.0
                    if coord_unit == 'px':
                        return float(self.px_to_pt(v))
                    return float(v) * mm

                debug_points = template_config.get('debug_points')
                for item in template_config.get('texts', []):
                    try:
                        width = _to_pt(item.get('width', 0))
                        x = _to_pt(item.get('x', 0))

                        raw_y = float(item.get('y', 0) or 0)
                        if coord_unit == 'px' and y_origin == 'top':
                            y = self._px_top_to_pt_bottom(raw_y, self.page_height)
                        else:
                            y = _to_pt(raw_y)

                        x_anchor = (item.get('x_anchor') or item.get('anchor') or 'left').lower()
                        if x_anchor == 'center':
                            x = x - (width / 2.0)
                        elif x_anchor == 'right':
                            x = x - width

                        y_offset_raw = float(item.get('y_offset', 0) or 0)
                        if coord_unit == 'px' and y_origin == 'top':
                            y = y + float(self.px_to_pt(y_offset_raw)) + global_y_offset
                        else:
                            y = y + _to_pt(y_offset_raw) + global_y_offset

                        align = item.get('align', 'center')
                        font = item.get('font')

                        # Optional: character spacing (tracking). Unit follows coord_unit.
                        _char_space_set = False
                        try:
                            if 'char_space' in item and item.get('char_space') is not None:
                                cs_raw = float(item.get('char_space') or 0)
                                if coord_unit == 'px':
                                    canvas_obj.setCharSpace(float(self.px_to_pt(cs_raw)))
                                else:
                                    canvas_obj.setCharSpace(float(cs_raw) * mm)
                                _char_space_set = True
                        except Exception:
                            _char_space_set = False

                        # Optional: per-glyph dx mapping (unit follows coord_unit)
                        _glyph_dx_prev = getattr(self, '_current_glyph_dx', None)
                        try:
                            glyph_dx_raw = item.get('glyph_dx')
                            if isinstance(glyph_dx_raw, dict) and glyph_dx_raw:
                                glyph_dx_pt = {}
                                for k, v in glyph_dx_raw.items():
                                    try:
                                        vv = float(v or 0)
                                    except Exception:
                                        vv = 0.0
                                    if coord_unit == 'px':
                                        glyph_dx_pt[str(k)] = float(self.px_to_pt(vv))
                                    else:
                                        glyph_dx_pt[str(k)] = float(vv) * mm
                                setattr(self, '_current_glyph_dx', glyph_dx_pt)
                            else:
                                setattr(self, '_current_glyph_dx', None)
                        except Exception:
                            setattr(self, '_current_glyph_dx', None)

                        if debug_points or item.get('debug_point'):
                            box_h = float(item.get('debug_box_height', 10))
                            box_shift = float(item.get('debug_box_y_shift', 0)) * mm
                            self.draw_debug_box(canvas_obj, x, y, width, height=box_h, y_shift=box_shift)

                        if item.get('field'):
                            txt = self.get_field_text(application, item.get('field'))
                        else:
                            txt = item.get('text', '')

                        if item.get('auto_size'):
                            max_size = self.px_to_pt(item.get('max_font_size', 16))
                            min_size = self.px_to_pt(item.get('min_font_size', 12))
                            self.draw_centered_text(canvas_obj, txt, x, y, width, max_size, min_size, font_name=font)
                        else:
                            size = self.px_to_pt(item.get('font_size', item.get('max_font_size', 16)))
                            if item.get('wrap'):
                                line_height = self.px_to_pt(item.get('line_height', None))
                                self.draw_wrapped_text(
                                    canvas_obj,
                                    txt,
                                    x,
                                    y,
                                    width,
                                    font_name=font,
                                    font_size=size,
                                    align=align,
                                    line_height=line_height,
                                    max_lines=item.get('max_lines', None),
                                    direction=item.get('direction', 'up')
                                )
                            else:
                                self.draw_text(canvas_obj, txt, x, y, width, font_name=font, font_size=size, align=align)

                        if _char_space_set:
                            try:
                                canvas_obj.setCharSpace(0)
                            except Exception:
                                pass

                        try:
                            setattr(self, '_current_glyph_dx', _glyph_dx_prev)
                        except Exception:
                            pass
                    except Exception:
                        continue

                debug_grid_overlay = template_config.get('debug_grid_overlay')
                if debug_grid_overlay:
                    try:
                        if isinstance(debug_grid_overlay, dict):
                            self.draw_debug_grid_overlay(canvas_obj, debug_grid_overlay)
                        else:
                            self.draw_debug_grid_overlay(canvas_obj, {})
                    except Exception:
                        pass

                canvas_obj.save()
                buffer.seek(0)
                return buffer.getvalue()

            # Legacy blocks (mm-based). Used only when template_config does not use 'texts'.
            # 绘制证书标题
            if 'title' in template_config:
                title_config = template_config['title']
                title_font = title_config.get('font')
                self.draw_centered_text(
                    canvas_obj,
                    title_config['text'],
                    title_config['x'] * mm,
                    title_config['y'] * mm,
                    title_config['width'] * mm,
                    self.px_to_pt(title_config.get('max_font_size', 32)),
                    self.px_to_pt(title_config.get('min_font_size', 16)),
                    font_name=title_font
                )

            # 绘制获奖者姓名
            if 'name' in template_config:
                name_config = template_config['name']
                name_font = name_config.get('font')

                # 处理多人项目的姓名显示
                if application.participant_count > 1:
                    participants = sorted(application.participants, key=lambda p: p.seq_no)
                    names = [p.participant_name for p in participants]
                    name_text = "、".join(names)
                else:
                    name_text = application.participants[0].participant_name if application.participants else ""

                self.draw_centered_text(
                    canvas_obj,
                    name_text,
                    name_config['x'] * mm,
                    name_config['y'] * mm,
                    name_config['width'] * mm,
                    self.px_to_pt(name_config.get('max_font_size', 24)),
                    self.px_to_pt(name_config.get('min_font_size', 12)),
                    font_name=name_font
                )

            # 绘制学校名称
            if 'school' in template_config:
                school_config = template_config['school']
                school_font = school_config.get('font')
                self.draw_centered_text(
                    canvas_obj,
                    application.school_name,
                    school_config['x'] * mm,
                    school_config['y'] * mm,
                    school_config['width'] * mm,
                    self.px_to_pt(school_config.get('max_font_size', 20)),
                    self.px_to_pt(school_config.get('min_font_size', 10)),
                    font_name=school_font
                )

            # 绘制项目名称
            if 'project' in template_config:
                project_config = template_config['project']
                project_font = project_config.get('font')
                project_text = f"{application.category} - {application.task}"
                self.draw_centered_text(
                    canvas_obj,
                    project_text,
                    project_config['x'] * mm,
                    project_config['y'] * mm,
                    project_config['width'] * mm,
                    self.px_to_pt(project_config.get('max_font_size', 18)),
                    self.px_to_pt(project_config.get('min_font_size', 10)),
                    font_name=project_font
                )

            # 绘制获奖等级
            if 'award' in template_config:
                award_config = template_config['award']
                award_font = award_config.get('font')
                self.draw_centered_text(
                    canvas_obj,
                    application.award_level or "",
                    award_config['x'] * mm,
                    award_config['y'] * mm,
                    award_config['width'] * mm,
                    self.px_to_pt(award_config.get('max_font_size', 22)),
                    self.px_to_pt(award_config.get('min_font_size', 12)),
                    font_name=award_font
                )

            # 完成PDF绘制
            canvas_obj.save()
            buffer.seek(0)
            return buffer.getvalue()
        finally:
            self.page_width, self.page_height = old_page_w, old_page_h
    
    def create_default_template(self, category, award_level):
        """
        创建默认的证书模板配置
        """
        return {
            "background_image": None,
            "background_color": None,
            "text_color": black,
            "title": {
                "text": "获奖证书",
                "x": 50,
                "y": 200,
                "width": 100,
                "max_font_size": 32,
                "min_font_size": 16,
                "font": "黑体"
            },
            "name": {
                "x": 50,
                "y": 160,
                "width": 100,
                "max_font_size": 24,
                "min_font_size": 12,
                "font": "宋体"
            },
            "school": {
                "x": 50,
                "y": 130,
                "width": 100,
                "max_font_size": 20,
                "min_font_size": 10,
                "font": "宋体"
            },
            "project": {
                "x": 50,
                "y": 100,
                "width": 100,
                "max_font_size": 18,
                "min_font_size": 10,
                "font": "宋体"
            },
            "award": {
                "x": 50,
                "y": 70,
                "width": 100,
                "max_font_size": 22,
                "min_font_size": 12,
                "font": "华文楷体"
            }
        }

    def _frange(self, start, stop, step):
        if step <= 0:
            return
        x = float(start)
        stop = float(stop)
        step = float(step)
        while x <= stop + 1e-9:
            yield x
            x += step
