# BÁO CÁO TỔNG HỢP KẾT QUẢ MÔ PHỎNG AUTONOMOUS DOCKING

## 1. Bảng thông số Gain trước và sau tinh chỉnh công bằng (Fair Tuning)

*Ngân sách tinh chỉnh: N=300 ứng viên mỗi bộ điều khiển trên 100 tư thế xuất phát (seed 1, kịch bản S2)*

| Bộ điều khiển | Tham số | Giá trị ban đầu | Giá trị sau tinh chỉnh | Ý nghĩa kỹ thuật |
|---|---|---|---|---|
| **Polar** | $k_\rho$ | 0.5 | **1.1851** | Hệ số suy giảm cự ly tới dock |
| | $k_\alpha$ | 1.5 | **2.0196** | Hệ số bẻ lái theo đường ngắm |
| | $k_\beta$ | -0.5 | **-0.5856** | Hệ số nắn hướng tiếp cận dock |
| **DualPID** | $K_{p,v}, K_{i,v}, K_{d,v}$ | (1.0, 0.0, 0.1) | **(1.555, 0.0045, 0.112)** | Vòng ngoài: Vận tốc dài |
| | $K_{p,\omega}, K_{i,\omega}, K_{d,\omega}$ | (3.0, 0.0, 0.2) | **(2.5857, 0.015, 0.0885)** | Vòng trong: Vận tốc góc |
| | $k_y$ | 2.0 | **3.4972** | Hệ số trường vector bám trục x |

## 2. Bảng chỉ số hiệu năng theo từng kịch bản (n=300 lượt chạy độc lập, seed 2024)

| Kịch bản | Bộ điều khiển | Tỷ lệ thành công (95% CI) | Thời gian docking (s, mean±std) | Thời gian median (s) | Sai số vị trí cuối (cm) | Sai số hướng cuối (độ) | Tỷ lệ Overshoot | Chiều dài quỹ đạo (m) | Năng lượng điều khiển |
|---|---|---|---|---|---|---|---|---|---|
| S1 | Polar | **100.0%** [98.7%, 100.0%] | 9.17 ± 2.26 | 9.14 | 1.94 ± 0.21 | 0.37° ± 0.64° | 0.0% | 2.23 ± 0.67 | 2.90 ± 1.49 |
| S1 | DualPID | **90.3%** [86.5%, 93.2%] | 9.94 ± 2.71 | 9.88 | 2.48 ± 1.81 | 1.36° ± 4.35° | 9.7% | 2.41 ± 0.83 | 3.05 ± 1.38 |
| S2 | Polar | **100.0%** [98.7%, 100.0%] | 9.22 ± 2.32 | 9.29 | 1.71 ± 0.40 | 1.86° ± 0.81° | 0.0% | 2.23 ± 0.67 | 3.70 ± 1.63 |
| S2 | DualPID | **90.0%** [86.1%, 92.9%] | 9.92 ± 2.71 | 9.86 | 2.47 ± 1.83 | 1.56° ± 4.28° | 10.0% | 2.41 ± 0.83 | 3.18 ± 1.39 |
| S3 | Polar | **100.0%** [98.7%, 100.0%] | 10.96 ± 3.74 | 10.57 | 1.60 ± 0.64 | 1.56° ± 0.86° | 0.0% | 2.24 ± 0.66 | 4.77 ± 3.66 |
| S3 | DualPID | **90.7%** [86.8%, 93.5%] | 9.86 ± 2.71 | 9.82 | 2.42 ± 1.60 | 1.25° ± 3.78° | 9.3% | 2.41 ± 0.82 | 3.13 ± 1.39 |
| S4 | Polar | **100.0%** [98.7%, 100.0%] | 7.36 ± 1.88 | 7.65 | 1.47 ± 0.59 | 1.91° ± 0.82° | 0.0% | 1.43 ± 0.66 | 4.62 ± 2.93 |
| S4 | DualPID | **18.0%** [14.1%, 22.7%] | 5.68 ± 2.54 | 4.40 | 7.62 ± 4.85 | 13.37° ± 12.06° | 82.0% | 1.36 ± 0.66 | 3.13 ± 1.22 |
| S5 | Polar | **99.3%** [97.6%, 99.8%] | 9.64 ± 4.22 | 9.14 | 1.52 ± 0.54 | 2.53° ± 7.31° | 0.0% | 2.25 ± 0.69 | 6.37 ± 10.55 |
| S5 | DualPID | **90.7%** [86.8%, 93.5%] | 9.74 ± 2.74 | 9.68 | 2.37 ± 1.56 | 1.92° ± 3.44° | 9.3% | 2.41 ± 0.82 | 3.81 ± 1.45 |

## 3. Kết quả kiểm định ý nghĩa thống kê ghép cặp (Paired Significance Tests)

| Kịch bản | Tỷ lệ Polar | Tỷ lệ DualPID | McNemar Stat | McNemar p-value | Có ý nghĩa p<0.05? | Wilcoxon Stat | Wilcoxon p-value | Có ý nghĩa p<0.05? |
|---|---|---|---|---|---|---|---|---|
| S1 | 100.0% | 90.3% | 27.03 | 2.00e-07 | **True** | 2979.5 | 2.29e-32 | **True** |
| S2 | 100.0% | 90.0% | 28.03 | 1.19e-07 | **True** | 5598.5 | 1.01e-21 | **True** |
| S3 | 100.0% | 90.7% | 26.04 | 3.35e-07 | **True** | 13537.0 | 1.52e-04 | **True** |
| S4 | 100.0% | 18.0% | 244.00 | 0.00e+00 | **True** | 124.0 | 1.64e-07 | **True** |
| S5 | 99.3% | 90.7% | 20.83 | 5.01e-06 | **True** | 8557.0 | 2.40e-13 | **True** |

