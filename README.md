# Dự án Mô phỏng Autonomous Docking cho Robot Di động Vi sai (Unicycle)

Dự án nghiên cứu và mô phỏng thuật toán cập trạm sạc tự động (**Autonomous Docking**) cho robot di động vi sai 2D không sử dụng ROS, dựa trên thư viện chuẩn **NumPy**, **Matplotlib**, **SciPy**, **pandas** và kiểm thử tự động với **pytest**.

Dự án so sánh chuyên sâu giữa hai chiến lược điều khiển:
1. **Bộ điều khiển Tọa độ cực (Polar Coordinates Controller - Siegwart / Aicardi)**: Tích hợp cơ chế quay lưng tự định hướng có hysteresis và đóng băng góc gần trạm sạc.
2. **Bộ điều khiển PID Hai vòng (Dual-loop PID Controller)**: Vòng ngoài điều khiển vận tốc dài $v$, vòng trong điều khiển vận tốc góc $\omega$ theo trường vector định hướng $\theta_{\text{ref}} = -\arctan(k_y y)$ kèm anti-windup và lọc vi phân thông thấp.

---

## 1. Cấu trúc Dự án

```text
ROBOT_FINAL/
│
├── main.py                    # Wrapper khởi chạy nhanh từ thư mục gốc
├── requirements.txt           # Danh mục thư viện phụ thuộc
├── REQUIRE.txt                # Đặc tả yêu cầu kỹ thuật đề bài
│
├── docking/                   # Thư mục mã nguồn chính
│   ├── config.py              # Thông số hình học, giới hạn, tiêu chuẩn docking, dataclass Noise
│   ├── robot.py               # Động học vi sai, tích phân Euler/RK4, wrap, bão hòa, hàng đợi trễ
│   ├── controllers.py         # PolarController, DualPIDController, lớp PID
│   ├── sim.py                 # Hàm run_episode() mô phỏng tập chạy và đánh giá trạng thái thật
│   ├── stability.py           # Tuyến tính hóa ma trận A, trị riêng, kiểm tra ổn định & tính đơn điệu
│   ├── tuning.py              # Tinh chỉnh công bằng (Fair Tuning, N=300 đánh giá/bộ)
│   ├── experiments.py         # Chạy kịch bản S1–S5 (n=300), quét hệ số nhiễu k, ablation study
│   ├── plots.py               # Sinh toàn bộ 10 hình vẽ kỹ thuật (PNG 300 dpi và PDF vector)
│   ├── stats.py               # Thống kê, khoảng tin cậy Wilson 95%, kiểm định McNemar & Wilcoxon
│   ├── main.py                # Điểm vào thực thi với các cờ dòng lệnh
│   │
│   ├── tests/
│   │   └── test_basic.py      # Bộ kiểm thử pytest bắt buộc
│   │
│   ├── results/               # Chứa các file kết quả thống kê CSV, JSON và Markdown
│   │   ├── best_gains.json    # Gain trước và sau tinh chỉnh
│   │   ├── scenario_metrics.csv # Toàn bộ chỉ số hiệu năng S1–S5
│   │   ├── mcnemar_wilcoxon.csv # Kết quả kiểm định ý nghĩa thống kê
│   │   ├── sweep_k.csv        # Dữ liệu quét độ nhạy nhiễu
│   │   ├── ablation.csv       # Dữ liệu thực nghiệm bóc tách thành phần
│   │   └── summary.md         # Báo cáo tổng hợp kết quả chi tiết
│   │
│   └── figures/               # Toàn bộ 10 bộ đồ thị kỹ thuật (PNG 300 dpi và PDF vector)
│       ├── fig1_dock_robot_coordinate_system.*
│       ├── fig2_s1_trajectories.*
│       ├── fig3_s1_time_response.*
│       ├── fig4_multi_pose_trajectories.*
│       ├── fig5_boxplots_s2_s5.*
│       ├── fig6_success_rates_wilson.*
│       ├── fig7_sweep_noise.*
│       ├── fig8_stability_analysis.*
│       ├── fig9_heatmap_success_map.*
│       └── fig10_ablation_study.*
```

---

## 2. Cài đặt Môi trường

Dự án yêu cầu **Python 3.10+**. Cài đặt các thư viện phụ thuộc bằng lệnh:

```bash
pip install -r requirements.txt
```

---

## 3. Hướng dẫn Chạy chương trình

