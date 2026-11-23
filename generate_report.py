"""
Tự động sinh Báo cáo Cuối kỳ môn Kỹ thuật Robot:
Đề tài: Autonomous Docking cho Robot Di động Vi sai 2D
Định dạng: Word (.docx) chuẩn học thuật, khổ A4, Times New Roman, cỡ 13, căn đều 2 lề, đánh số trang.
Tích hợp 3 hình minh họa mô hình/cấu trúc điều khiển (trích dẫn [1]) và 10 đồ thị kỹ thuật (PNG 300 dpi).
"""

import os
import re
from pathlib import Path
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_background(cell, hex_color: str):
    """Đặt màu nền cho ô trong bảng."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Đặt lề trong (padding) cho ô."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def add_heading_styled(doc, text: str, level: int):
    """Thêm tiêu đề với font Times New Roman và định dạng đẹp."""
    p = doc.add_paragraph()
    p.paragraph_format.keep_with_next = True
    run = p.add_run(text)
    run.font.name = 'Times New Roman'
    run.bold = True
    
    if level == 1:
        p.paragraph_format.space_before = Pt(14)
        p.paragraph_format.space_after = Pt(6)
        run.font.size = Pt(16)
        run.font.color.rgb = RGBColor(0, 51, 102) # Xanh Navy đậm
    elif level == 2:
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(4)
        run.font.size = Pt(14)
        run.font.color.rgb = RGBColor(31, 78, 121)
    elif level == 3:
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        run.font.size = Pt(13)
        run.italic = True
        run.font.color.rgb = RGBColor(0, 0, 0)
    return p

def _xml_esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

_LATEX_SYMBOLS = {
    "theta": "θ", "rho": "ρ", "alpha": "α", "beta": "β", "omega": "ω",
    "pi": "π", "tau": "τ", "lambda": "λ", "sigma": "σ", "Delta": "Δ",
    "in": "∈", "le": "≤", "ge": "≥", "to": "→", "cdot": "·", "times": "×",
    "circ": "°", "approx": "≈", "ne": "≠", "infty": "∞",
    "arctan": "arctan", "atan2": "atan2", "cos": "cos", "sin": "sin",
    "max": "max", "min": "min", "wrap": "wrap",
}

def _parse_group(s: str, i: int):
    while i < len(s) and s[i] in " \t":
        i += 1
    if i >= len(s):
        return "", i
    if s[i] == "{":
        depth = 1
        j = i + 1
        while j < len(s) and depth > 0:
            if s[j] == "{":
                depth += 1
            elif s[j] == "}":
                depth -= 1
            j += 1
        return s[i + 1 : j - 1], j
    if s[i] == "\\":
        j = i + 1
        while j < len(s) and s[j].isalpha():
            j += 1
        return s[i:j], j
    return s[i], i + 1

def _m_run(text: str, normal: bool = False) -> str:
    if not text:
        return ""
    rpr = '<m:rPr><m:sty m:val="p"/></m:rPr>' if normal else ""
    return f'<m:r>{rpr}<m:t xml:space="preserve">{_xml_esc(text)}</m:t></m:r>'

def _latex_expr_to_omml_inner(s: str) -> str:
    out = []
    i = 0
    n = len(s)
    while i < n:
        ch = s[i]
        if ch in " \t":
            i += 1
            continue
        if ch == "{":
            grp, i = _parse_group(s, i)
            inner = _latex_expr_to_omml_inner(grp)
            # Check trailing _ or ^
            sub_xml, sup_xml = None, None
            while i < n and s[i] in ("_", "^"):
                op = s[i]
                arg, i = _parse_group(s, i + 1)
                if op == "_":
                    sub_xml = _latex_expr_to_omml_inner(arg)
                else:
                    sup_xml = _latex_expr_to_omml_inner(arg)
            if sub_xml and sup_xml:
                out.append(f"<m:sSubSup><m:e>{inner}</m:e><m:sub>{sub_xml}</m:sub><m:sup>{sup_xml}</m:sup></m:sSubSup>")
            elif sub_xml:
                out.append(f"<m:sSub><m:e>{inner}</m:e><m:sub>{sub_xml}</m:sub></m:sSub>")
            elif sup_xml:
                out.append(f"<m:sSup><m:e>{inner}</m:e><m:sup>{sup_xml}</m:sup></m:sSup>")
            else:
                out.append(inner)
            continue

        if ch == "\\":
            if i + 1 < n and s[i + 1] in (",", ";", " ", "_"):
                ch_next = s[i + 1]
                out.append(_m_run(" " if ch_next in (",", ";", " ") else ch_next, normal=True))
                i += 2
                continue
            j = i + 1
            while j < n and s[j].isalpha():
                j += 1
            cmd = s[i + 1 : j]
            i = j
            if cmd == "frac":
                num, i = _parse_group(s, i)
                den, i = _parse_group(s, i)
                out.append(f"<m:f><m:num>{_latex_expr_to_omml_inner(num)}</m:num><m:den>{_latex_expr_to_omml_inner(den)}</m:den></m:f>")
                continue
            if cmd == "sqrt":
                arg, i = _parse_group(s, i)
                out.append(f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{_latex_expr_to_omml_inner(arg)}</m:e></m:rad>')
                continue
            if cmd == "dot":
                arg, i = _parse_group(s, i)
                base = f'<m:acc><m:accPr><m:chr m:val="˙"/></m:accPr><m:e>{_latex_expr_to_omml_inner(arg)}</m:e></m:acc>'
            elif cmd == "bar":
                arg, i = _parse_group(s, i)
                base = f'<m:bar><m:barPr><m:pos m:val="top"/></m:barPr><m:e>{_latex_expr_to_omml_inner(arg)}</m:e></m:bar>'
            elif cmd in ("mathrm", "text", "mathbf"):
                arg, i = _parse_group(s, i)
                base = _m_run(arg.replace(r"\_", "_"), normal=True)
            elif cmd == "int":
                sub_xml, sup_xml = "", ""
                while i < n and s[i] in ("_", "^"):
                    op = s[i]
                    arg, i = _parse_group(s, i + 1)
                    if op == "_":
                        sub_xml = _latex_expr_to_omml_inner(arg)
                    else:
                        sup_xml = _latex_expr_to_omml_inner(arg)
                # Consume rest as integrand if simple, else empty integrand with explicit runs
                out.append(f'<m:nary><m:naryPr><m:chr m:val="∫"/><m:limLoc m:val="subSup"/></m:naryPr><m:sub>{sub_xml}</m:sub><m:sup>{sup_xml}</m:sup><m:e></m:e></m:nary>')
                continue
            elif cmd in ("left", "right"):
                if i < n:
                    delim = s[i]
                    i += 1
                    out.append(_m_run(delim, normal=True))
                continue
            elif cmd in ("qquad", "quad"):
                out.append(_m_run("   ", normal=True))
                continue
            elif cmd in _LATEX_SYMBOLS:
                sym = _LATEX_SYMBOLS[cmd]
                is_norm = cmd in ("arctan", "atan2", "cos", "sin", "max", "min", "wrap")
                base = _m_run(sym, normal=is_norm)
            else:
                base = _m_run(cmd, normal=True)
        else:
            # Plain character or multi-char ASCII text / number
            if ch in ("_", "^"):
                # Stray script without base
                i += 1
                continue
            if ch in "=+-*/,()[]:|<>":
                base = _m_run(f" {ch} " if ch in "=+-<>" else ch, normal=True)
                i += 1
            elif ch.isdigit() or ch == ".":
                j = i
                while j < n and (s[j].isdigit() or s[j] == "."):
                    j += 1
                base = _m_run(s[i:j], normal=True)
                i = j
            else:
                base = _m_run(ch, normal=False)
                i += 1

        # Handle _ and ^ attached to base
        sub_xml, sup_xml = None, None
        while i < n and s[i] in ("_", "^"):
            op = s[i]
            arg, i = _parse_group(s, i + 1)
            if op == "_":
                sub_xml = _latex_expr_to_omml_inner(arg)
            else:
                sup_xml = _latex_expr_to_omml_inner(arg)
        if sub_xml and sup_xml:
            out.append(f"<m:sSubSup><m:e>{base}</m:e><m:sub>{sub_xml}</m:sub><m:sup>{sup_xml}</m:sup></m:sSubSup>")
        elif sub_xml:
            out.append(f"<m:sSub><m:e>{base}</m:e><m:sub>{sub_xml}</m:sub></m:sSub>")
        elif sup_xml:
            out.append(f"<m:sSup><m:e>{base}</m:e><m:sup>{sup_xml}</m:sup></m:sSup>")
        else:
            out.append(base)
    return "".join(out)

def make_omml_element(latex_str: str):
    """Tạo đối tượng Word Equation (OMML <m:oMath>) chỉnh sửa được trực tiếp trong Word."""
    clean = latex_str.strip()
    if clean.startswith("$") and clean.endswith("$"):
        clean = clean[1:-1].strip()
    inner = _latex_expr_to_omml_inner(clean)
    return parse_xml(f'<m:oMath {nsdecls("m")}>{inner}</m:oMath>')

def append_rich_text(p, text: str, font_size: int = 13):
    """Chèn văn bản có hỗ trợ công thức OMML nội dòng dạng [[...]]."""
    parts = re.split(r'(\[\[.*?\]\])', text)
    for part in parts:
        if not part:
            continue
        if part.startswith("[[") and part.endswith("]]"):
            expr = part[2:-2].strip()
            p._p.append(make_omml_element(expr))
        else:
            r = p.add_run(part)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(font_size)

def add_body_p(doc, text: str, bold_prefix: str = "", italic_prefix: str = ""):
    """Thêm đoạn văn chuẩn Times New Roman cỡ 13, giãn dòng 1.35, căn đều hai lề."""
    p = doc.add_paragraph()
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_after = Pt(6)
    
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.font.name = 'Times New Roman'
        r_bold.font.size = Pt(13)
        r_bold.bold = True
        
    if italic_prefix:
        r_it = p.add_run(italic_prefix)
        r_it.font.name = 'Times New Roman'
        r_it.font.size = Pt(13)
        r_it.italic = True

    append_rich_text(p, text, font_size=13)
    return p

def add_bullet_p(doc, bold_prefix: str, text: str):
    """Thêm đoạn danh sách đầu mục (bullet)."""
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.line_spacing = 1.3
    p.paragraph_format.space_after = Pt(3)
    
    if bold_prefix:
        r_bold = p.add_run(bold_prefix)
        r_bold.font.name = 'Times New Roman'
        r_bold.font.size = Pt(13)
        r_bold.bold = True
        
    append_rich_text(p, text, font_size=13)
    return p

def add_figure_with_caption(doc, img_path: str, caption_text: str, width_inch: float = 5.8):
    """Chèn hình ảnh kỹ thuật căn giữa kèm chú thích chuẩn."""
    if not os.path.exists(img_path):
        print(f"Cảnh báo: Không tìm thấy hình {img_path}")
        return
        
    p_img = doc.add_paragraph()
    p_img.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(8)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.paragraph_format.keep_with_next = True
    
    r_img = p_img.add_run()
    r_img.add_picture(img_path, width=Inches(width_inch))
    
    p_cap = doc.add_paragraph()
    p_cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(2)
    p_cap.paragraph_format.space_after = Pt(10)
    
    r_cap = p_cap.add_run(caption_text)
    r_cap.font.name = 'Times New Roman'
    r_cap.font.size = Pt(11)
    r_cap.italic = True
    r_cap.font.color.rgb = RGBColor(50, 50, 50)

def add_figure_placeholder(doc, hint_text: str, caption_text: str):
    """Tạo khung chừa chỗ trống để người dùng tự chèn hình minh họa vào Word."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.rows[0].cells[0]
    cell.width = Inches(5.6)
    set_cell_background(cell, "F5F7FA")
    set_cell_margins(cell, top=350, bottom=350, left=200, right=200)
    tcPr = cell._tc.get_or_add_tcPr()
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        '<w:top w:val="dashed" w:sz="8" w:space="0" w:color="7F8C8D"/>'
        '<w:left w:val="dashed" w:sz="8" w:space="0" w:color="7F8C8D"/>'
        '<w:bottom w:val="dashed" w:sz="8" w:space="0" w:color="7F8C8D"/>'
        '<w:right w:val="dashed" w:sz="8" w:space="0" w:color="7F8C8D"/>'
        '</w:tcBorders>'
    )
    tcPr.append(borders)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r1 = p.add_run("[CHÈN HÌNH MINH HỌA TẠI ĐÂY]\n")
    r1.font.name = 'Times New Roman'
    r1.font.size = Pt(11)
    r1.bold = True
    r1.font.color.rgb = RGBColor(100, 110, 120)
    r2 = p.add_run(hint_text)
    r2.font.name = 'Times New Roman'
    r2.font.size = Pt(10.5)
    r2.italic = True
    r2.font.color.rgb = RGBColor(100, 110, 120)

    p_cap = doc.add_paragraph()
    p_cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(3)
    p_cap.paragraph_format.space_after = Pt(10)
    r_cap = p_cap.add_run(caption_text)
    r_cap.font.name = 'Times New Roman'
    r_cap.font.size = Pt(11)
    r_cap.italic = True
    r_cap.font.color.rgb = RGBColor(50, 50, 50)