## 4. Nhận xét tự động dựa trên số liệu thực nghiệm
1. **Hiệu năng kịch bản lý tưởng (S1)**: Bộ điều khiển Polar đạt tỷ lệ thành công tuyệt đối 100.0% với thời gian docking trung bình 9.17s, nhanh hơn DualPID (9.94s, tỷ lệ thành công 90.3%). Quỹ đạo Polar ngắn hơn (2.23m so với 2.41m của PID).
2. **Độ bền vững trước nhiễu đo lường (S2) và chấp hành kèm trễ (S3)**: Polar Controller duy trì tỷ lệ thành công 100% ở cả S2 và S3, trong khi DualPID đạt xấp xỉ 90.0% và 90.7%. Kiểm định McNemar cho p-value < 0.001 khẳng định sự vượt trội có ý nghĩa thống kê của Polar.
3. **Điểm yếu chí mạng của DualPID ở kịch bản tư thế khó (S4)**: DualPID bị sụt giảm tỷ lệ thành công nghiêm trọng xuống **18.0%**, trong khi Polar vẫn giữ vững **100.0%**. Nguyên nhân do hàm dẫn hướng $\theta_{ref} = -\arctan(k_y y)$ tạo ra trường vector đổi hướng quá gấp khi robot ở sát dock ($x \ge -0.5$m) hoặc lệch bên lớn ($|y| \ge 1.5$m); dưới giới hạn vận tốc góc $W_{MAX}$, robot vi sai bị bán kính quay giới hạn dẫn tới cắt ngang vượt quá giới hạn $x > 0.05$m (overshoot rate của PID lên tới 82.0%).
4. **Kịch bản nhiễu tổng hợp cao (S5)**: Khi chịu đồng thời nhiễu vị trí 2cm, nhiễu góc 3°, trễ 100ms và nhiễu chấp hành, Polar Controller đạt **99.3%** thành công, cao hơn rõ rệt so với **90.7%** của DualPID.
5. **Đặc tính tiêu hao năng lượng điều khiển**: DualPID tiêu thụ năng lượng điều khiển $\int (v^2+\omega^2)dt$ thấp hơn Polar trong hầu hết kịch bản (ví dụ ở S5 là 3.81 so với 6.37), do PID giảm tốc mượt hơn khi sai số góc lớn, trong khi Polar phản ứng góc mạnh mẽ hơn để ép robot bám chặt đường ngắm.
6. **Vai trò của các cơ chế bóc tách (Ablation Study)**: Đối với Polar Controller, cơ chế đóng băng góc gần dock (Freeze $\rho < 2$cm) đóng vai trò sống còn để triệt tiêu rung lắc do nhiễu $\arctan2(dy, dx)$ khi cự ly tiến về 0. Đối với DualPID, bộ lọc vi phân thông thấp D và anti-windup tích phân là điều kiện tiên quyết để tránh bão hòa và vọt lố.

## 5. Các giả thiết đã sử dụng
- Robot vi sai giả định chuyển động lăn thuần túy không trượt trên mặt phẳng 2D (no slip condition).
- Động cơ chấp hành phản hồi tức thời theo lệnh vận tốc (bỏ qua trễ động lực học bậc hai của mô-men động cơ, chỉ xét trễ truyền thông FIFO).
- Trạm sạc là điểm mốc tĩnh tại gốc $O=(0,0)$ hướng dọc theo trục $+x$.
- Nhiễu đo lường giả định là phân phối chuẩn Gaussian trắng cộng tính (Additive White Gaussian Noise) kèm độ lệch tĩnh góc hướng.

## 6. Giới hạn của mô phỏng
- Chưa mô hình hóa ma sát tiếp xúc phi tuyến với mặt sàn và hiện tượng trượt bánh khi quay tại chỗ ở vận tốc cao.
- Không gian docking không có vật cản động hoặc tĩnh xung quanh.
- Cảm biến đo trạng thái được mô phỏng ở tần số cố định 50 Hz (bằng tần số chu kỳ điều khiển dt=0.02s); trên thực tế camera fiducial marker (như AprilTag/Aruco) thường chỉ đạt 15-30 Hz và có jitter thời gian lấy mẫu.

## 7. Các tham số gợi ý người dùng nên thử thay đổi
1. `RHO_FREEZE`: Thử nghiệm thay đổi từ 0.01m đến 0.05m để khảo sát ngưỡng đóng băng tối ưu trên robot phần cứng thật.
2. `delay_steps`: Tăng độ trễ lên 150-200ms (7-10 bước) để khảo sát ngưỡng mất ổn định của vòng điều khiển khi truyền thông không dây bị nghẽn.
3. `k_y` trong DualPID: Thử giảm $k_y$ xuống $0.5 - 1.0$ khi ở gần dock để làm mượt trường vector dẫn hướng nhằm cải thiện tỷ lệ thành công của PID ở kịch bản S4.
4. `scale_saturation`: Bật `scale_saturation=True` trong `PolarController` và `DualPID` để so sánh chất lượng bám đường cong so với cắt độc lập.