### Cách 1: Chạy toàn bộ quy trình từ A đến Z (`--all`)
Lệnh này thực hiện tuần tự: Kiểm chứng ổn định $\to$ Tinh chỉnh công bằng (N=300) $\to$ Chạy thực nghiệm S1–S5 (n=300 mỗi kịch bản) $\to$ Quét độ nhạy $k$ $\to$ Ablation Study $\to$ Vẽ và xuất 10 hình kỹ thuật $\to$ Xuất báo cáo `results/summary.md` và in bảng tổng hợp Markdown ra màn hình:

```bash
python main.py --all
```
*(Chương trình tận dụng xử lý đa tiến trình `multiprocessing` trên toàn bộ lõi CPU, hoàn thành toàn bộ trong khoảng 2–3 phút)*.

### Cách 2: Chạy riêng từng mô-đun chức năng
- **Kiểm chứng ổn định giải tích và kiểm tra số:**
  ```bash
  python main.py --stability
  ```
- **Thực hiện tinh chỉnh tham số công bằng (Fair Tuning, N=300):**
  ```bash
  python main.py --tune
  ```
- **Chạy các kịch bản thực nghiệm S1–S5 và lưu kết quả CSV:**
  ```bash
  python main.py --scenarios
  ```
- **Vẽ và xuất 10 hình đồ thị kỹ thuật ra thư mục `figures/`:**
  ```bash
  python main.py --plots
  ```

---

## 4. Chạy Bộ Kiểm thử Tự động (pytest)

Để kiểm chứng toàn bộ 6 tiêu chí kiểm thử bắt buộc (hàm `wrap`, bão hòa vận tốc, tái lập kết quả từng bit, tính đúng đắn khi không nhiễu, điều kiện ổn định, đánh giá tiêu chí trên trạng thái thật):

```bash
pytest docking/tests/test_basic.py -v
```

---

## 5. Tóm tắt Tiêu chí Docking và Kịch bản Thử nghiệm

- **Tiêu chuẩn thành công**:
  - Sai số vị trí cuối cùng: $e_{\text{pos}} = \sqrt{x^2+y^2} \le 2\text{ cm}$.
  - Sai số góc hướng cuối cùng: $|\theta| \le 3^\circ$.
  - Thời gian docking: $t \le 60\text{ s}$.
  - Không vượt dock: $x > 0.05\text{ m}$ bị coi là thất bại tức thì do vọt lố (overshoot).
  - Đánh giá nghiêm ngặt trên **trạng thái thật**, không phụ thuộc trạng thái đo.

- **Kịch bản thực nghiệm**:
  - **S1**: Lý tưởng, không nhiễu từ 3 tư thế đại diện và tập kiểm thử.
  - **S2**: Nhiễu đo Gaussian $\sigma_{\text{pos}} = 1\text{ cm}$, $\sigma_\theta = 1^\circ$.
  - **S3**: Nhiễu chấp hành $\sigma_v = 0.01\text{ m/s}$, $\sigma_\omega = 0.05\text{ rad/s}$ kết hợp trễ truyền thông FIFO 75–80 ms.
  - **S4**: Tư thế thử thách khắc nghiệt: rất lệch bên ($|y| \ge 1.5\text{ m}, x \ge -1.0\text{ m}$) hoặc áp sát dock ($x \in [-0.5, -0.3]\text{ m}$) với góc lệch lớn ($|\theta| \ge 2.0\text{ rad}$).
  - **S5**: Nhiễu tổng hợp mức cao: $\sigma_{\text{pos}} = 2\text{ cm}$, $\sigma_\theta = 3^\circ$, $\sigma_v = 0.02\text{ m/s}$, $\sigma_\omega = 0.1\text{ rad/s}$, trễ 100 ms.
  - **Quét $k$**: Nhân hệ số $k \in \{0, 0.5, 1, 1.5, 2, 3, 4\}$ lên bộ nhiễu S5.
  - **Ablation Study**: Đánh giá vai trò của Freeze, Hysteresis, Lọc vi phân D và Anti-windup.

---

## 6. Tái lập Kết quả (Reproducibility)
Tất cả các lượt chạy thực nghiệm và tinh chỉnh đều được cố định hạt giống ngẫu nhiên độc lập theo từng lượt:
- Tập tinh chỉnh (Tuning): `seed = 1` (100 tư thế).
- Tập kiểm thử (Test): `seed = 2024` (300 tư thế độc lập).
- Chuỗi nhiễu mỗi lượt chạy: `base_seed + episode_index`, đảm bảo cả hai bộ điều khiển đối đầu trên **chính xác từng bit dữ liệu tư thế và nhiễu**.
