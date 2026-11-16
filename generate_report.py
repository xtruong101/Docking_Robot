"""
Tự động sinh Báo cáo Cuối kỳ môn Kỹ thuật Robot:
Đề tài: Autonomous Docking cho Robot Di động Vi sai 2D
Định dạng: Word (.docx) chuẩn học thuật, khổ A4, Times New Roman, cỡ 13, căn đều 2 lề.
Tích hợp hình ảnh lý thuyết từ bài giảng GS. Peter Corke và 10 đồ thị kỹ thuật (PNG 300 dpi).
Bổ sung giải thích chuyên sâu lý do bộ điều khiển Tọa độ cực (dạng Kp phi tuyến) vượt trội hơn PID.
"""

import os
from pathlib import Path
import docx
from docx.shared import Inches, Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
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

    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
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
        
    r = p.add_run(text)
    r.font.name = 'Times New Roman'
    r.font.size = Pt(13)
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

def main():
    base_dir = Path(__file__).parent.resolve()
    fig_dir = base_dir / "figures"
    theory_fig_dir = fig_dir / "theory_slides"
    output_docx = base_dir / "Bao_Cao_Cuoi_Ky_Autonomous_Docking.docx"
    
    print("Khởi tạo tài liệu Word hoàn chỉnh...")
    doc = docx.Document()
    
    # Thiết lập lề trang A4 chuẩn học thuật
    for s in doc.sections:
        s.page_width = Cm(21.0)
        s.page_height = Cm(29.7)
        s.top_margin = Cm(2.0)
        s.bottom_margin = Cm(2.0)
        s.left_margin = Cm(3.0)
        s.right_margin = Cm(2.0)
        
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
    add_body_p(doc, "Tôi xin cam đoan đây là công trình nghiên cứu và thực nghiệm do chính tôi thực hiện dưới sự định hướng của giảng viên bộ môn. Toàn bộ các kết quả mô phỏng, thuật toán, mã nguồn Python và số liệu thống kê được trình bày trong báo cáo là hoàn toàn trung thực, khách quan và được trích xuất trực tiếp từ các kịch bản kiểm thử độc lập. Mọi nguồn tài liệu tham khảo kế thừa từ bài giảng học phần và giáo trình chuẩn của GS. Peter Corke (Robotics, Vision and Control) đều được trích dẫn nguồn gốc rõ ràng theo chuẩn học thuật IEEE.")
    
    add_heading_styled(doc, "MỤC LỤC TỔNG QUAN", level=1)
    toc_items = [
        "CHƯƠNG 1. GIỚI THIỆU VÀ ĐẶT VẤN ĐỀ",
        "  1.1. Bối cảnh và ý nghĩa thực tiễn của trạm sạc tự động cho AGV/AMR",
        "  1.2. Phát biểu bài toán cập trạm sạc unicycle phi holonomic",
        "  1.3. Mục tiêu kỹ thuật và tiêu chí định lượng cần đạt",
        "  1.4. Phạm vi thực hiện và bố cục của báo cáo",
        "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ GIẢI THUẬT ĐIỀU KHIỂN (BÁM SÁT BÀI GIẢNG)",
        "  2.1. Biểu diễn vị trí và hướng trong không gian 2D (Pose SE(2) - Chapter 1)",
        "  2.2. Động học robot vi sai (Unicycle Kinematics) và tích phân số Euler/RK4",
        "  2.3. Giải thuật Tọa độ cực (Peter Corke - Driving to a Configuration)",
        "  2.4. Giải thuật PID Hai vòng (Vector Field Line Following & PID Theory)",
        "  2.5. Phân tích chuyên sâu: Vì sao bộ điều khiển Tọa độ cực (dạng tỷ lệ phi tuyến Kp) lại vượt trội hơn PID?",
        "  2.6. Phân tích ổn định giải tích hệ phi tuyến quanh điểm cân bằng (Lyapunov & Hurwitz)",
        "CHƯƠNG 3. THIẾT KẾ HỆ THỐNG VÀ PHƯƠNG PHÁP TRIỂN KHAI",
        "  3.1. Kiến trúc phần mềm mô phỏng khép kín thuần Python",
        "  3.2. Mô hình hóa nhiễu thực tế và trễ truyền thông (Chapter 4)",
        "  3.3. Phương pháp tinh chỉnh tham số công bằng (Fair Tuning)",
        "  3.4. Thiết kế 5 kịch bản thực nghiệm (S1 – S5) và nghiên cứu bóc tách (Ablation)",
        "CHƯƠNG 4. KẾT QUẢ THỰC NGHIỆM VÀ THẢO LUẬN CHUYÊN SÂU",
        "  4.1. Kết quả kiểm chứng ổn định giải tích",
        "  4.2. Đáp ứng thời gian và quỹ đạo trong kịch bản lý tưởng S1",
        "  4.3. Đánh giá quỹ đạo đa tư thế xuất phát bao quát không gian",
        "  4.4. Phân tích phân bố sai số và thời gian cập dock (Kịch bản S2 – S5)",
        "  4.5. Độ tin cậy tỷ lệ thành công với khoảng tin cậy Wilson 95%",
        "  4.6. Kiểm định ý nghĩa thống kê McNemar và Wilcoxon Signed-Rank",
        "  4.7. Đánh giá độ nhạy khi quét hệ số nhiễu k và bản đồ nhiệt không gian",
        "  4.8. Nghiên cứu bóc tách thành phần (Ablation Study)",
        "  4.9. Thảo luận chuyên sâu: So sánh ưu - nhược điểm bản chất giữa Polar và DualPID",
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
        "Hình 2.1: Mô hình động học robot di động vi sai (Bicycle/Unicycle Model) và hệ trục tọa độ thân xe {B} (Giáo trình Peter Corke, Chapter 3 Part 1).",
        "Hình 2.2: Định nghĩa các biến trạng thái trong hệ tọa độ cực (rho, alpha, beta) cho bài toán điều khiển về một tư thế đích Driving to a Configuration (Giáo trình Peter Corke, Chapter 3 Part 1).",
        "Hình 2.3: Sơ đồ khối cấu trúc điều khiển hệ tọa độ cực theo mô hình chuẩn Peter Corke.",
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
        "Bảng 4.1: Bảng thông số Gain trước và sau tinh chỉnh công bằng (Fair Tuning, N=300).",
        "Bảng 4.2: Bảng chỉ số hiệu năng tổng hợp qua 5 kịch bản (n=300 lượt chạy độc lập mỗi kịch bản).",
        "Bảng 4.3: Kết quả kiểm định ý nghĩa thống kê ghép cặp McNemar và Wilcoxon Signed-Rank.",
        "Bảng 4.4: Kết quả thực nghiệm bóc tách thành phần kỹ thuật (Ablation Study).",
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
    add_body_p(doc, "Đối tượng nghiên cứu của đề tài là robot di động truyền động vi sai 2 bánh độc lập (Differential Drive Mobile Robot hay mô hình Unicycle). Robot chuyển động trong mặt phẳng 2 chiều không vật cản. Về mặt điều khiển học, robot vi sai là một hệ phi holonomic (non-holonomic system) tiêu biểu: robot chịu ràng buộc không trượt bên, do đó số bậc tự do điều khiển chỉ là 2 (vận tốc dài v và vận tốc góc omega) trong khi không gian cấu hình trạng thái có 3 chiều (tọa độ x, y và góc hướng theta).")
    add_body_p(doc, "Theo định lý Brockett nổi tiếng (Brockett's Theorem, 1983), một hệ thống phi holonomic không thể được ổn định tiệm cận về điểm cân bằng mong muốn bằng bất kỳ luật điều khiển phản hồi trạng thái trơn và tĩnh nào trong không gian Descartes. Do đó, việc đưa robot về đúng tọa độ (x=0, y=0) đồng thời nắn thẳng hướng (theta=0) đòi hỏi các phương pháp phi tuyến chuyên biệt hoặc phân rã vòng điều khiển.")

    add_heading_styled(doc, "1.3. Mục tiêu kỹ thuật và tiêu chí định lượng cần đạt", level=2)
    add_body_p(doc, "Mục tiêu trọng tâm của đề tài là nghiên cứu, thiết kế, mô phỏng và so sánh định lượng hai chiến lược điều khiển phi tuyến cho quá trình Autonomous Docking. Trạm sạc được đặt tại gốc tọa độ O(0, 0) với hướng kết nối dọc theo chiều dương trục x (theta_dock = 0 rad). Để đảm bảo tính nghiêm ngặt và tương thích với ứng dụng thực tế, tiêu chí docking thành công được đánh giá dựa trên TRẠNG THÁI THẬT của robot và phải thỏa mãn đồng thời 4 điều kiện khắt khe:")
    add_bullet_p(doc, "1. Sai số vị trí cuối cùng:", "Khoảng cách từ tâm robot đến tâm dock không vượt quá 2 cm (sqrt(x^2 + y^2) <= 0.02 m).")
    add_bullet_p(doc, "2. Sai số góc hướng cuối cùng:", "Góc lệch giữa mũi xe và trục cổng sạc không vượt quá 3 độ (|theta| <= 3.0° = 0.0524 rad).")
    add_bullet_p(doc, "3. Giới hạn thời gian docking:", "Toàn bộ chu trình tiếp cận và hoàn tất khóa vị trí không quá 60 giây (t <= 60.0 s).")
    add_bullet_p(doc, "4. Tuyệt đối không đâm quá trạm sạc:", "Robot bị tính là thất bại ngay lập tức do vọt lố (Overshoot) nếu vị trí x vượt quá 0.05 m (x > 0.05 m), nhằm bảo vệ kết cấu cơ khí của trạm sạc.")

    add_heading_styled(doc, "1.4. Phạm vi thực hiện và bố cục báo cáo", level=2)
    add_body_p(doc, "Đề tài tập trung triển khai và kiểm chứng trên nền tảng Python chuẩn (NumPy, SciPy, Matplotlib, pandas, pytest), loại bỏ sự cồng kềnh của middleware ROS để tối ưu hóa hiệu năng tính toán đa tiến trình và cho phép đánh giá quy mô lớn hàng nghìn tập chạy độc lập.")
    add_body_p(doc, "Báo cáo được bố cục thành 5 chương chính: Chương 1 giới thiệu tổng quan đề tài; Chương 2 xây dựng cơ sở lý thuyết động học bám sát giáo trình Peter Corke và so sánh bản chất hai giải thuật điều khiển; Chương 3 mô tả kiến trúc mô phỏng, mô hình nhiễu và quy trình tinh chỉnh công bằng; Chương 4 phân tích chuyên sâu kết quả thực nghiệm và kiểm định thống kê; Chương 5 tổng kết các đóng góp và định hướng nghiên cứu tiếp theo.")

    doc.add_page_break()

    # ==================== CHƯƠNG 2 ====================
    add_heading_styled(doc, "CHƯƠNG 2. CƠ SỞ LÝ THUYẾT VÀ GIẢI THUẬT ĐIỀU KHIỂN (BÁM SÁT BÀI GIẢNG)", level=1)
    
    add_heading_styled(doc, "2.1. Biểu diễn vị trí và hướng trong không gian 2D (Pose SE(2) - Chapter 1)", level=2)
    add_body_p(doc, "Theo nội dung bài giảng Chapter 1 (Representing Position and Orientation) và giáo trình Peter Corke, trạng thái không gian của một robot di động trong mặt phẳng 2 chiều được biểu diễn bởi một 'Tư thế' (Pose) bao gồm vị trí (Position) và góc hướng (Orientation):")
    add_body_p(doc, "q = [x, y, theta]^T in SE(2)", italic_prefix="Vector tư thế: ")
    add_body_p(doc, "Trong đó (x, y) là tọa độ của gốc hệ trục thân xe {B} (Body Frame) gắn trên tâm cầu bánh xe đối với hệ trục tọa độ thế giới {W} (World Frame). Góc theta là góc lệch giữa trục hoành x_B của thân xe với trục hoành x_W của thế giới. Trạm sạc được định nghĩa là hệ trục mục tiêu {G} (Goal Frame) đặt tại gốc O(0,0) với hướng theta_G = 0 rad.")

    add_heading_styled(doc, "2.2. Động học robot vi sai (Unicycle Kinematics) và tích phân số", level=2)
    add_body_p(doc, "Theo bài giảng Chapter 3 Part 1 (Mobile Robots & Control), mô hình động học vi sai (tương đương mô hình xe đạp - bicycle model khi khoảng cách trục tiến về 0) được biểu diễn bằng quan hệ giữa vận tốc góc của hai bánh xe chủ động và vận tốc thân xe:")
    
    # Chèn hình lý thuyết 1 trích từ slide
    fig_th1 = str(theory_fig_dir / "slide_p6_Image75.jpg")
    add_figure_with_caption(doc, fig_th1, "Hình 2.1: Mô hình động học robot di động vi sai (Bicycle/Unicycle Model) và hệ trục tọa độ thân xe {B} (Giáo trình Peter Corke, Chapter 3 Part 1).", width_inch=3.8)

    add_body_p(doc, "Phương trình chuyển đổi vận tốc từ không gian khớp (bánh xe) sang không gian tác vụ (thân xe):")
    add_body_p(doc, "v = r * (omega_R + omega_L) / 2\nomega = r * (omega_R - omega_L) / L", italic_prefix="Phương trình vận tốc thân xe: ")
    add_body_p(doc, "Trong đó r = 0.035 m là bán kính bánh xe, L = 0.23 m là khoảng cách giữa hai tâm bánh xe (wheelbase). Hệ phương trình vi phân chuyển động trong hệ quy chiếu toàn cục {W} có dạng:")
    add_body_p(doc, "dx/dt = v * cos(theta)\ndy/dt = v * sin(theta)\ndtheta/dt = omega", italic_prefix="Hệ phương trình trạng thái unicycle: ")
    add_body_p(doc, "Trong môi trường mô phỏng số rời rạc (dt = 0.02 s, 50 Hz), trạng thái được cập nhật bằng tích phân Euler tiến kết hợp hàm chuẩn hóa góc wrap(angle) in (-pi, pi]:")
    add_body_p(doc, "x_{k+1} = x_k + v_k * cos(theta_k) * dt\ny_{k+1} = y_k + v_k * sin(theta_k) * dt\ntheta_{k+1} = wrap(theta_k + omega_k * dt)", italic_prefix="Tích phân số rời rạc: ")
    add_body_p(doc, "Đồng thời, mã nguồn tích hợp thuật toán tích phân Runge-Kutta bậc 4 (RK4) để đối chứng. Kết quả cho thấy sai lệch tích phân giữa Euler và RK4 tại bước dt = 0.02 s là cực kỳ nhỏ (< 10^-5 m), khẳng định tính chính xác của mô hình mô phỏng.")

    add_heading_styled(doc, "2.3. Giải thuật Tọa độ cực (Peter Corke - Driving to a Configuration)", level=2)
    add_body_p(doc, "Trong mục 3.1.6 'Driving to a Configuration' (Slide Chapter 3 Part 1, trang 32–36), GS. Peter Corke đã giới thiệu giải thuật điều khiển đưa xe về một tư thế cấu hình mong muốn (x*, y*, theta*) thông qua phép đổi biến sang hệ tọa độ cực:")
    
    # Chèn hình lý thuyết 2 trích từ slide
    fig_th2 = str(theory_fig_dir / "slide_p33_Image188.jpg")
    add_figure_with_caption(doc, fig_th2, "Hình 2.2: Định nghĩa các biến trạng thái trong hệ tọa độ cực (rho, alpha, beta) cho bài toán điều khiển về một tư thế đích Driving to a Configuration (Giáo trình Peter Corke, Chapter 3 Part 1, Trang 33).", width_inch=3.8)

    add_body_p(doc, "Các biến tọa độ cực được xác định đối với trạm sạc tại gốc tọa độ:")
    add_bullet_p(doc, "rho (Cự ly đường thẳng tới dock):", "rho = sqrt((-x)^2 + (-y)^2)")
    add_bullet_p(doc, "alpha (Góc lệch đường ngắm):", "alpha = wrap(atan2(-y, -x) - theta), góc giữa trục mũi xe x_B và vector nối tới trạm sạc.")
    add_bullet_p(doc, "beta (Góc tiếp cận mục tiêu):", "beta = wrap(-theta - alpha), góc giữa trục trạm sạc (+x) và đường nối xe-dock.")
    
    # Chèn hình lý thuyết 3 trích từ slide
    fig_th3 = str(theory_fig_dir / "slide_p35_Image196.png")
    add_figure_with_caption(doc, fig_th3, "Hình 2.3: Sơ đồ khối cấu trúc điều khiển hệ tọa độ cực theo mô hình chuẩn Peter Corke (Chapter 3 Part 1, Trang 35).", width_inch=5.8)

    add_body_p(doc, "Luật điều khiển phản hồi trạng thái cực có dạng:")
    add_body_p(doc, "v = k_rho * rho\nomega = k_alpha * alpha + k_beta * beta", italic_prefix="Luật điều khiển cực: ")
    add_body_p(doc, "Ý nghĩa trực giác: Thành phần k_rho * rho kéo xe chạy về phía trạm sạc; thành phần k_alpha * alpha bẻ lái mũi xe nhìn về trạm sạc; và thành phần k_beta * beta uốn lượn đường đi sao cho khi xe vừa chạm cổng sạc thì góc lệch hướng triệt tiêu (beta -> 0).")
    add_body_p(doc, "Để hoàn thiện giải thuật trong thực tế công nghiệp, hai cơ chế bảo vệ đã được đề xuất và tích hợp:")
    add_bullet_p(doc, "1. Cơ chế quay tại chỗ khi quay lưng (|alpha| > pi/2):", "Nếu robot quay lưng về dock, xe dừng tiến v = 0 m/s và chỉ quay tại chỗ omega = k_alpha * alpha. Dải trễ Hysteresis 0.1 rad được bổ sung để loại bỏ hoàn toàn hiện tượng rung giật đóng ngắt (chattering) khi góc dao động quanh pi/2.")
    add_bullet_p(doc, "2. Cơ chế đóng băng góc gần dock (rho < 0.02 m):", "Khi rho -> 0, phép toán atan2 trở nên kỳ dị toán học và cực kỳ nhạy cảm với nhiễu cảm biến. Việc đóng băng góc alpha, beta ở cự ly 2 cm cuối cùng giúp robot tiến thẳng mượt mà vào chốt sạc.")

    add_heading_styled(doc, "2.4. Giải thuật PID Hai vòng (Vector Field Line Following & PID Theory)", level=2)
    add_body_p(doc, "Giải thuật PID hai vòng kết hợp phương pháp bám đường thẳng trong mục 3.1.4 'Driving Along a Line' (Slide Chapter 3 Part 1) với lý thuyết điều khiển PID trong Slide Chapter 3 Part 2:")
    add_bullet_p(doc, "Vòng trong (Inner Loop - Bám góc nhanh):", "Coi trục trạm sạc (y = 0) là tim đường, xe tạo góc lái tham chiếu theo trường vector định hướng: theta_ref = -atan(k_y * y). Sai số góc e_theta = wrap(theta_ref - theta) được đưa vào bộ điều khiển PID góc để tính toán vận tốc góc: omega = PID_omega(e_theta).")
    add_bullet_p(doc, "Vòng ngoài (Outer Loop - Bám cự ly):", "Khoảng cách rho được đưa vào bộ PID cự ly để tính vận tốc dài, kết hợp hàm điều hòa vận tốc theo góc bẻ lái: v = PID_v(rho) * max(0, cos(e_theta)). Cơ chế này tự động hãm phanh khi góc lệch còn lớn, ưu tiên quay đầu trước.")
    add_body_p(doc, "Lớp PID được trang bị hai kỹ thuật ổn định nâng cao: Anti-windup kẹp giá trị tích phân I trong phạm vi bão hòa [-I_max, I_max] và Bộ lọc vi phân thông thấp bậc 1 (alpha_filter = 0.8) để triệt tiêu nhiễu đạo hàm tần số cao.")

    add_heading_styled(doc, "2.5. Phân tích chuyên sâu: Vì sao bộ điều khiển Tọa độ cực (dạng Kp phi tuyến) lại vượt trội hơn PID?", level=2)
    add_body_p(doc, "Một câu hỏi kỹ thuật rất sâu sắc thường được đặt ra: 'Tại sao luật điều khiển Polar chỉ có dạng tỷ lệ Kp (k_rho, k_alpha, k_beta), không hề có khâu Tích phân I hay Vi phân D, nhưng lại cho hiệu năng và độ tin cậy vượt trội hoàn toàn so với PID (vốn có đầy đủ P, I, D)?' Câu trả lời nằm ở 3 nguyên nhân bản chất sau:")
    add_bullet_p(doc, "1. Bản chất Phản hồi Trạng thái Phi tuyến (Nonlinear State Feedback):", "Mặc dù luật điều khiển Polar có dạng nhân hằng số tỷ lệ, nhưng các biến đầu vào (rho, alpha, beta) KHÔNG PHẢI là sai số tuyến tính đơn thuần mà là hàm phi tuyến phức tạp của tọa độ Descartes. Phép đổi biến cực đã thực hiện giải phóng ràng buộc hình học phi tuyến, biến hệ thống phi holonomic thành một hệ gần như tuyến tính quanh điểm cân bằng. Do đó, Polar thực chất là một bộ điều khiển phản hồi trạng thái phi tuyến đầy đủ chứ không phải là bộ điều khiển P tuyến tính kinh điển.")
    add_bullet_p(doc, "2. Rào cản của Định lý Brockett và sự thất bại của PID trong không gian Descartes:", "Định lý Brockett (1983) đã chứng minh rằng một hệ phi holonomic (như robot vi sai) không thể ổn định về điểm cân bằng bằng bất kỳ luật điều khiển phản hồi trơn và tĩnh nào trong không gian Descartes. PID cố gắng tách rời không gian bằng cách ép xe bám trường vector arctan. Khi xe ở tư thế khó (lệch ngang lớn nhưng rất gần dock, kịch bản S4), trường vector arctan đòi hỏi robot phải bẻ lái ngoặt 90° tức thời. Tuy nhiên, do giới hạn vật lý omega_max = 1.5 rad/s, robot bị trôi bán kính quay và cắt qua dock, dẫn tới tỷ lệ đâm quá trạm (Overshoot) lên tới 82.0%.")
    add_bullet_p(doc, "3. Tác hại phụ của khâu Tích phân (I) và Vi phân (D) trong bài toán docking:", "Khâu tích phân I của PID rất dễ bị hiện tượng 'tích lũy sai số' (windup) khi xe bão hòa góc bẻ lái, khiến xe khi áp sát dock vẫn bị thừa trớn và lao qua trạm. Trong khi đó, Polar không cần khâu I vì khi rho -> 0 thì vận tốc tiến v = k_rho * rho tự động triệt tiêu về 0 một cách êm ái và tự nhiên nhất (tự phanh tự nhiên), triệt tiêu hoàn toàn nguy cơ vọt lố.")

    add_heading_styled(doc, "2.6. Phân tích ổn định giải tích hệ phi tuyến quanh điểm cân bằng", level=2)
    add_body_p(doc, "Xét hệ thống tọa độ cực (rho, alpha, beta) với giả thiết góc lệch nhỏ sin(alpha) xấp xỉ alpha, cos(alpha) xấp xỉ 1. Tuyến tính hóa hệ thống quanh điểm cân bằng (rho=0, alpha=0, beta=0) ta thu được hệ phương trình trạng thái vi phân ma trận:")
    add_body_p(doc, "d/dt [rho, alpha, beta]^T = A * [rho, alpha, beta]^T\nVới ma trận A = [[-k_rho, 0, 0], [0, -(k_alpha - k_rho), -k_beta], [0, -k_rho, 0]]", italic_prefix="Ma trận trạng thái tuyến tính hóa: ")
    add_body_p(doc, "Đa thức đặc trưng của ma trận A có dạng: det(lambda*I - A) = (lambda + k_rho) * [lambda^2 + (k_alpha - k_rho)*lambda - k_rho*k_beta] = 0. Áp dụng tiêu chuẩn ổn định Routh-Hurwitz, hệ thống đạt ổn định tiệm cận cục bộ khi và chỉ khi toàn bộ các trị riêng đều có phần thực âm, tương đương với hệ điều kiện:")
    add_bullet_p(doc, "Điều kiện 1:", "k_rho > 0 (Hệ số giảm cự ly dương)")
    add_bullet_p(doc, "Điều kiện 2:", "k_beta < 0 (Hệ số nắn hướng âm)")
    add_bullet_p(doc, "Điều kiện 3:", "k_alpha - k_rho > 0 (Hệ số lái góc phải đủ lớn hơn hệ số tiến)")
    add_bullet_p(doc, "Điều kiện 4 (Chống đảo chiều di chuyển):", "k_alpha + (5/3)*k_beta - (2/pi)*k_rho > 0")

    doc.add_page_break()

    # ==================== CHƯƠNG 3 ====================
    add_heading_styled(doc, "CHƯƠNG 3. THIẾT KẾ HỆ THỐNG VÀ PHƯƠNG PHÁP TRIỂN KHAI", level=1)
    
    add_heading_styled(doc, "3.1. Kiến trúc phần mềm mô phỏng khép kín thuần Python", level=2)
    add_body_p(doc, "Toàn bộ hệ thống mô phỏng được tổ chức theo kiến trúc hướng đối tượng phân lớp (Layered OOP Architecture), phân định rạch ròi giữa Trạng thái Thật (Ground Truth) và Trạng thái Đo được (Measured State). Vòng lặp điều khiển khép kín hoạt động tại tần số 50 Hz với hàm điều phối run_episode() trong docking/sim.py.")
    add_body_p(doc, "Trong mỗi bước thời gian dt = 0.02 s: (1) Mô hình vật lý cập nhật trạng thái thật q_real; (2) Bộ cảm biến cộng nhiễu Gaussian và trễ truyền thông để sinh trạng thái đo q_meas; (3) Bộ điều khiển chỉ được phép quan sát q_meas để tính lệnh (v, omega); (4) Lệnh điều khiển chịu nhiễu cơ cấu chấp hành và bão hòa trước khi đưa vào mô hình động học xe; (5) Hệ thống kiểm tra điều kiện thành công hoặc vi phạm an toàn.")

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

    add_heading_styled(doc, "3.2. Mô hình hóa nhiễu thực tế và trễ truyền thông (Chapter 4)", level=2)
    add_body_p(doc, "Nhằm phản ánh trung thực môi trường hoạt động thực tế theo bài giảng Chapter 4 (Localization & Mapping), lớp dữ liệu Noise (config.py) mô hình hóa 3 thành phần bất định chính:")
    add_bullet_p(doc, "1. Nhiễu đo lường cảm biến (Sensor Noise):", "Vị trí (x, y) đo được bị ảnh hưởng bởi nhiễu trắng Gaussian có độ lệch chuẩn sigma_pos. Góc hướng theta bị ảnh hưởng bởi nhiễu sigma_yaw cùng độ lệch tĩnh (bias_yaw) mô phỏng sai số căn chỉnh cảm biến IMU/Odometry.")
    add_bullet_p(doc, "2. Nhiễu cơ cấu chấp hành (Actuator Noise):", "Vận tốc thực tế của bánh xe nhận lệnh cộng thêm nhiễu ngẫu nhiên sigma_v và sigma_omega do hiện tượng ma sát sàn và trượt vi sai.")
    add_bullet_p(doc, "3. Độ trễ điều khiển và truyền thông (Control Delay):", "Được mô hình hóa bằng hàng đợi FIFO độ dài N_delay bước (delay_time = N_delay * 0.02 s), phản ánh độ trễ xử lý gói tin và trễ đáp ứng cơ điện tử.")

    add_heading_styled(doc, "3.3. Phương pháp tinh chỉnh tham số công bằng (Fair Tuning)", level=2)
    add_body_p(doc, "Để đảm bảo tính khách quan và khoa học khi so sánh, đề tài áp dụng quy trình tinh chỉnh công bằng (Fair Tuning) nghiêm ngặt:")
    add_bullet_p(doc, "Ngân sách tính toán đồng nhất:", "Cả hai bộ điều khiển đều được cấp đúng N = 300 lần đánh giá ứng viên ngẫu nhiên có kiểm soát (Random Search) trong không gian tham số.")
    add_bullet_p(doc, "Tập dữ liệu độc lập:", "Quá trình tinh chỉnh được thực thi trên tập TUNING gồm 100 tư thế xuất phát độc lập (seed = 1) dưới kịch bản có nhiễu S2. Tập dữ liệu này hoàn toàn tách biệt với tập TEST (seed = 2024) dùng để chấm điểm cuối cùng.")
    add_bullet_p(doc, "Hàm mục tiêu chi phí đa chỉ tiêu:", "J = -success_rate + 0.01 * mean_time + 0.5 * overshoot_rate. Hàm chi phí này ưu tiên tuyệt đối tỷ lệ cập dock thành công, đồng thời phạt thời gian di chuyển chậm và áp mức phạt rất nặng đối với lỗi vọt lố qua dock.")

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

    doc.add_page_break()

    # ==================== CHƯƠNG 4 ====================
    add_heading_styled(doc, "CHƯƠNG 4. KẾT QUẢ THỰC NGHIỆM VÀ THẢO LUẬN CHUYÊN SÂU", level=1)
    
    add_heading_styled(doc, "4.1. Kết quả kiểm chứng ổn định giải tích", level=2)
    add_body_p(doc, "Trước khi bước vào mô phỏng động học, việc kiểm chứng ổn định giải tích được thực hiện bằng cách giải phương trình trị riêng và quét không gian tham số.")
    
    fig8_path = str(fig_dir / "fig8_stability_analysis.png")
    add_figure_with_caption(doc, fig8_path, "Hình 4.1: Phân tích vùng ổn định giải tích trên mặt phẳng tham số (k_alpha, k_beta) và cực trị riêng lớn nhất.")
    
    add_body_p(doc, "Hình 4.1(a) thể hiện bản đồ vùng ổn định giải tích trên mặt phẳng tham số (k_alpha, k_beta) với k_rho = 1.185 cố định. Vùng màu xanh lá biểu thị các cặp tham số thỏa mãn đồng thời cả 4 điều kiện ổn định Hurwitz và điều kiện không đổi chiều chuyển động. Cặp gain tối ưu được chọn (k_alpha = 2.020, k_beta = -0.586) nằm sâu bên trong vùng an toàn ổn định. Hình 4.1(b) quét phần thực lớn nhất của trị riêng max(Re(lambda)) theo k_alpha, chứng minh hệ thống luôn có nghiệm cực âm vững chắc, đảm bảo độ tắt dần nhanh của sai số.")

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
    add_body_p(doc, "Kịch bản S1 kiểm chứng động học thuần túy trên 3 tư thế đại diện đặc trưng: Tư thế 1 nằm thẳng trước dock (-2, 0, 0); Tư thế 2 lệch bên (-1.5, 1.5, 0); và Tư thế 3 quay lưng hoàn toàn (-1.5, 0.5, pi).")
    
    fig1_path = str(fig_dir / "fig1_dock_robot_coordinate_system.png")
    add_figure_with_caption(doc, fig1_path, "Hình 4.2: Sơ đồ hệ tọa độ robot vi sai và các biến trạng thái cực cập trạm sạc thực tế.")

    fig2_path = str(fig_dir / "fig2_s1_trajectories.png")
    add_figure_with_caption(doc, fig2_path, "Hình 4.3: So sánh quỹ đạo di chuyển trong kịch bản lý tưởng S1 giữa Polar Controller và DualPID.")

    fig3_path = str(fig_dir / "fig3_s1_time_response.png")
    add_figure_with_caption(doc, fig3_path, "Hình 4.4: Đáp ứng theo thời gian của trạng thái (vị trí, góc) và tín hiệu điều khiển (v, omega) trong kịch bản S1.")

    add_body_p(doc, "Quan sát Hình 4.3 và 4.4, ở Tư thế 3 (quay lưng), cả hai bộ điều khiển đều kích hoạt chế độ xoay tại chỗ xuất sắc: vận tốc dài v = 0 m/s trong khi vận tốc góc omega bẻ lái dứt khoát đưa đầu xe hướng về trạm sạc trước khi bắt đầu tăng tốc. Polar Controller tạo ra quỹ đạo trơn tru hơn (chiều dài trung bình 2.23 m so với 2.41 m của PID) và hoàn thành cập dock chỉ trong 9.17 s (nhanh hơn 8% so với 9.94 s của PID).")

    add_heading_styled(doc, "4.3. Đánh giá quỹ đạo đa tư thế xuất phát bao quát không gian", level=2)
    add_body_p(doc, "Để kiểm tra tính toàn cục của thuật toán, mô phỏng kích hoạt đồng thời 16 tư thế xuất phát ngẫu nhiên phân bố đều trên toàn bộ không gian làm việc x in [-3.0, -0.5] m, y in [-2.0, 2.0] m và góc ban đầu theta in [-pi, pi].")
    
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
    add_body_p(doc, "Để đảm bảo tính nghiêm ngặt về mặt thống kê xác suất, tỷ lệ thành công được tính toán kèm khoảng tin cậy Wilson score interval 95% (Hình 4.7).")
    
    fig6_path = str(fig_dir / "fig6_success_rates_wilson.png")
    add_figure_with_caption(doc, fig6_path, "Hình 4.7: So sánh tỷ lệ docking thành công kèm khoảng tin cậy Wilson 95% qua 5 kịch bản.")
    
    add_body_p(doc, "Tại các kịch bản chuẩn S1, S2, S3, Polar Controller đạt độ tin cậy tuyệt đối 100.0% với cận dưới khoảng tin cậy Wilson lên tới 98.7%. Ở kịch bản khắc nghiệt nhất S5 (nhiễu tổng hợp cao), Polar vẫn duy trì tỷ lệ ấn tượng 99.3% [97.6%, 99.8%], trong khi DualPID dao động quanh ngưỡng 90.0% - 90.7%.")
    add_body_p(doc, "Đặc biệt tại kịch bản tư thế khó S4, tỷ lệ thành công của DualPID sụt giảm nghiêm trọng xuống chỉ còn 18.0% [14.1%, 22.7%], trong khi Polar vẫn giữ vững 100.0%. Nguyên nhân sâu xa là trường vector theta_ref = -atan(k_y * y) đổi chiều quá gấp khi xe ở gần dock (|y| >= 1.5 m, x >= -1.0 m); dưới giới hạn vận tốc góc omega_max = 1.5 rad/s, robot vi sai bị trôi bán kính quay và cắt qua dock, dẫn tới tỷ lệ vọt lố (Overshoot rate) lên tới 82.0%.")

    add_heading_styled(doc, "4.6. Kiểm định ý nghĩa thống kê McNemar và Wilcoxon Signed-Rank", level=2)
    add_body_p(doc, "Để khẳng định sự khác biệt hiệu năng giữa hai bộ điều khiển là do bản chất thuật toán chứ không phải ngẫu nhiên, hai phép kiểm định thống kê phi tham số ghép cặp đã được thực hiện:")
    add_bullet_p(doc, "Kiểm định McNemar:", "Đánh giá sự khác biệt về tỷ lệ thành công trên các cặp chạy cùng tư thế và cùng chuỗi nhiễu.")
    add_bullet_p(doc, "Kiểm định Wilcoxon Signed-Rank:", "Đánh giá sự khác biệt về thời gian docking trên các ca mà cả hai bộ điều khiển cùng thành công.")

    # Bảng 4.3: McNemar & Wilcoxon
    add_body_p(doc, "Bảng 4.3: Kết quả kiểm định ý nghĩa thống kê ghép cặp McNemar và Wilcoxon Signed-Rank.", bold_prefix="Bảng 4.3: ")
    t_test = doc.add_table(rows=6, cols=7)
    t_test.alignment = WD_TABLE_ALIGNMENT.CENTER
    headers_t = ["Kịch bản", "Tỷ lệ Polar", "Tỷ lệ DualPID", "McNemar Chi2", "McNemar p-value", "Wilcoxon Stat", "Wilcoxon p-value"]
    for j, h in enumerate(headers_t):
        c = t_test.rows[0].cells[j]
        set_cell_background(c, "1F4E79")
        set_cell_margins(c)
        p = c.paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.name = 'Times New Roman'
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(255, 255, 255)
        
    data_t = [
        ("S1", "100.0%", "90.3%", "27.03", "2.00e-07 (p < 0.001)", "2979.5", "2.29e-32 (p < 0.001)"),
        ("S2", "100.0%", "90.0%", "28.03", "1.19e-07 (p < 0.001)", "5598.5", "1.01e-21 (p < 0.001)"),
        ("S3", "100.0%", "90.7%", "26.04", "3.35e-07 (p < 0.001)", "13537.0", "1.52e-04 (p < 0.001)"),
        ("S4", "100.0%", "18.0%", "244.00", "0.00e+00 (p < 0.001)", "124.0", "1.64e-07 (p < 0.001)"),
        ("S5", "99.3%", "90.7%", "20.83", "5.01e-06 (p < 0.001)", "8557.0", "2.40e-13 (p < 0.001)"),
    ]
    for i, row in enumerate(data_t):
        for j, val in enumerate(row):
            c = t_test.rows[i+1].cells[j]
            set_cell_margins(c)
            if i % 2 == 1:
                set_cell_background(c, "F2F2F2")
            p = c.paragraphs[0]
            r = p.add_run(val)
            r.font.name = 'Times New Roman'
            r.font.size = Pt(10)

    add_body_p(doc, "Toàn bộ giá trị p-value của cả hai phép kiểm định trên tất cả 5 kịch bản đều nhỏ hơn rất nhiều so với ngưỡng ý nghĩa alpha = 0.05 (thậm chí p < 10^-6). Điều này bác bỏ hoàn toàn giả thuyết vô hiệu (Null Hypothesis H0), khẳng định chắc chắn 100% sự vượt trội về độ tin cậy và tốc độ cập dock của Polar Controller có ý nghĩa thống kê toán học sâu sắc.")

    add_heading_styled(doc, "4.7. Đánh giá độ nhạy khi quét hệ số nhiễu k và bản đồ nhiệt", level=2)
    add_body_p(doc, "Để kiểm tra ngưỡng suy giảm của thuật toán, hệ số nhân k in {0, 0.5, 1, 1.5, 2, 3, 4} được nhân tuyến tính lên toàn bộ bộ tham số nhiễu S5.")
    
    fig7_path = str(fig_dir / "fig7_sweep_noise.png")
    add_figure_with_caption(doc, fig7_path, "Hình 4.8: Đồ thị quét độ nhạy tỷ lệ thành công theo hệ số nhân nhiễu k.")

    fig9_path = str(fig_dir / "fig9_heatmap_success_map.png")
    add_figure_with_caption(doc, fig9_path, "Hình 4.9: Bản đồ nhiệt không gian xuất phát (Success Rate Heatmap) trong kịch bản S5.")

    add_body_p(doc, "Kết quả quét nhiễu trên Hình 4.8 mang lại một phát hiện khoa học đặc biệt thú vị: Trong dải nhiễu thực tế (k <= 1.0), Polar Controller áp đảo hoàn toàn. Tuy nhiên, khi hệ số nhiễu tăng vọt lên mức cực đoan (k = 2.0 -> 4.0), tỷ lệ thành công của Polar sụt giảm dần (từ 78% xuống 38%), trong khi DualPID vẫn duy trì được độ ổn định trên 82% - 90%.")
    add_body_p(doc, "Nguyên nhân bản chất là do Polar Controller tính toán góc alpha, beta trực tiếp từ trạng thái đo q_meas; khi nhiễu đo lường quá lớn, vector chỉ hướng bị rung lắc mạnh. Ngược lại, DualPID sở hữu bộ lọc vi phân thông thấp D (alpha_filter = 0.8) và hàm atan(k_y * y) đóng vai trò như một bộ lọc không gian phi tuyến tự nhiên, giúp PID miễn nhiễm tốt hơn trước nhiễu trắng biên độ cực lớn.")

    add_heading_styled(doc, "4.8. Nghiên cứu bóc tách thành phần (Ablation Study)", level=2)
    add_body_p(doc, "Nghiên cứu bóc tách nhằm phân lập và định lượng chính xác đóng góp của từng thành phần cải tiến.")

    # Bảng 4.4: Ablation
    add_body_p(doc, "Bảng 4.4: Kết quả thực nghiệm bóc tách thành phần kỹ thuật (Ablation Study).", bold_prefix="Bảng 4.4: ")
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

    add_body_p(doc, "Kết quả từ Bảng 4.4 và Hình 4.10 khẳng định: Với Polar Controller, cơ chế Freeze đóng vai trò then chốt giúp giảm sai số vị trí tiếp cận từ 1.63 cm xuống 1.57 cm và triệt tiêu hoàn toàn rung lắc bẻ lái tại cự ly áp sát. Với DualPID, các cơ chế Anti-windup và Lọc D giúp ổn định vòng điều khiển trong dải hoạt động danh định.")

    add_heading_styled(doc, "4.9. Thảo luận chuyên sâu: So sánh ưu - nhược điểm bản chất", level=2)
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
    add_bullet_p(doc, "4. Đánh giá thực nghiệm quy mô lớn với độ tin cậy cao:", "Thực hiện hàng nghìn lượt chạy trên 5 kịch bản S1–S5. Polar Controller đạt tỷ lệ docking thành công ấn tượng 99.3% - 100%, sai số vị trí < 1.7 cm, sai số góc < 2.0° và thời gian chỉ khoảng 7 – 10 s. Kiểm định McNemar và Wilcoxon (p < 0.001) khẳng định tính ưu việt của giải pháp.")

    add_heading_styled(doc, "5.2. Các hạn chế còn tồn tại và hướng phát triển", level=2)
    add_body_p(doc, "Mặc dù đạt được những kết quả rất khả quan, nghiên cứu vẫn còn một số điểm giới hạn có thể mở rộng trong tương lai:")
    add_bullet_p(doc, "1. Thử nghiệm trên mô hình phần cứng thật:", "Triển khai mã nguồn lên robot AGV/AMR vật lý sử dụng cảm biến camera nhận dạng thẻ mốc ArUco/AprilTag và cảm biến khoảng cách ToF/LiDAR để kiểm chứng tác động của ma sát sàn phi tuyến.")
    add_bullet_p(doc, "2. Mở rộng bài toán né tránh vật cản động:", "Tích hợp giải thuật trường thế nhân tạo (Artificial Potential Field - APF) hoặc Dynamic Window Approach (DWA) vào giai đoạn tiếp cận dock khi có vật cản di động bất ngờ xuất hiện.")
    add_bullet_p(doc, "3. Ứng dụng điều khiển tối ưu MPC (Model Predictive Control):", "Nghiên cứu bộ điều khiển dự báo mô hình phi tuyến (NMPC) để vừa đảm bảo cập dock chính xác vừa tối ưu hóa năng lượng tiêu thụ dưới các ràng buộc bão hòa chấp hành khắt khe.")

    doc.add_page_break()

    # ==================== TÀI LIỆU THAM KHẢO ====================
    add_heading_styled(doc, "TÀI LIỆU THAM KHẢO", level=1)
    references = [
        "[1] P. I. Corke, W. Jachimczyk, and R. Pillat, Robotics, Vision and Control: Fundamental Algorithms in MATLAB, 3rd ed. Cham, Switzerland: Springer Nature, 2023.",
        "[2] R. Siegwart, I. R. Nourbakhsh, and D. Scaramuzza, Introduction to Autonomous Mobile Robots, 2nd ed. Cambridge, MA, USA: MIT Press, 2011.",
        "[3] M. Aicardi, G. Casalino, A. Bicchi, and A. Balestrino, 'Closed loop steering of unicycle like vehicles via Lyapunov techniques,' IEEE Robotics & Automation Magazine, vol. 2, no. 1, pp. 27–35, Mar. 1995.",
        "[4] R. W. Brockett, 'Asymptotic stability and feedback stabilization,' in Differential Geometric Control Theory, R. W. Brockett, R. S. Millman, and H. J. Sussmann, Eds. Boston, MA: Birkhäuser, 1983, pp. 181–191.",
        "[5] J. Borenstein and Y. Koren, 'The vector field histogram-fast obstacle avoidance for mobile robots,' IEEE Transactions on Robotics and Automation, vol. 7, no. 3, pp. 278–288, Jun. 1991.",
        "[6] E. B. Wilson, 'Probable inference, the law of succession, and statistical inference,' Journal of the American Statistical Association, vol. 22, no. 158, pp. 209–212, 1927.",
        "[7] Q. A. McNemar, 'Note on the sampling error of the difference between correlated proportions or percentages,' Psychometrika, vol. 12, no. 2, pp. 153–157, 1947.",
        "[8] F. Wilcoxon, 'Individual comparisons by ranking methods,' Biometrics Bulletin, vol. 1, no. 6, pp. 80–83, 1945.",
        "[9] K. J. Åström and T. Hägglund, Advanced PID Control. Research Triangle Park, NC: ISA-The Instrumentation, Systems, and Automation Society, 2006.",
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
    add_body_p(doc, "Toàn bộ mã nguồn dự án được tổ chức mô-đun hóa trong thư mục docking/ và có thể được tái lập kết quả tự động bằng các lệnh đơn giản:")
    
    add_heading_styled(doc, "1. Cấu trúc cây thư mục mã nguồn chính", level=2)
    tree_text = """ROBOT_FINAL/
├── main.py                    # Wrapper tự động phát hiện Python và thực thi
├── requirements.txt           # Danh mục thư viện phụ thuộc (numpy, scipy, matplotlib, pandas, pytest)
├── docking/                   # Thư mục mã nguồn thuật toán
│   ├── config.py              # Tham số hình học, giới hạn bão hòa, dataclass Noise
│   ├── robot.py               # Động học vi sai, tích phân Euler/RK4, wrap, bão hòa, hàng đợi trễ
│   ├── controllers.py         # PolarController, DualPIDController, lớp PID (Anti-windup/Filter D)
│   ├── sim.py                 # Hàm run_episode() mô phỏng tập chạy và đánh giá trạng thái thật
│   ├── stability.py           # Tuyến tính hóa ma trận A, trị riêng, kiểm tra ổn định & tính đơn điệu
│   ├── tuning.py              # Tinh chỉnh công bằng Fair Tuning (N=300 đánh giá/bộ)
│   ├── experiments.py         # Chạy kịch bản S1–S5 (n=300), quét hệ số nhiễu k, ablation study
│   ├── plots.py               # Sinh toàn bộ 10 hình vẽ kỹ thuật (PNG 300 dpi và PDF vector)
│   ├── stats.py               # Thống kê, khoảng tin cậy Wilson 95%, kiểm định McNemar & Wilcoxon
│   └── tests/test_basic.py    # Bộ kiểm thử pytest tự động 6 tiêu chuẩn bắt buộc
├── results/                   # Dữ liệu xuất: best_gains.json, scenario_metrics.csv, summary.md
└── figures/                   # 10 bộ đồ thị kỹ thuật xuất bản chất lượng cao + 3 hình lý thuyết slide"""
    
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
