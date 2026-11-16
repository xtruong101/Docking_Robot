"""
Cấu hình hệ thống mô phỏng Autonomous Docking cho robot vi sai.
Chứa các hằng số vật lý, thông số động học, tiêu chí docking và dataclass mô hình nhiễu.
"""

from dataclasses import dataclass
import numpy as np


# --- Tham số thời gian ---
DT: float = 0.02           # Chu kỳ lấy mẫu (giây)
MAX_TIME: float = 60.0      # Thời gian tối đa cho một lượt docking (giây)
MAX_STEPS: int = int(MAX_TIME / DT)  # Số bước tối đa: 3000 bước

# --- Giới hạn động học & thông số robot ---
V_MAX: float = 0.3          # Giới hạn tốc độ dài cực đại (m/s)
W_MAX: float = 1.5          # Giới hạn tốc độ góc cực đại (rad/s)
WHEEL_RADIUS: float = 0.035 # Bán kính bánh xe r (m)
TRACK_WIDTH: float = 0.23   # Khoảng cách giữa 2 bánh L (m)

# --- Tiêu chí thành công docking (đánh giá trên TRẠNG THÁI THẬT) ---
POS_TOLERANCE: float = 0.02      # Sai số vị trí cho phép: <= 2 cm (m)
YAW_TOLERANCE: float = np.radians(3.0)  # Sai số góc hướng cho phép: <= 3 độ (rad)
OVERSHOOT_X_LIMIT: float = 0.05  # Giới hạn vượt dock: x > 0.05 m tính là overshoot thất bại

# --- Phạm vi tư thế ban đầu ---
X_INIT_MIN: float = -3.0
X_INIT_MAX: float = -0.5
Y_INIT_MIN: float = -2.0
Y_INIT_MAX: float = 2.0
THETA_INIT_MIN: float = -np.pi
THETA_INIT_MAX: float = np.pi

# --- Tham số bộ điều khiển ---
RHO_FREEZE_DEFAULT: float = 0.02 # Ngưỡng đóng băng tọa độ cực gần dock (m)
HYSTERESIS_BAND: float = 0.1     # Biên trễ chuyển chế độ quay tại chỗ (rad)

# --- Bộ gain khởi điểm ---
DEFAULT_POLAR_GAINS = {
    "k_rho": 0.5,
    "k_alpha": 1.5,
    "k_beta": -0.5,
}

DEFAULT_PID_GAINS = {
    "kp_v": 1.0,
    "ki_v": 0.0,
    "kd_v": 0.1,
    "kp_w": 3.0,
    "ki_w": 0.0,
    "kd_w": 0.2,
    "k_y": 2.0,
}

# --- Hạt giống ngẫu nhiên (Seeds) ---
SEED_TUNING: int = 1
SEED_TEST: int = 2024


@dataclass
class Noise:
    """Mô hình nhiễu đo lường và nhiễu chấp hành."""
    sig_pos: float = 0.0      # Sai số đo vị trí chuẩn sigma (m)
    sig_yaw: float = 0.0      # Sai số đo góc hướng chuẩn sigma (rad)
    sig_v: float = 0.0        # Nhiễu vận tốc dài cơ cấu chấp hành (m/s)
    sig_w: float = 0.0        # Nhiễu vận tốc góc cơ cấu chấp hành (rad/s)
    delay_steps: int = 0      # Độ trễ điều khiển tính bằng số bước FIFO (dt = 0.02s)
    bias_yaw: float = 0.0     # Độ lệch tĩnh góc hướng (rad)


# --- 3 tư thế đại diện cho kịch bản S1 ---
S1_REPRESENTATIVE_POSES = [
    np.array([-2.0, 0.0, 0.0]),      # Tư thế 1: Phía trước dock
    np.array([-1.5, 1.5, 0.0]),      # Tư thế 2: Lệch bên
    np.array([-1.5, 0.5, np.pi]),    # Tư thế 3: Quay lưng về dock
]