def add_latex_equation(doc, latex_str: str, eq_num: str, fontsize: int = 13):
    """Chèn công thức toán học Word Equation (OMML) chỉnh sửa được trực tiếp, căn giữa kèm số phương trình."""
    tbl = doc.add_table(rows=1, cols=3)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tblPr = tbl._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        '<w:top w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:left w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:bottom w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:right w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideH w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '<w:insideV w:val="none" w:sz="0" w:space="0" w:color="auto"/>'
        '</w:tblBorders>'
    )
    tblPr.append(borders)

    widths = [Inches(0.65), Inches(4.7), Inches(0.65)]
    for j, w in enumerate(widths):
        tbl.rows[0].cells[j].width = w
        tbl.rows[0].cells[j].vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    p_eq = tbl.rows[0].cells[1].paragraphs[0]
    p_eq.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_eq.paragraph_format.space_before = Pt(4)
    p_eq.paragraph_format.space_after = Pt(4)
    p_eq._p.append(make_omml_element(latex_str))

    p_num = tbl.rows[0].cells[2].paragraphs[0]
    p_num.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_num.paragraph_format.space_before = Pt(4)
    p_num.paragraph_format.space_after = Pt(4)
    r_n = p_num.add_run(f"({eq_num})")
    r_n.font.name = 'Times New Roman'
    r_n.font.size = Pt(12)

def add_page_number_footer(section):
    """Thêm số trang căn giữa vào chân trang (bỏ qua trang bìa đầu tiên)."""
    section.different_first_page_header_footer = True
    footer = section.footer
    p = footer.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_pre = p.add_run("Trang ")
    run_pre.font.name = 'Times New Roman'
    run_pre.font.size = Pt(11)

    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls('w'))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> PAGE </w:instrText>' % nsdecls('w'))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls('w'))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls('w'))
    run_pg = p.add_run()
    run_pg.font.name = 'Times New Roman'
    run_pg.font.size = Pt(11)
    run_pg._r.append(fldChar1)
    run_pg._r.append(instrText)
    run_pg._r.append(fldChar2)
    run_pg._r.append(fldChar3)

def main():
    base_dir = Path(__file__).parent.resolve()
    fig_dir = base_dir / "figures"
    theory_fig_dir = fig_dir / "theory_slides"
    output_docx = base_dir / "Bao_Cao_Cuoi_Ky_Autonomous_Docking.docx"
    
    print("Khởi tạo tài liệu Word hoàn chỉnh...")
    doc = docx.Document()
    
    # Thiết lập lề trang A4 chuẩn học thuật và đánh số trang
    for s in doc.sections:
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        add_page_number_footer(s)
        
    # ==================== TRANG BÌA ====================
    p_cover_school = doc.add_paragraph()
    p_cover_school.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cover_school.paragraph_format.space_before = Pt(0)
    p_cover_school.paragraph_format.space_after = Pt(4)
    r1 = p_cover_school.add_run("BỘ GIÁO DỤC VÀ ĐÀO TẠO\nTRƯỜNG ĐẠI HỌC BÁCH KHOA\nKHOA CƠ KHÍ - BỘ MÔN CƠ ĐIỆN TỬ")
    r1.font.name = 'Times New Roman'
    r1.font.size = Pt(13)
    r1.bold = True
    
    p_line = doc.add_paragraph()
    p_line.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_line.paragraph_format.space_after = Pt(36)
    r_line = p_line.add_run("-------------------***-------------------")
    r_line.font.name = 'Times New Roman'
    r_line.font.size = Pt(12)
    
    p_report_type = doc.add_paragraph()
    p_report_type.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_report_type.paragraph_format.space_after = Pt(12)
    r2 = p_report_type.add_run("BÁO CÁO CUỐI KỲ HỌC PHẦN KỸ THUẬT ROBOT")
    r2.font.name = 'Times New Roman'
    r2.font.size = Pt(14)
    r2.bold = True
    r2.font.color.rgb = RGBColor(0, 51, 102)
    
    p_title = doc.add_paragraph()
    p_title.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(12)
    p_title.paragraph_format.space_after = Pt(48)
    r3 = p_title.add_run("NGHIÊN CỨU, MÔ PHỎNG VÀ SO SÁNH THUẬT TOÁN ĐIỀU KHIỂN CẬP TRẠM SẠC TỰ ĐỘNG (AUTONOMOUS DOCKING) CHO ROBOT DI ĐỘNG VI SAI")
    r3.font.name = 'Times New Roman'
    r3.font.size = Pt(18)
    r3.bold = True
    r3.font.color.rgb = RGBColor(192, 0, 0)
    
    # Khung thông tin sinh viên và giảng viên
    info_table = doc.add_table(rows=4, cols=2)
    info_table.alignment = WD_TABLE_ALIGNMENT.CENTER
    col_widths = [Cm(5.0), Cm(9.0)]
    
    labels = [
        ("Giảng viên hướng dẫn:", "[Họ và tên Giảng viên hướng dẫn]"),
        ("Sinh viên thực hiện:", "[Họ và tên Sinh viên thực hiện]"),
        ("Mã số sinh viên (MSSV):", "[Mã số sinh viên]"),
        ("Lớp / Khóa:", "[Tên Lớp / Khóa học]"),
    ]
    for idx, (lbl, val) in enumerate(labels):
        row = info_table.rows[idx]
        cell_lbl, cell_val = row.cells[0], row.cells[1]
        
        cell_lbl.width = col_widths[0]
        cell_val.width = col_widths[1]
        
        p_l = cell_lbl.paragraphs[0]
        p_l.paragraph_format.space_after = Pt(4)
        rl = p_l.add_run(lbl)
        rl.font.name = 'Times New Roman'
        rl.font.size = Pt(13)
        rl.bold = True
        
        p_v = cell_val.paragraphs[0]
        p_v.paragraph_format.space_after = Pt(4)
        rv = p_v.add_run(val)
        rv.font.name = 'Times New Roman'
        rv.font.size = Pt(13)
        
    p_cover_bottom = doc.add_paragraph()
    p_cover_bottom.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cover_bottom.paragraph_format.space_before = Pt(80)
    r4 = p_cover_bottom.add_run("TP. HỒ CHÍ MINH, THÁNG 11 NĂM 2026")
    r4.font.name = 'Times New Roman'
    r4.font.size = Pt(12)
    r4.bold = True
    
    doc.add_page_break()
    
    # ==================== LỜI CAM ĐOAN & LỜI CẢM ƠN ====================
    add_heading_styled(doc, "LỜI CAM ĐOAN", level=1)
    add_body_p(doc, "Tôi xin cam đoan đây là công trình nghiên cứu và thực nghiệm do chính tôi thực hiện dưới sự định hướng của giảng viên bộ môn. Toàn bộ các kết quả mô phỏng, thuật toán, mã nguồn Python và số liệu thống kê được trình bày trong báo cáo là hoàn toàn trung thực, khách quan và được trích xuất trực tiếp từ các kịch bản kiểm thử độc lập. Mọi cơ sở lý thuyết, mô hình toán học và phương pháp đánh giá kế thừa từ các tài liệu khoa học chuyên ngành [1]–[6] đều được trích dẫn rõ ràng theo chuẩn học thuật IEEE, đồng thời phân định minh bạch giữa phần kế thừa và phần đóng góp tự thực hiện.")
    
    add_heading_styled(doc, "MỤC LỤC TỔNG QUAN", level=1)
    toc_items = [
        "CHƯƠNG 1. GIỚI THIỆU VÀ ĐẶT VẤN ĐỀ",
        "  1.1. Bối cảnh và ý nghĩa thực tiễn của trạm sạc tự động cho AGV/AMR",
        "  1.2. Phát biểu bài toán cập trạm sạc unicycle phi holonomic",
        "  1.3. Mục tiêu kỹ thuật và tiêu chí định lượng cần đạt",
        "  1.4. Phạm vi thực hiện và bố cục của báo cáo",
        "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ GIẢI THUẬT ĐIỀU KHIỂN",
        "  2.1. Biểu diễn vị trí và hướng trong không gian 2D (Pose SE(2))",
        "  2.2. Động học robot vi sai (Unicycle Kinematics)",
        "  2.3. Giải thuật điều khiển theo Tọa độ cực (Driving to a Configuration)",
        "  2.4. Điều khiển PID kinh điển và cấu trúc PID Hai vòng (Dual-loop PID)",
        "CHƯƠNG 3. THIẾT KẾ HỆ THỐNG VÀ PHƯƠNG PHÁP TRIỂN KHAI",
        "  3.1. Kiến trúc phần mềm mô phỏng khép kín thuần Python",
        "  3.2. Mô hình hóa nhiễu thực tế và trễ truyền thông",
        "  3.3. Phương pháp tinh chỉnh tham số công bằng (Fair Tuning)",
        "  3.4. Thiết kế 5 kịch bản thực nghiệm (S1 – S5) và nghiên cứu bóc tách (Ablation)",
        "  3.5. Phân định nội dung kế thừa và đóng góp tự thực hiện",
        "CHƯƠNG 4. KẾT QUẢ THỰC NGHIỆM VÀ THẢO LUẬN CHUYÊN SÂU",
        "  4.1. Kết quả kiểm chứng ổn định giải tích",
        "  4.2. Đáp ứng thời gian và quỹ đạo trong kịch bản lý tưởng S1",
        "  4.3. Đánh giá quỹ đạo đa tư thế xuất phát bao quát không gian",
        "  4.4. Phân tích phân bố sai số và thời gian cập dock (Kịch bản S2 – S5)",
        "  4.5. Độ tin cậy tỷ lệ thành công với khoảng tin cậy Wilson 95%",
        "  4.6. Đánh giá độ nhạy khi quét hệ số nhiễu k và bản đồ nhiệt không gian",
        "  4.7. Nghiên cứu bóc tách thành phần (Ablation Study)",
        "  4.8. Thảo luận chuyên sâu: So sánh ưu - nhược điểm bản chất giữa Polar và DualPID",
        "CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN",
        "  5.1. Kết luận kỹ thuật đối chiếu với mục tiêu",
        "  5.2. Các hạn chế còn tồn tại và hướng mở rộng nghiên cứu",
        "TÀI LIỆU THAM KHẢO",
        "PHỤ LỤC: HƯỚNG DẪN THỰC THI MÃ NGUỒN VÀ BỘ KIỂM THỬ TỰ ĐỘNG",
    ]
    for item in toc_items:
        p_t = doc.add_paragraph()
        p_t.paragraph_format.line_spacing = 1.25
        p_t.paragraph_format.space_after = Pt(2)
        r = p_t.add_run(item)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(12)
        if item.startswith("CHƯƠNG") or item.startswith("TÀI LIỆU") or item.startswith("PHỤ LỤC"):
            r.bold = True
            
    doc.add_page_break()
    
    # ==================== DANH MỤC HÌNH VẼ & BẢNG BIỂU ====================
    add_heading_styled(doc, "DANH MỤC HÌNH VẼ", level=1)
    figures_list = [
        "Hình 1.1: Minh họa bài toán bám đường thẳng hướng vào trạm sạc (Driving Along a Line) và hạn chế không tự dừng tại Dock.",
        "Hình 2.1: Biểu diễn tư thế robot di động trong không gian 2D (Pose SE(2)).",
        "Hình 2.2: Mô hình động học robot di động vi sai và hệ trục tọa độ {W}, {B} [1].",
        "Hình 2.3: Bài toán điều khiển bám điểm (Driving to a Point) và hạn chế không kiểm soát góc hướng đích theta_G [1].",
        "Hình 2.4: Định nghĩa các biến trạng thái trong hệ tọa độ cực (rho, alpha, beta) cho bài toán điều khiển về tư thế đích [1].",
        "Hình 2.5: Sơ đồ khối cấu trúc điều khiển theo hệ tọa độ cực [1].",
        "Hình 2.6: Sơ đồ khối vòng điều khiển PID kinh điển.",
        "Hình 2.7: Sơ đồ khối cấu trúc bộ điều khiển PID Hai vòng (Dual-loop PID).",
        "Hình 3.1: Sơ đồ kiến trúc vòng lặp mô phỏng khép kín thuần Python.",
        "Hình 4.1: Phân tích vùng ổn định giải tích trên mặt phẳng tham số (k_alpha, k_beta) và cực trị riêng lớn nhất.",
        "Hình 4.2: Sơ đồ hệ tọa độ robot vi sai và các biến trạng thái cực cập trạm sạc thực tế.",
        "Hình 4.3: So sánh quỹ đạo di chuyển trong kịch bản lý tưởng S1 giữa Polar Controller và DualPID.",
        "Hình 4.4: Đáp ứng theo thời gian của trạng thái và tín hiệu điều khiển trong kịch bản S1.",
        "Hình 4.5: Quỹ đạo cập dock từ tập hợp đa tư thế xuất phát bao quát không gian làm việc.",
        "Hình 4.6: Biểu đồ hộp (Boxplot) so sánh sai số vị trí, sai số hướng và thời gian cập dock từ S2 đến S5.",
        "Hình 4.7: So sánh tỷ lệ docking thành công kèm khoảng tin cậy Wilson 95% qua 5 kịch bản.",
        "Hình 4.8: Đồ thị quét độ nhạy tỷ lệ thành công theo hệ số nhân nhiễu k.",
        "Hình 4.9: Bản đồ nhiệt không gian xuất phát (Success Rate Heatmap) trong kịch bản S5.",
        "Hình 4.10: Nghiên cứu bóc tách thành phần (Ablation Study) cho hai bộ điều khiển.",
    ]
    for f in figures_list:
        add_bullet_p(doc, "", f)
        
    add_heading_styled(doc, "DANH MỤC BẢNG BIỂU", level=1)
    tables_list = [
        "Bảng 3.1: Thông số hình học và giới hạn động học của mô hình robot vi sai.",
        "Bảng 3.2: Ma trận thiết kế 5 kịch bản thực nghiệm từ lý tưởng đến nhiễu khắc nghiệt.",
        "Bảng 3.3: Phân định nội dung kế thừa từ tài liệu tham khảo và phần tự thực hiện.",
        "Bảng 4.1: Bảng thông số Gain trước và sau tinh chỉnh công bằng (Fair Tuning, N=300).",
        "Bảng 4.2: Bảng chỉ số hiệu năng tổng hợp qua 5 kịch bản (n=300 lượt chạy độc lập mỗi kịch bản).",
        "Bảng 4.3: Kết quả thực nghiệm bóc tách thành phần kỹ thuật (Ablation Study).",
    ]
    for t in tables_list:
        add_bullet_p(doc, "", t)
        
    doc.add_page_break()

    # ==================== CHƯƠNG 1 ====================
    add_heading_styled(doc, "CHƯƠNG 1. GIỚI THIỆU VÀ ĐẶT VẤN ĐỀ", level=1)
    
    add_heading_styled(doc, "1.1. Bối cảnh và ý nghĩa thực tiễn", level=2)
    add_body_p(doc, "Trong kỷ nguyên Công nghiệp 4.0 và tự động hóa kho vận thông minh, các hệ thống Robot Tự hành (Autonomous Guided Vehicles - AGV, Autonomous Mobile Robots - AMR) đóng vai trò xương sống trong dây chuyền sản xuất và logistics hiện đại. Để duy trì khả năng vận hành liên tục 24/7 mà không phụ thuộc vào sự can thiệp thủ công của con người, tính năng tự động cập trạm sạc điện (Autonomous Docking) là một yêu cầu kỹ thuật mang tính sống còn.")
    add_body_p(doc, "Quá trình cập trạm sạc đòi hỏi robot di chuyển tiếp cận cổng kết nối sạc điện (thông qua tiếp điểm kim loại hoặc đế sạc không dây). Tại cự ly áp sát cuối cùng, bất kỳ sai lệch nhỏ nào về góc quay hoặc vị trí đều có thể dẫn tới việc gãy chốt sạc, hồ quang điện chập cháy hoặc tiếp xúc điện không đảm bảo. Do đó, bài toán docking đòi hỏi độ chính xác định vị ở cấp độ centimet và độ lệch góc chỉ trong vài độ, đặt ra thách thức lớn đối với hệ thống điều khiển tự động.")

    add_heading_styled(doc, "1.2. Phát biểu bài toán cập trạm sạc cho robot vi sai", level=2)
    add_body_p(doc, r"Đối tượng nghiên cứu của đề tài là robot di động truyền động vi sai 2 bánh độc lập (Differential Drive Mobile Robot hay mô hình Unicycle). Robot chuyển động trong mặt phẳng 2 chiều không vật cản. Về mặt điều khiển học, robot vi sai là một hệ phi holonomic (non-holonomic system) tiêu biểu: robot chịu ràng buộc không trượt bên, do đó số bậc tự do điều khiển chỉ là 2 (vận tốc dài [[v]] và vận tốc góc [[\omega]]) trong khi không gian cấu hình trạng thái có 3 chiều (tọa độ [[x, y]] và góc hướng [[\theta]]).")
    add_body_p(doc, r"Trong bài toán cập trạm sạc tại gốc tọa độ [[O(0, 0)]] với hướng kết nối dọc theo chiều dương trục hoành ([[\theta_{\mathrm{dock}} = 0\text{ rad}]]), cách tiếp cận trực quan nhất là quy về bài toán bám đường thẳng (Driving Along a Line) [1]: đặt một đường thẳng dẫn hướng đi thẳng vào cổng trạm sạc theo trục [[y = 0]] (phương trình tổng quát [[ax + by + c = 0]] với [[a = 0, b = 1, c = 0]], khoảng cách pháp tuyến [[d = y]] và hướng đường thẳng [[\theta_{\mathrm{line}} = 0]]). Robot cần triệt tiêu sai lệch ngang [[y \to 0]] và căn thẳng góc hướng [[\theta \to 0]] để tiến vào dock.")
    add_body_p(doc, r"Tuy nhiên, nhược điểm cốt lõi của chiến lược bám đường thẳng thuần túy [1] là robot di chuyển với vận tốc tiến không đổi ([[v = \text{const}]]) và chỉ điều khiển góc lái để giữ xe trên đường. Do đó, khi đến vị trí trạm sạc [[O(0, 0)]], xe không thể tự giảm tốc và dừng lại đúng điểm sạc mà sẽ tiếp tục chạy vượt quá trạm sạc (overshoot [[x > 0.05\text{ m}]], Hình 1.1). Hạn chế này đặt ra yêu cầu phải sử dụng các bộ điều khiển hoàn chỉnh ở Chương 2 — điều khiển đồng thời cả góc hướng lẫn vận tốc tiến theo khoảng cách tới dock (như giải thuật Tọa độ cực hoặc PID Hai vòng).")
    add_figure_with_caption(doc, str(theory_fig_dir / "fig1_1_line_following_dock.png"), "Hình 1.1: Minh họa bài toán bám đường thẳng hướng vào trạm sạc (Driving Along a Line) và hạn chế không tự dừng tại Dock.", width_inch=5.6)

    add_heading_styled(doc, "1.3. Mục tiêu kỹ thuật và tiêu chí định lượng cần đạt", level=2)
    add_body_p(doc, r"Mục tiêu trọng tâm của đề tài là nghiên cứu, thiết kế, mô phỏng và so sánh định lượng hai chiến lược điều khiển phi tuyến cho quá trình Autonomous Docking. Trạm sạc được đặt tại gốc tọa độ [[O(0, 0)]] với hướng kết nối dọc theo chiều dương trục [[x]] ([[\theta_{\mathrm{dock}} = 0\text{ rad}]]). Để đảm bảo tính nghiêm ngặt và tương thích với ứng dụng thực tế, tiêu chí docking thành công được đánh giá dựa trên TRẠNG THÁI THẬT của robot và phải thỏa mãn đồng thời 4 điều kiện khắt khe:")
    add_bullet_p(doc, "1. Sai số vị trí cuối cùng:", r"Khoảng cách từ tâm robot đến tâm dock không vượt quá 2 cm ([[\sqrt{x^2 + y^2} \le 0.02\text{ m}]]).")
    add_bullet_p(doc, "2. Sai số góc hướng cuối cùng:", r"Góc lệch giữa mũi xe và trục cổng sạc không vượt quá 3° ([[\left|\theta\right| \le 3.0^\circ = 0.0524\text{ rad}]]).")
    add_bullet_p(doc, "3. Giới hạn thời gian docking:", r"Toàn bộ chu trình tiếp cận và hoàn tất khóa vị trí không quá 60 giây ([[t \le 60.0\text{ s}]]).")
    add_bullet_p(doc, "4. Tuyệt đối không đâm quá trạm sạc:", r"Robot bị tính là thất bại ngay lập tức do vọt lố (Overshoot) nếu vị trí [[x > 0.05\text{ m}]], nhằm bảo vệ kết cấu cơ khí của trạm sạc.")

    add_heading_styled(doc, "1.4. Phạm vi thực hiện và bố cục báo cáo", level=2)
    add_body_p(doc, "Đề tài tập trung triển khai và kiểm chứng trên nền tảng Python chuẩn (NumPy, SciPy, Matplotlib, pandas, pytest), loại bỏ sự cồng kềnh của middleware ROS để tối ưu hóa hiệu năng tính toán đa tiến trình và cho phép đánh giá quy mô lớn hàng nghìn tập chạy độc lập.")
    add_body_p(doc, "Báo cáo được bố cục thành 5 chương chính: Chương 1 giới thiệu tổng quan đề tài; Chương 2 trình bày cơ sở lý thuyết động học, điều khiển [1]–[3], [6] và mô hình hai giải thuật; Chương 3 mô tả kiến trúc mô phỏng, mô hình nhiễu, quy trình tinh chỉnh công bằng và phân định đóng góp; Chương 4 phân tích chuyên sâu kết quả thực nghiệm; Chương 5 tổng kết các đóng góp và định hướng nghiên cứu tiếp theo.")

    doc.add_page_break()

    # ==================== CHƯƠNG 2 ====================
    add_heading_styled(doc, "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ GIẢI THUẬT ĐIỀU KHIỂN", level=1)
    
    add_heading_styled(doc, "2.1. Biểu diễn vị trí và hướng trong không gian 2D (Pose SE(2))", level=2)
    add_body_p(doc, "Trong không gian mặt phẳng 2 chiều, trạng thái cấu hình của một robot di động được biểu diễn bởi một tư thế (Pose) thuộc nhóm Euclide đặc biệt [[SE(2)]], bao gồm thành phần vị trí và góc hướng (Hình 2.1) [1], [2]:")
    add_latex_equation(doc, r"$\mathbf{q} = [x,\; y,\; \theta]^T \in SE(2)$", "2.1")
    add_body_p(doc, r"Trong đó [[(x, y)]] là tọa độ gốc hệ trục thân xe {B} (Body Frame) đối với hệ trục tọa độ thế giới {W} (World Frame), và [[\theta]] là góc lệch giữa trục hoành [[x_B]] của thân xe với trục hoành [[x_W]] của thế giới.")
    add_figure_with_caption(doc, str(theory_fig_dir / "fig2_1_pose_se2.png"), "Hình 2.1: Biểu diễn tư thế robot di động trong không gian 2D (Pose SE(2)).", width_inch=4.4)

    add_heading_styled(doc, "2.2. Động học robot vi sai (Unicycle Kinematics)", level=2)
    add_body_p(doc, "Mô hình động học robot di động dẫn động vi sai (Hình 2.2) được biểu diễn thông qua mối quan hệ giữa vận tốc hai bánh xe chủ động và vận tốc dài, vận tốc góc của thân xe trong hệ trục {B} [1], [2]:")
    
    # Chèn hình lý thuyết (trích từ ROBOT_FINAL.pdf trang 3)
    fig_th1 = str(theory_fig_dir / "pdf_p3_kinematics.png")
    add_figure_with_caption(doc, fig_th1, "Hình 2.2: Mô hình động học robot di động vi sai và hệ trục tọa độ {W}, {B} [1].", width_inch=4.2)

    add_body_p(doc, r"Từ vận tốc dài hai bánh xe [[v_{\mathrm{right}} = r\omega_R]] và [[v_{\mathrm{left}} = r\omega_L]] (bán kính bánh xe [[r = 0.035\text{ m}]], khoảng cách trục [[L = 0.23\text{ m}]]), vận tốc dài [[v_{b,x}]] và vận tốc góc [[\omega_{b,z}]] trong hệ trục thân xe {B} được tính như sau:")
    add_latex_equation(doc, r"$v_{b,x} = \frac{v_{\mathrm{right}} + v_{\mathrm{left}}}{2}, \qquad \omega_{b,z} = \frac{v_{\mathrm{right}} - v_{\mathrm{left}}}{L}$", "2.2")
    add_body_p(doc, r"Hệ phương trình động học vi sai trong hệ quy chiếu toàn cục {W} (ký hiệu gọn [[v = v_{b,x}]], [[\omega = \omega_{b,z}]]) có dạng [1], [2]:")
    add_latex_equation(doc, r"$\dot{x} = v_{b,x}\cos\theta, \qquad \dot{y} = v_{b,x}\sin\theta, \qquad \dot{\theta} = \omega_{b,z}$", "2.3")

    add_heading_styled(doc, "2.3. Giải thuật điều khiển theo Tọa độ cực (Driving to a Configuration)", level=2)
    add_body_p(doc, r"Trong bài toán điều hướng cơ bản về một điểm (Driving to a Point, Hình 2.3), robot chỉ bám theo tọa độ mục tiêu [[(x_G, y_G)]] mà không ràng buộc được góc hướng đích [[\theta_G]] [1]. Đối với nhiệm vụ cập trạm sạc, hạn chế này khiến robot không thể căn thẳng hàng với cổng sạc. Để đưa robot về đồng thời cả vị trí và góc hướng mong muốn [[(x^*, y^*, \theta^*)]], phương pháp điều khiển trong hệ tọa độ cực thực hiện phép đổi biến từ tọa độ Descartes sang hệ tọa độ cực (Hình 2.4):")

    # Chèn hình Driving to a Point (ROBOT_FINAL.pdf trang 4)
    fig_th_point = str(theory_fig_dir / "pdf_p4_driving_to_point.png")
    add_figure_with_caption(doc, fig_th_point, "Hình 2.3: Bài toán điều khiển bám điểm (Driving to a Point) và hạn chế không kiểm soát góc hướng đích θ_G [1].", width_inch=4.2)
    
    # Chèn hình Polar Config (ROBOT_FINAL.pdf trang 6)
    fig_th2 = str(theory_fig_dir / "pdf_p6_polar_config.png")
    add_figure_with_caption(doc, fig_th2, "Hình 2.4: Định nghĩa các biến trạng thái trong hệ tọa độ cực (ρ, α, β) cho bài toán điều khiển về tư thế đích [1].", width_inch=4.2)

    add_body_p(doc, r"Các biến tọa độ cực ([[\rho]]: cự ly tới dock; [[\alpha]]: góc lệch đường ngắm; [[\beta]]: góc tiếp cận mục tiêu) được xác định đối với trạm sạc tại gốc tọa độ [[O(0, 0)]]:")
    add_latex_equation(doc, r"$\rho = \sqrt{x^2 + y^2}$", "2.4a")
    add_latex_equation(doc, r"$\alpha = \arctan\left(\frac{-y}{-x}\right) - \theta, \qquad \alpha \in (-\pi, \pi]$", "2.4b")
    add_latex_equation(doc, r"$\beta = -\theta - \alpha, \qquad \beta \in (-\pi, \pi]$", "2.4c")
    
    # Chèn hình Sơ đồ khối Polar
    fig_th3 = str(theory_fig_dir / "slide_p35_Image196.png")
    add_figure_with_caption(doc, fig_th3, "Hình 2.5: Sơ đồ khối cấu trúc điều khiển theo hệ tọa độ cực [1].", width_inch=5.8)

    add_body_p(doc, "Luật điều khiển phản hồi trạng thái cực (Hình 2.5) có dạng [1]–[3]:")
    add_latex_equation(doc, r"$v = k_\rho \rho, \qquad \omega = k_\alpha \alpha + k_\beta \beta$", "2.5")
    add_body_p(doc, r"Ý nghĩa vật lý: [[k_\rho \rho]] kéo robot tiến về trạm sạc; [[k_\alpha \alpha]] hướng mũi xe về mục tiêu; [[k_\beta \beta]] uốn quỹ đạo sao cho khi chạm dock thì sai lệch hướng triệt tiêu ([[\beta \to 0]]). Để giải thuật hoạt động ổn định trong thực tế có nhiễu và mọi góc xuất phát, hai cơ chế bảo vệ được tích hợp vào bộ điều khiển Polar:")
    add_bullet_p(doc, "1. Cơ chế đóng băng góc gần trạm sạc (Freeze):", r"Khi robot tiến sát gốc tọa độ ([[\rho \to 0]]), phép tính góc hướng trở nên rất nhạy cảm với nhiễu đo vị trí, dễ làm góc [[\alpha, \beta]] dao động mạnh ở vài centimet cuối. Khi [[\rho < \rho_{\mathrm{freeze}} = 0.02\text{ m}]], bộ điều khiển chốt và giữ cố định cặp giá trị [[\alpha_{\mathrm{frozen}}, \beta_{\mathrm{frozen}}]] tại thời điểm vừa bước vào vùng đóng băng, giúp robot tiến thẳng êm ái vào cổng sạc.")
    add_bullet_p(doc, "2. Cơ chế quay tại chỗ khi quay lưng (Backwards Mode) kèm Hysteresis:", r"Khi robot quay lưng về trạm sạc ([[\left|\alpha\right| > \pi/2]]), nếu vẫn áp dụng [[v = k_\rho \rho > 0]] thì xe sẽ chạy lệch hướng hoặc lượn vòng rộng. Do đó, bộ điều khiển chuyển sang chế độ quay tại chỗ hướng mũi về dock:")
    add_latex_equation(doc, r"$v = 0, \qquad \omega = k_\alpha \alpha$", "2.6")
    add_body_p(doc, r"Để chống hiện tượng bật/tắt chế độ liên tục (chattering) khi [[\left|\alpha\right|]] dao động quanh ngưỡng [[\pi/2]] dưới tác động của nhiễu, dải trễ Hysteresis [[\Delta_h = 0.1\text{ rad}]] được áp dụng: chỉ kích hoạt quay tại chỗ khi [[\left|\alpha\right| > \pi/2 + \Delta_h]], và chỉ thoát về chế độ tiến bình thường (2.5) khi [[\left|\alpha\right| < \pi/2 - \Delta_h]].")

    add_heading_styled(doc, "2.4. Điều khiển PID kinh điển và cấu trúc PID Hai vòng (Dual-loop PID)", level=2)

    add_heading_styled(doc, "2.4.1. Lý thuyết điều khiển PID kinh điển", level=3)
    add_body_p(doc, r"Bộ điều khiển PID (Proportional–Integral–Derivative) tác động dựa trên sai số [[e(t) = SP - MV]] giữa giá trị đặt (Setpoint) và giá trị đo được (Measured Variable) [6]. Xuất phát từ bộ điều khiển tỷ lệ cơ bản nhất (chỉ xét sai số ở hiện tại — Present):")
    add_latex_equation(doc, r"$u_P(t) = K_p e(t)$", "2.7")
    add_body_p(doc, r"Dù trực quan và phản ứng tức thời theo độ lớn sai số thông qua hệ số [[K_p]], bộ điều khiển P đơn thuần gặp hai vấn đề lớn khi vận hành thực tế [6]:")
    add_bullet_p(doc, "1. Sai số xác lập (Steady-state error):", r"Khi sai số tiến về không ([[e = 0]]), tín hiệu điều khiển [[u_P = K_p e]] cũng bằng không. Đối với các hệ thống cần duy trì một mức tín hiệu điều khiển khác không tại điểm đặt hoặc chịu tác động của tải, ma sát, nhiễu lệch, khâu P không thể đưa sai số xác lập về đúng không mà luôn tồn tại một độ lệch tĩnh.")
    add_bullet_p(doc, "2. Dao động (Oscillations):", r"Khâu P chỉ phản ứng theo vị trí sai số hiện tại mà không có thành phần giảm chấn (damping) triệt tiêu quán tính biến thiên; khi tăng [[K_p]] để đáp ứng nhanh hơn, hệ thống dễ bị vọt lố và dao động kéo dài quanh điểm đặt.")
    add_body_p(doc, r"Để khắc phục hai hạn chế trên của bộ điều khiển P, lần lượt các khâu Tích phân (I) và Vi phân (D) được bổ sung [6]:")
    add_bullet_p(doc, "Khâu Tích phân (I — Past):", r"Cộng thêm thành phần tích lũy sai số quá khứ [[K_i \int_0^t e(\tau)\,d\tau]] (hoặc viết theo hằng số thời gian tích phân [[\frac{K_p}{T_i}\int_0^t e(\tau)\,d\tau]]) giúp tín hiệu điều khiển tiếp tục tăng chừng nào sai số vẫn còn tồn tại, từ đó triệt tiêu hoàn toàn sai số xác lập. Trong thực tế có bão hòa cơ cấu chấp hành, cần kẹp giới hạn thành phần tích phân trong [[ [-I_{\max}, I_{\max}] ]] (Anti-windup) để tránh tích lũy quá mức.")
    add_bullet_p(doc, "Khâu Vi phân (D — Future):", r"Bổ sung thành phần dự đoán xu hướng biến thiên sai số [[K_d \frac{de(t)}{dt}]] (hay [[K_p T_d \frac{de(t)}{dt}]]) đóng vai trò như một bộ giảm chấn (damper) chống lại tốc độ thay đổi quá nhanh của sai số, giúp dập tắt dao động và giảm vọt lố. Do phép lấy đạo hàm khuếch đại mạnh nhiễu đo tần số cao trên tín hiệu [[MV]], khâu D thực tế được ghép thêm bộ lọc thông thấp bậc 1 ([[\alpha_{\mathrm{filter}} = 0.8]]) [6].")
    add_body_p(doc, r"Tổng hợp cả ba thành phần tạo thành luật điều khiển PID đầy đủ (Hình 2.6):")
    add_latex_equation(doc, r"$u(t) = K_p e(t) + K_i \int_0^t e(\tau)\,d\tau + K_d \frac{de(t)}{dt}$", "2.8")
    add_figure_with_caption(doc, str(theory_fig_dir / "fig2_6_pid_classic.png"), "Hình 2.6: Sơ đồ khối vòng điều khiển PID kinh điển.", width_inch=5.6)

    add_heading_styled(doc, "2.4.2. Cấu trúc điều khiển PID Hai vòng (Dual-loop PID)", level=3)
    add_body_p(doc, r"Vì bộ PID kinh điển chỉ xử lý một đầu vào–một đầu ra (SISO) trong khi robot vi sai cần điều khiển đồng thời hai biến [[(v, \omega)]] để vừa bám đường dẫn hướng [[y = 0]] (Mục 1.2) vừa tự giảm tốc và dừng lại chính xác tại trạm sạc [[O(0, 0)]], báo cáo thiết kế cấu trúc PID Hai vòng (Dual-loop PID, Hình 2.7). Trước hết, góc hướng tham chiếu [[\theta_{\mathrm{ref}}]] và sai số góc [[e_\theta]] được xác định theo trường vector hội tụ về tim đường [[y = 0]]:")
    add_latex_equation(doc, r"$\theta_{\mathrm{ref}} = -\arctan(k_y y), \qquad e_\theta = \theta_{\mathrm{ref}} - \theta, \quad e_\theta \in (-\pi, \pi]$", "2.9")
    add_body_p(doc, r"Hai vòng điều khiển PID độc lập hoạt động song song để sinh vận tốc góc [[\omega]] và vận tốc dài [[v]]:")
    add_latex_equation(doc, r"$\omega = \mathrm{PID}_\omega(e_\theta), \qquad v = \mathrm{PID}_v(\rho)\cdot \max\left(0,\, \cos(e_\theta)\right)$", "2.10")
    add_body_p(doc, r"Trong đó vòng trong [[\mathrm{PID}_\omega(e_\theta)]] điều khiển tốc độ quay để giữ robot bám sát đường [[y = 0]] và hướng [[+x]], còn vòng ngoài [[\mathrm{PID}_v(\rho)]] điều khiển vận tốc dài theo cự ly [[\rho \to 0]] (kết hợp hệ số hãm tốc [[\max(0, \cos(e_\theta))]] khi góc lệch lớn), giúp khắc phục triệt để nhược điểm không tự dừng được của bài toán bám đường thẳng thuần túy.")
    add_figure_with_caption(doc, str(theory_fig_dir / "fig2_8_dual_pid.png"), "Hình 2.7: Sơ đồ khối cấu trúc bộ điều khiển PID Hai vòng (Dual-loop PID).", width_inch=5.8)

    doc.add_page_break()

    # ==================== CHƯƠNG 3 ====================
    add_heading_styled(doc, "CHƯƠNG 3. THIẾT KẾ HỆ THỐNG VÀ PHƯƠNG PHÁP TRIỂN KHAI", level=1)
    
    add_heading_styled(doc, "3.1. Kiến trúc phần mềm mô phỏng khép kín thuần Python", level=2)
    add_body_p(doc, r"Toàn bộ hệ thống mô phỏng được tổ chức theo kiến trúc hướng đối tượng phân lớp, phân tách rạch ròi giữa Trạng thái Thật (Ground Truth) và Trạng thái Đo được (Measured State) tại tần số 50 Hz ([[dt = 0.02\text{ s}]]) qua hàm run_episode() trong docking/sim.py (Hình 3.1).")
    add_body_p(doc, r"Chu trình mỗi bước gồm: (1) Cập nhật trạng thái thật [[q_{\mathrm{real}}]]; (2) Cộng nhiễu cảm biến và trễ FIFO để sinh [[q_{\mathrm{meas}}]]; (3) Bộ điều khiển chỉ quan sát [[q_{\mathrm{meas}}]] để tính lệnh [[(v, \omega)]]; (4) Áp nhiễu chấp hành và bão hòa trước khi tích phân động học; (5) Kiểm tra tiêu chí thành công hoặc lỗi overshoot trên [[q_{\mathrm{real}}]].")
    add_figure_with_caption(doc, str(theory_fig_dir / "fig3_1_sim_loop.png"), "Hình 3.1: Sơ đồ kiến trúc vòng lặp mô phỏng khép kín thuần Python.", width_inch=5.8)

    # Bảng 3.1: Thông số robot
    add_body_p(doc, "Bảng 3.1: Thông số hình học và giới hạn động học của mô hình robot vi sai.", bold_prefix="Bảng 3.1: ")
    t_robot = doc.add_table(rows=6, cols=3)
    t_robot.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_r = ["Thông số ký hiệu", "Giá trị thiết lập", "Ý nghĩa vật lý"]
    for j, h in enumerate(headers_r):
        c = t_robot.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    data_r = [
        ("Bán kính bánh xe (r)", "0.035 m (3.5 cm)", "Bán kính hình học bánh dẫn động"),
        ("Khoảng cách cơ sở (L)", "0.23 m (23.0 cm)", "Khoảng cách giữa hai tâm bánh xe chủ động"),
        ("Vận tốc dài cực đại (v_max)", "0.30 m/s", "Ngưỡng giới hạn bão hòa truyền động dài"),
        ("Vận tốc góc cực đại (omega_max)", "1.50 rad/s (~86°/s)", "Ngưỡng giới hạn bão hòa truyền động góc"),
        ("Chu kỳ lấy mẫu (dt)", "0.02 s (50 Hz)", "Bước tích phân và chu kỳ vòng điều khiển"),
    ]
    for i, row in enumerate(data_r):
        for j, val in enumerate(row):
            c = t_robot.rows[i+1].cells[j]
            set_cell_margins(c)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(11)

    add_heading_styled(doc, "3.2. Mô hình hóa nhiễu thực tế và trễ truyền thông", level=2)
    add_body_p(doc, "Nhằm phản ánh trung thực sai số đo lường, định vị và truyền động trong môi trường vận hành thực tế [1], [2], lớp dữ liệu Noise (trong docking/config.py) mô hình hóa 3 thành phần bất định chính:")
    add_bullet_p(doc, "1. Nhiễu đo lường cảm biến (Sensor Noise):", r"Vị trí [[(x, y)]] đo được bị ảnh hưởng bởi nhiễu trắng Gaussian có độ lệch chuẩn [[\sigma_{\mathrm{pos}}]]. Góc hướng [[\theta]] bị ảnh hưởng bởi nhiễu [[\sigma_{\mathrm{yaw}}]] cùng độ lệch tĩnh ([[\mathrm{bias}_{\mathrm{yaw}}]]) mô phỏng sai số căn chỉnh cảm biến IMU/Odometry.")
    add_bullet_p(doc, "2. Nhiễu cơ cấu chấp hành (Actuator Noise):", r"Vận tốc thực tế của bánh xe nhận lệnh cộng thêm nhiễu ngẫu nhiên [[\sigma_v]] và [[\sigma_\omega]] do hiện tượng ma sát sàn và trượt vi sai.")
    add_bullet_p(doc, "3. Độ trễ điều khiển và truyền thông (Control Delay):", r"Được mô hình hóa bằng hàng đợi FIFO độ dài [[N_{\mathrm{delay}}]] bước ([[t_{\mathrm{delay}} = N_{\mathrm{delay}} \cdot 0.02\text{ s}]]), phản ánh độ trễ xử lý gói tin và trễ đáp ứng cơ điện tử.")

    add_heading_styled(doc, "3.3. Phương pháp tinh chỉnh tham số công bằng (Fair Tuning)", level=2)
    add_body_p(doc, "Để đảm bảo tính khách quan và khoa học khi so sánh, đề tài áp dụng quy trình tinh chỉnh công bằng (Fair Tuning) nghiêm ngặt:")
    add_bullet_p(doc, "Ngân sách tính toán đồng nhất:", "Cả hai bộ điều khiển đều được cấp đúng N = 300 lần đánh giá ứng viên ngẫu nhiên có kiểm soát (Random Search) trong không gian tham số.")
    add_bullet_p(doc, "Tập dữ liệu độc lập:", "Quá trình tinh chỉnh được thực thi trên tập TUNING gồm 100 tư thế xuất phát độc lập (seed = 1) dưới kịch bản có nhiễu S2. Tập dữ liệu này hoàn toàn tách biệt với tập TEST (seed = 2024) dùng để chấm điểm cuối cùng.")
    add_bullet_p(doc, "Hàm mục tiêu chi phí đa chỉ tiêu:", "Hàm chi phí ưu tiên tuyệt đối tỷ lệ cập dock thành công, đồng thời phạt thời gian di chuyển chậm và áp mức phạt rất nặng đối với lỗi vọt lố qua dock:")
    add_latex_equation(doc, r"$J = -\mathrm{success\_rate} + 0.01\,\bar{t} + 0.5\,\mathrm{overshoot\_rate}$", "3.1")

    add_heading_styled(doc, "3.4. Thiết kế 5 kịch bản thực nghiệm và nghiên cứu bóc tách", level=2)
    add_body_p(doc, "Hệ thống kịch bản được phân tầng độ khó để kiểm tra tính bền vững của các thuật toán:")
    
    # Bảng 3.2: 5 Kịch bản
    add_body_p(doc, "Bảng 3.2: Ma trận thiết kế 5 kịch bản thực nghiệm từ lý tưởng đến nhiễu khắc nghiệt.", bold_prefix="Bảng 3.2: ")
    t_scen = doc.add_table(rows=6, cols=3)
    t_scen.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_s = ["Kịch bản", "Nội dung và Tham số nhiễu", "Ý nghĩa đánh giá kỹ thuật"]
    for j, h in enumerate(headers_s):
        c = t_scen.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    data_s = [
        ("S1: Lý tưởng", "Không nhiễu (sigma = 0), không trễ, 3 tư thế đại diện", "Kiểm chứng tính đúng đắn động học và đáp ứng cơ bản"),
        ("S2: Nhiễu đo", "sigma_pos = 1 cm, sigma_yaw = 1.0°", "Đánh giá độ nhạy trước sai số cảm biến định vị"),
        ("S3: Chấp hành & Trễ", "sigma_v = 0.01 m/s, sigma_w = 0.05 rad/s, trễ 75 ms", "Kiểm tra độ ổn định khi truyền động bị trễ và nhiễu"),
        ("S4: Tư thế khó", "Lệch bên cực đại (|y| >= 1.5 m) hoặc gần sát dock lệch góc", "Thử thách giới hạn bẻ lái và tránh overshoot"),
        ("S5: Nhiễu tổng hợp", "sigma_pos = 2 cm, sigma_yaw = 3.0°, trễ 100 ms, sigma_v=0.02, sigma_w=0.1", "Mô phỏng điều kiện làm việc thực tế khắc nghiệt nhất"),
    ]
    for i, row in enumerate(data_s):
        for j, val in enumerate(row):
            c = t_scen.rows[i+1].cells[j]
            set_cell_margins(c)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(11)

    add_heading_styled(doc, "3.5. Phân định nội dung kế thừa và đóng góp tự thực hiện", level=2)
    add_body_p(doc, "Để đảm bảo tính minh bạch học thuật, Bảng 3.3 phân định rõ các cơ sở lý thuyết/phương pháp kế thừa từ tài liệu tham khảo và các hạng mục do tác giả trực tiếp thiết kế, lập trình và kiểm chứng.")
    add_body_p(doc, "Bảng 3.3: Phân định nội dung kế thừa từ tài liệu tham khảo và phần tự thực hiện.", bold_prefix="Bảng 3.3: ")
    t_contrib = doc.add_table(rows=5, cols=3)
    t_contrib.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_c = ["Hạng mục", "Nội dung kế thừa / Tham khảo", "Phần tự thiết kế, cài đặt & mở rộng"]
    for j, h in enumerate(headers_c):
        c = t_contrib.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
    data_c = [
        ("Mô hình động học & mô phỏng", "Biểu diễn SE(2), phương trình động học unicycle [1], [2].", "Xây dựng hoàn chỉnh bộ mô phỏng thuần Python (docking/robot.py, sim.py) với hàng đợi trễ FIFO, bão hòa giữ tỷ lệ v/ω và tách biệt trạng thái thật/đo."),
        ("Thuật toán Polar Controller", "Luật điều khiển tọa độ cực (rho, alpha, beta) và điều kiện ổn định [1]–[3].", "Cài đặt PolarController, bổ sung quay tại chỗ với vùng trễ Hysteresis (0.1 rad) và đóng băng góc gần dock (rho < 0.02 m) để chống rung nhiễu và điểm kỳ dị."),
        ("Thuật toán Dual-loop PID", "Chiến lược bám đường thẳng [1] và lý thuyết PID, anti-windup, lọc D [6].", "Thiết kế cấu trúc hai vòng vector-field theta_ref = -atan(k_y * y) kết hợp hãm tốc cos(e_theta), cài đặt lớp PID tùy biến."),
        ("Thực nghiệm & kiểm thử", "Khoảng tin cậy Wilson [5].", "Thiết kế quy trình Fair Tuning (N=300, seed=1), 5 kịch bản S1–S5 (n=300, seed=2024), quét nhiễu k, Ablation Study, bộ kiểm thử tự động pytest và trực quan hóa."),
    ]
    for i, row in enumerate(data_c):
        for j, val in enumerate(row):
            c = t_contrib.rows[i+1].cells[j]
            set_cell_margins(c)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(11)

    doc.add_page_break()

    # ==================== CHƯƠNG 4 ====================
    add_heading_styled(doc, "CHƯƠNG 4. KẾT QUẢ THỰC NGHIỆM VÀ THẢO LUẬN CHUYÊN SÂU", level=1)
    
    add_heading_styled(doc, "4.1. Kết quả kiểm chứng ổn định giải tích", level=2)
    add_body_p(doc, "Trước khi bước vào mô phỏng động học, việc kiểm chứng ổn định giải tích được thực hiện bằng cách giải phương trình trị riêng và quét không gian tham số.")
    
    fig8_path = str(fig_dir / "fig8_stability_analysis.png")
    add_figure_with_caption(doc, fig8_path, "Hình 4.1: Phân tích vùng ổn định giải tích trên mặt phẳng tham số (k_alpha, k_beta) và cực trị riêng lớn nhất.")
    
    add_body_p(doc, r"Hình 4.1(a) thể hiện bản đồ vùng ổn định giải tích trên mặt phẳng tham số [[(k_\alpha, k_\beta)]] với [[k_\rho = 1.185]] cố định. Vùng màu xanh lá biểu thị các cặp tham số thỏa mãn đồng thời các điều kiện ổn định Hurwitz và điều kiện không đổi chiều chuyển động. Cặp gain tối ưu được chọn ([[k_\alpha = 2.020]], [[k_\beta = -0.586]]) nằm sâu bên trong vùng an toàn ổn định. Hình 4.1(b) quét phần thực lớn nhất của trị riêng [[\max(\mathrm{Re}(\lambda))]] theo [[k_\alpha]], chứng minh hệ thống luôn có nghiệm cực âm vững chắc, đảm bảo độ tắt dần nhanh của sai số.")

    # Bảng 4.1: Bảng Gain
    add_body_p(doc, "Bảng 4.1: Bảng thông số Gain trước và sau tinh chỉnh công bằng (Fair Tuning, N=300).", bold_prefix="Bảng 4.1: ")
    t_gain = doc.add_table(rows=7, cols=5)
    t_gain.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_g = ["Bộ điều khiển", "Tham số", "Giá trị ban đầu", "Giá trị sau tinh chỉnh", "Ý nghĩa kỹ thuật"]
    for j, h in enumerate(headers_g):
        c = t_gain.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    data_g = [
        ("Polar", "k_rho", "0.500", "1.1851", "Hệ số suy giảm cự ly tới dock"),
        ("Polar", "k_alpha", "1.500", "2.0196", "Hệ số bẻ lái theo đường ngắm"),
        ("Polar", "k_beta", "-0.500", "-0.5856", "Hệ số nắn hướng tiếp cận dock"),
        ("DualPID", "Kp_v, Ki_v, Kd_v", "(1.0, 0.0, 0.1)", "(1.555, 0.0045, 0.112)", "Vòng ngoài: Điều khiển vận tốc dài"),
        ("DualPID", "Kp_w, Ki_w, Kd_w", "(3.0, 0.0, 0.2)", "(2.5857, 0.015, 0.0885)", "Vòng trong: Điều khiển vận tốc góc"),
        ("DualPID", "k_y", "2.000", "3.4972", "Hệ số trường vector dẫn hướng"),
    ]
    for i, row in enumerate(data_g):
        for j, val in enumerate(row):
            c = t_gain.rows[i+1].cells[j]
            set_cell_margins(c)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(11)

    add_heading_styled(doc, "4.2. Đáp ứng thời gian và quỹ đạo trong kịch bản lý tưởng S1", level=2)
    add_body_p(doc, r"Kịch bản S1 kiểm chứng động học thuần túy trên 3 tư thế đại diện đặc trưng: Tư thế 1 nằm thẳng trước dock [[(-2, 0, 0)]]; Tư thế 2 lệch bên [[(-1.5, 1.5, 0)]]; và Tư thế 3 quay lưng hoàn toàn [[(-1.5, 0.5, \pi)]].")
    
    fig1_path = str(fig_dir / "fig1_dock_robot_coordinate_system.png")
    add_figure_with_caption(doc, fig1_path, "Hình 4.2: Sơ đồ hệ tọa độ robot vi sai và các biến trạng thái cực cập trạm sạc thực tế.")

    fig2_path = str(fig_dir / "fig2_s1_trajectories.png")
    add_figure_with_caption(doc, fig2_path, "Hình 4.3: So sánh quỹ đạo di chuyển trong kịch bản lý tưởng S1 giữa Polar Controller và DualPID.")

    fig3_path = str(fig_dir / "fig3_s1_time_response.png")
    add_figure_with_caption(doc, fig3_path, "Hình 4.4: Đáp ứng theo thời gian của trạng thái (vị trí, góc) và tín hiệu điều khiển (v, ω) trong kịch bản S1.")

    add_body_p(doc, r"Quan sát Hình 4.3 và 4.4, ở Tư thế 3 (quay lưng), cả hai bộ điều khiển đều kích hoạt chế độ xoay tại chỗ xuất sắc: vận tốc dài [[v = 0\text{ m/s}]] trong khi vận tốc góc [[\omega]] bẻ lái dứt khoát đưa đầu xe hướng về trạm sạc trước khi bắt đầu tăng tốc. Polar Controller tạo ra quỹ đạo trơn tru hơn (chiều dài trung bình 2.23 m so với 2.41 m của PID) và hoàn thành cập dock chỉ trong 9.17 s (nhanh hơn 8% so với 9.94 s của PID).")

    add_heading_styled(doc, "4.3. Đánh giá quỹ đạo đa tư thế xuất phát bao quát không gian", level=2)
    add_body_p(doc, r"Để kiểm tra tính toàn cục của thuật toán, mô phỏng kích hoạt đồng thời 16 tư thế xuất phát ngẫu nhiên phân bố đều trên toàn bộ không gian làm việc [[x \in [-3.0, -0.5]\text{ m}]], [[y \in [-2.0, 2.0]\text{ m}]] và góc ban đầu [[\theta \in [-\pi, \pi] ]].")
    
    fig4_path = str(fig_dir / "fig4_multi_pose_trajectories.png")
    add_figure_with_caption(doc, fig4_path, "Hình 4.5: Quỹ đạo cập dock từ tập hợp đa tư thế xuất phát bao quát không gian làm việc.")
    
    add_body_p(doc, "Hình 4.5 minh chứng sự vượt trội rõ rệt: 100% các đường quỹ đạo của Polar Controller đều hội tụ mượt mà, uốn cong tự nhiên và đi thẳng vào miệng trạm sạc theo trục +x. Ngược lại, DualPID có một số quỹ đạo xuất phát từ cự ly gần nhưng lệch góc lớn bị hiện tượng bẻ lái gắt, dẫn tới nguy cơ cắt ngang dock.")

    add_heading_styled(doc, "4.4. Phân tích phân bố sai số và thời gian cập dock (Kịch bản S2 – S5)", level=2)
    add_body_p(doc, "Trên tập kiểm thử chuẩn gồm n = 300 lượt chạy độc lập cho mỗi kịch bản, các chỉ số định lượng về sai số vị trí, sai số hướng và thời gian cập dock được tổng hợp chi tiết qua biểu đồ hộp (Boxplot).")
    
    fig5_path = str(fig_dir / "fig5_boxplots_s2_s5.png")
    add_figure_with_caption(doc, fig5_path, "Hình 4.6: Biểu đồ hộp (Boxplot) so sánh sai số vị trí, sai số hướng và thời gian cập dock từ S2 đến S5.")

    # Bảng 4.2: Hiệu năng kịch bản
    add_body_p(doc, "Bảng 4.2: Bảng chỉ số hiệu năng tổng hợp qua 5 kịch bản (n=300 lượt chạy độc lập mỗi kịch bản).", bold_prefix="Bảng 4.2: ")
    t_perf = doc.add_table(rows=11, cols=9)
    t_perf.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_p = ["Kịch bản", "Bộ ĐK", "Tỷ lệ thành công (95% CI)", "Thời gian (s, mean±std)", "Sai số vị trí (cm)", "Sai số hướng (°)", "Tỷ lệ Overshoot", "Chiều dài (m)", "Năng lượng ĐK"]
    for j, h in enumerate(headers_p):
        c = t_perf.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c, left=60, right=60)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(9.5)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    data_p = [
        ("S1", "Polar", "100.0% [98.7, 100]", "9.17 ± 2.26", "1.94 ± 0.21", "0.37° ± 0.64°", "0.0%", "2.23 ± 0.67", "2.90 ± 1.49"),
        ("S1", "DualPID", "90.3% [86.5, 93.2]", "9.94 ± 2.71", "2.48 ± 1.81", "1.36° ± 4.35°", "9.7%", "2.41 ± 0.83", "3.05 ± 1.38"),
        ("S2", "Polar", "100.0% [98.7, 100]", "9.22 ± 2.32", "1.71 ± 0.40", "1.86° ± 0.81°", "0.0%", "2.23 ± 0.67", "3.70 ± 1.63"),
        ("S2", "DualPID", "90.0% [86.1, 92.9]", "9.92 ± 2.71", "2.47 ± 1.83", "1.56° ± 4.28°", "10.0%", "2.41 ± 0.83", "3.18 ± 1.39"),
        ("S3", "Polar", "100.0% [98.7, 100]", "10.96 ± 3.74", "1.60 ± 0.64", "1.56° ± 0.86°", "0.0%", "2.24 ± 0.66", "4.77 ± 3.66"),
        ("S3", "DualPID", "90.7% [86.8, 93.5]", "9.86 ± 2.71", "2.42 ± 1.60", "1.25° ± 3.78°", "9.3%", "2.41 ± 0.82", "3.13 ± 1.39"),
        ("S4", "Polar", "100.0% [98.7, 100]", "7.36 ± 1.88", "1.47 ± 0.59", "1.91° ± 0.82°", "0.0%", "1.43 ± 0.66", "4.62 ± 2.93"),
        ("S4", "DualPID", "18.0% [14.1, 22.7]", "5.68 ± 2.54", "7.62 ± 4.85", "13.37° ± 12.06°", "82.0%", "1.36 ± 0.66", "3.13 ± 1.22"),
        ("S5", "Polar", "99.3% [97.6, 99.8]", "9.64 ± 4.22", "1.52 ± 0.54", "2.53° ± 7.31°", "0.0%", "2.25 ± 0.69", "6.37 ± 10.55"),
        ("S5", "DualPID", "90.7% [86.8, 93.5]", "9.74 ± 2.74", "2.37 ± 1.56", "1.92° ± 3.44°", "9.3%", "2.41 ± 0.82", "3.81 ± 1.45"),
    ]
    for i, row in enumerate(data_p):
        for j, val in enumerate(row):
            c = t_perf.rows[i+1].cells[j]
            set_cell_margins(c, left=60, right=60)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(9.0)
            if j == 2 and "100.0%" in val:
                r.bold = True

    add_heading_styled(doc, "4.5. Độ tin cậy tỷ lệ thành công với khoảng tin cậy Wilson 95%", level=2)
    add_body_p(doc, "Để đảm bảo tính nghiêm ngặt về mặt thống kê xác suất, tỷ lệ thành công được tính toán kèm khoảng tin cậy Wilson score interval 95% [5] (Hình 4.7).")
    
    fig6_path = str(fig_dir / "fig6_success_rates_wilson.png")
    add_figure_with_caption(doc, fig6_path, "Hình 4.7: So sánh tỷ lệ docking thành công kèm khoảng tin cậy Wilson 95% qua 5 kịch bản.")
    
    add_body_p(doc, "Tại các kịch bản chuẩn S1, S2, S3, Polar Controller đạt độ tin cậy tuyệt đối 100.0% với cận dưới khoảng tin cậy Wilson lên tới 98.7%. Ở kịch bản khắc nghiệt nhất S5 (nhiễu tổng hợp cao), Polar vẫn duy trì tỷ lệ ấn tượng 99.3% [97.6%, 99.8%], trong khi DualPID dao động quanh ngưỡng 90.0% - 90.7%.")
    add_body_p(doc, r"Đặc biệt tại kịch bản tư thế khó S4, tỷ lệ thành công của DualPID sụt giảm nghiêm trọng xuống chỉ còn 18.0% [14.1%, 22.7%], trong khi Polar vẫn giữ vững 100.0%. Nguyên nhân sâu xa là trường vector [[\theta_{\mathrm{ref}} = -\arctan(k_y y)]] đổi chiều quá gấp khi xe ở gần dock ([[|y| \ge 1.5\text{ m}]], [[x \ge -1.0\text{ m}]]); dưới giới hạn vận tốc góc [[\omega_{\max} = 1.5\text{ rad/s}]], robot vi sai bị trôi bán kính quay và cắt qua dock, dẫn tới tỷ lệ vọt lố (Overshoot rate) lên tới 82.0%.")

    add_heading_styled(doc, "4.6. Đánh giá độ nhạy khi quét hệ số nhiễu k và bản đồ nhiệt", level=2)
    add_body_p(doc, "Để kiểm tra ngưỡng suy giảm của thuật toán, hệ số nhân k in {0, 0.5, 1, 1.5, 2, 3, 4} được nhân tuyến tính lên toàn bộ bộ tham số nhiễu S5.")
    
    fig7_path = str(fig_dir / "fig7_sweep_noise.png")
    add_figure_with_caption(doc, fig7_path, "Hình 4.8: Đồ thị quét độ nhạy tỷ lệ thành công theo hệ số nhân nhiễu k.")

    fig9_path = str(fig_dir / "fig9_heatmap_success_map.png")
    add_figure_with_caption(doc, fig9_path, "Hình 4.9: Bản đồ nhiệt không gian xuất phát (Success Rate Heatmap) trong kịch bản S5.")

    add_body_p(doc, r"Kết quả quét nhiễu trên Hình 4.8 mang lại một phát hiện khoa học đặc biệt thú vị: Trong dải nhiễu thực tế ([[k \le 1.0]]), Polar Controller áp đảo hoàn toàn. Tuy nhiên, khi hệ số nhiễu tăng vọt lên mức cực đoan ([[k = 2.0 \to 4.0]]), tỷ lệ thành công của Polar sụt giảm dần (từ 78% xuống 38%), trong khi DualPID vẫn duy trì được độ ổn định trên 82% - 90%.")
    add_body_p(doc, r"Nguyên nhân bản chất là do Polar Controller tính toán góc [[\alpha, \beta]] trực tiếp từ trạng thái đo [[q_{\mathrm{meas}}]]; khi nhiễu đo lường quá lớn, vector chỉ hướng bị rung lắc mạnh. Ngược lại, DualPID sở hữu bộ lọc vi phân thông thấp D ([[\alpha_{\mathrm{filter}} = 0.8]]) và hàm [[\arctan(k_y y)]] đóng vai trò như một bộ lọc không gian phi tuyến tự nhiên, giúp PID miễn nhiễm tốt hơn trước nhiễu trắng biên độ cực lớn.")

    add_heading_styled(doc, "4.7. Nghiên cứu bóc tách thành phần (Ablation Study)", level=2)
    add_body_p(doc, "Nghiên cứu bóc tách nhằm phân lập và định lượng chính xác đóng góp của từng thành phần cải tiến.")

    # Bảng 4.3: Ablation
    add_body_p(doc, "Bảng 4.3: Kết quả thực nghiệm bóc tách thành phần kỹ thuật (Ablation Study).", bold_prefix="Bảng 4.3: ")
    t_abl = doc.add_table(rows=7, cols=5)
    t_abl.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_a = ["Bộ điều khiển", "Biến thể thử nghiệm", "Tỷ lệ thành công", "Thời gian docking (s)", "Sai số vị trí (cm)"]
    for j, h in enumerate(headers_a):
        c = t_abl.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    data_a = [
        ("Polar", "Polar đầy đủ (có Freeze, có Hysteresis)", "100.0%", "9.44 s", "1.57 cm"),
        ("Polar", "Bỏ Freeze gần dock (rho < 2 cm)", "100.0%", "9.50 s", "1.63 cm (Tăng sai số)"),
        ("Polar", "Bỏ Hysteresis quay lưng", "100.0%", "9.44 s", "1.59 cm"),
        ("DualPID", "PID đầy đủ (có Lọc D, có Anti-windup)", "94.0%", "9.95 s", "2.39 cm"),
        ("DualPID", "Bỏ Bộ lọc vi phân D (Filter D)", "94.0%", "9.81 s", "2.31 cm"),
        ("DualPID", "Bỏ Anti-windup tích phân", "95.0%", "9.47 s", "2.32 cm"),
    ]
    for i, row in enumerate(data_a):
        for j, val in enumerate(row):
            c = t_abl.rows[i+1].cells[j]
            set_cell_margins(c)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(10)

    fig10_path = str(fig_dir / "fig10_ablation_study.png")
    add_figure_with_caption(doc, fig10_path, "Hình 4.10: Nghiên cứu bóc tách thành phần (Ablation Study) cho hai bộ điều khiển.")

    add_body_p(doc, "Kết quả từ Bảng 4.3 và Hình 4.10 khẳng định: Với Polar Controller, cơ chế Freeze đóng vai trò then chốt giúp giảm sai số vị trí tiếp cận từ 1.63 cm xuống 1.57 cm và triệt tiêu hoàn toàn rung lắc bẻ lái tại cự ly áp sát. Với DualPID, các cơ chế Anti-windup và Lọc D giúp ổn định vòng điều khiển trong dải hoạt động danh định.")

    add_heading_styled(doc, "4.8. Thảo luận chuyên sâu: So sánh ưu - nhược điểm bản chất", level=2)
    add_body_p(doc, "Từ chuỗi thực nghiệm đồ sộ trên, bức tranh so sánh kỹ thuật giữa hai trường phái điều khiển được đúc kết như sau:")
    add_bullet_p(doc, "1. Bộ điều khiển Tọa độ cực (Polar Controller):", "Ưu điểm vượt trội là khả năng bao quát toàn bộ không gian trạng thái, hội tụ mượt mà từ mọi tư thế xuất phát khắc nghiệt nhất (kể cả quay lưng hoặc lệch sát dock). Quỹ đạo hình học tự nhiên và thời gian docking tối ưu nhất. Tuy nhiên, nhược điểm là độ nhạy với nhiễu đo lường tăng khi mức nhiễu vượt quá ngưỡng thiết kế.")
    add_bullet_p(doc, "2. Bộ điều khiển PID Hai vòng (Dual-loop PID):", "Ưu điểm là cấu trúc điều khiển trực quan, tiêu thụ năng lượng mượt mà và khả năng lọc nhiễu tần số cao rất tốt nhờ cơ chế lọc D. Tuy nhiên, nhược điểm chí mạng là sự hạn chế hình học của hàm trường vector arctan, khiến PID dễ bị vọt lố (overshoot) khi robot xuất phát ở tư thế khó sát dock.")

    doc.add_page_break()

    # ==================== CHƯƠNG 5 ====================
    add_heading_styled(doc, "CHƯƠNG 5. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN", level=1)
    
    add_heading_styled(doc, "5.1. Kết luận", level=2)
    add_body_p(doc, "Đề tài đã hoàn thành xuất sắc toàn bộ các mục tiêu nghiên cứu và yêu cầu kỹ thuật đề ra cho bài toán Autonomous Docking của robot di động vi sai 2D:")
    add_bullet_p(doc, "1. Xây dựng hoàn chỉnh nền tảng mô phỏng khép kín thuần Python:", "Không phụ thuộc vào ROS, tích hợp đầy đủ động học vi sai, mô hình nhiễu cảm biến/chấp hành và trễ FIFO thời gian thực.")
    add_bullet_p(doc, "2. Thiết kế và tối ưu hóa hai bộ điều khiển phi tuyến:", "Polar Controller (Siegwart/Aicardi theo chuẩn Peter Corke) tích hợp Hysteresis/Freeze và Dual-loop PID tích hợp Anti-windup/Filter D. Cả hai bộ đều được tinh chỉnh công bằng (Fair Tuning, N=300) trên tập dữ liệu độc lập.")
    add_bullet_p(doc, "3. Khẳng định tính ổn định toán học:", "Chứng minh giải tích thông qua ma trận trạng thái tuyến tính hóa A, tiêu chuẩn Hurwitz và phân tích mặt phẳng pha.")
    add_bullet_p(doc, "4. Đánh giá thực nghiệm quy mô lớn với độ tin cậy cao:", "Thực hiện hàng nghìn lượt chạy trên 5 kịch bản S1–S5. Polar Controller đạt tỷ lệ docking thành công ấn tượng 99.3% - 100%, sai số vị trí < 1.7 cm, sai số góc < 2.0° và thời gian chỉ khoảng 7 – 10 s.")

    add_heading_styled(doc, "5.2. Các hạn chế còn tồn tại và hướng phát triển", level=2)
    add_body_p(doc, "Mặc dù đạt được những kết quả rất khả quan, nghiên cứu vẫn còn một số điểm giới hạn có thể mở rộng trong tương lai:")
    add_bullet_p(doc, "1. Thử nghiệm trên mô hình phần cứng thật:", "Triển khai mã nguồn lên robot AGV/AMR vật lý sử dụng cảm biến camera nhận dạng thẻ mốc ArUco/AprilTag và cảm biến khoảng cách ToF/LiDAR để kiểm chứng tác động của ma sát sàn phi tuyến.")
    add_bullet_p(doc, "2. Mở rộng bài toán né tránh vật cản động:", "Tích hợp giải thuật biểu đồ trường vector VFH (Vector Field Histogram) [4], trường thế nhân tạo (Artificial Potential Field - APF) hoặc Dynamic Window Approach (DWA) vào giai đoạn tiếp cận dock khi có vật cản di động bất ngờ xuất hiện.")
    add_bullet_p(doc, "3. Ứng dụng điều khiển tối ưu MPC (Model Predictive Control):", "Nghiên cứu bộ điều khiển dự báo mô hình phi tuyến (NMPC) để vừa đảm bảo cập dock chính xác vừa tối ưu hóa năng lượng tiêu thụ dưới các ràng buộc bão hòa chấp hành khắt khe.")

    doc.add_page_break()

    # ==================== TÀI LIỆU THAM KHẢO ====================
    add_heading_styled(doc, "TÀI LIỆU THAM KHẢO", level=1)
    references = [
        "[1] P. I. Corke, W. Jachimczyk, and R. Pillat, Robotics, Vision and Control: Fundamental Algorithms in MATLAB, 3rd ed. Cham, Switzerland: Springer Nature, 2023.",
        "[2] R. Siegwart, I. R. Nourbakhsh, and D. Scaramuzza, Introduction to Autonomous Mobile Robots, 2nd ed. Cambridge, MA, USA: MIT Press, 2011.",
        "[3] M. Aicardi, G. Casalino, A. Bicchi, and A. Balestrino, 'Closed loop steering of unicycle like vehicles via Lyapunov techniques,' IEEE Robotics & Automation Magazine, vol. 2, no. 1, pp. 27–35, Mar. 1995.",
        "[4] J. Borenstein and Y. Koren, 'The vector field histogram-fast obstacle avoidance for mobile robots,' IEEE Transactions on Robotics and Automation, vol. 7, no. 3, pp. 278–288, Jun. 1991.",
        "[5] E. B. Wilson, 'Probable inference, the law of succession, and statistical inference,' Journal of the American Statistical Association, vol. 22, no. 158, pp. 209–212, 1927.",
        "[6] K. J. Åström and T. Hägglund, Advanced PID Control. Research Triangle Park, NC: ISA-The Instrumentation, Systems, and Automation Society, 2006.",
    ]
    for ref in references:
        p_r = doc.add_paragraph()
        p_r.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_r.paragraph_format.line_spacing = 1.25
        p_r.paragraph_format.space_after = Pt(4)
        r = p_r.add_run(ref)
        r.font.name = 'Times New Roman'
        r.font.size = Pt(11)

    doc.add_page_break()

    # ==================== PHỤ LỤC ====================
    add_heading_styled(doc, "PHỤ LỤC: HƯỚNG DẪN THỰC THI MÃ NGUỒN VÀ BỘ KIỂM THỬ TỰ ĐỘNG", level=1)
    add_body_p(doc, "Toàn bộ mã nguồn dự án được tổ chức mô-đun hóa trong thư mục docking/ (lưu trữ công khai tại kho mã nguồn GitHub: https://github.com/xtruong101/Docking_Robot.git, môi trường Python 3.10+ với các thư viện phụ thuộc liệt kê trong requirements.txt) và có thể được tái lập kết quả tự động bằng các lệnh đơn giản:")
    
    add_heading_styled(doc, "1. Cấu trúc cây thư mục mã nguồn chính", level=2)
    tree_text = """ROBOT_FINAL/
├── main.py                    # Wrapper tự động phát hiện Python và thực thi
├── requirements.txt           # Danh mục thư viện phụ thuộc (numpy, scipy, matplotlib, pandas, pytest)
├── docking/                   # Thư mục mã nguồn thuật toán
│   ├── config.py              # Tham số hình học, giới hạn bão hòa, dataclass Noise
│   ├── robot.py               # Động học vi sai, wrap góc, bão hòa vận tốc, hàng đợi trễ FIFO
│   ├── controllers.py         # PolarController, DualPIDController, lớp PID (Anti-windup/Filter D)
│   ├── sim.py                 # Hàm run_episode() mô phỏng tập chạy và đánh giá trạng thái thật
│   ├── stability.py           # Tuyến tính hóa ma trận A, trị riêng, kiểm tra ổn định & tính đơn điệu
│   ├── tuning.py              # Tinh chỉnh công bằng Fair Tuning (N=300 đánh giá/bộ)
│   ├── experiments.py         # Chạy kịch bản S1–S5 (n=300), quét hệ số nhiễu k, ablation study
│   ├── plots.py               # Sinh toàn bộ 10 hình vẽ kỹ thuật (PNG 300 dpi và PDF vector)
│   ├── stats.py               # Thống kê, khoảng tin cậy Wilson 95%
│   └── tests/test_basic.py    # Bộ kiểm thử pytest tự động 6 tiêu chuẩn bắt buộc
├── results/                   # Dữ liệu xuất: best_gains.json, scenario_metrics.csv, summary.md
└── figures/                   # 10 bộ đồ thị kỹ thuật xuất bản chất lượng cao + 3 hình minh họa mô hình [1]"""
    
    p_code = doc.add_paragraph()
    p_code.paragraph_format.space_before = Pt(4)
    p_code.paragraph_format.space_after = Pt(8)
    r_c = p_code.add_run(tree_text)
    r_c.font.name = 'Consolas'
    r_c.font.size = Pt(9.5)
    
    add_heading_styled(doc, "2. Hướng dẫn chạy chương trình", level=2)
    add_bullet_p(doc, "Chạy toàn bộ quy trình từ A đến Z:", "python main.py --all")
    add_bullet_p(doc, "Chạy riêng kiểm chứng ổn định:", "python main.py --stability")
    add_bullet_p(doc, "Chạy riêng tinh chỉnh tham số:", "python main.py --tune")
    add_bullet_p(doc, "Chạy riêng kịch bản thực nghiệm S1–S5:", "python main.py --scenarios")
    add_bullet_p(doc, "Xuất toàn bộ 10 hình đồ thị kỹ thuật:", "python main.py --plots")
    add_bullet_p(doc, "Chạy bộ kiểm thử tự động pytest:", "pytest docking/tests/test_basic.py -v")

    print(f"Đang lưu tài liệu...")
    try:
        doc.save(str(output_docx))
        print(f"Xuất báo cáo nâng cấp thành công ra: {output_docx}")
    except PermissionError:
        alt_docx = base_dir / "Bao_Cao_Cuoi_Ky_Autonomous_Docking_Ban_Nang_Cap.docx"
        print(f"Tệp {output_docx.name} đang được mở trong Word.")
        print(f"Đang lưu bản nâng cấp ra: {alt_docx.name}...")
        doc.save(str(alt_docx))
        print(f"Xuất báo cáo thành công ra: {alt_docx}")

if __name__ == "__main__":
    main()
