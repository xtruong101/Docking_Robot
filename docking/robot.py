"""
Mô hình động học robot vi sai (unicycle) 2D, tích phân số, bão hòa và hàng đợi trễ.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from collections import deque
from typing import Tuple, Union
import numpy as np

from config import (
    DT,
    V_MAX,
    W_MAX,
    WHEEL_RADIUS,
    TRACK_WIDTH,
    Noise,
)


def wrap(angle: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """
    Chuẩn hóa góc về khoảng nửa mở (-pi, pi].
    Đảm bảo đầu ra luôn nằm trong (-pi, pi].
    """
    wrapped = (angle + np.pi) % (2.0 * np.pi) - np.pi
    if isinstance(wrapped, np.ndarray):
        wrapped = np.where(wrapped <= -np.pi, np.pi, wrapped)
    else:
        if wrapped <= -np.pi:
            wrapped = np.pi
    return wrapped


def saturate(
    v: float,
    w: float,
    v_max: float = V_MAX,
    w_max: float = W_MAX,
    scale: bool = False,
) -> Tuple[float, float]:
    """
    Bão hòa tín hiệu điều khiển (v, w).
    Nếu scale=False: cắt trực tiếp (clip) độc lập từng kênh.
    Nếu scale=True: tỷ lệ hóa đồng thời để bảo toàn bán kính quay tức thời R = v / w.
    """
    if scale:
        scale_factor = 1.0
        abs_v = abs(v)
        abs_w = abs(w)
        if abs_v > v_max and abs_v > 1e-12:
            scale_factor = min(scale_factor, v_max / abs_v)
        if abs_w > w_max and abs_w > 1e-12:
            scale_factor = min(scale_factor, w_max / abs_w)
        return float(v * scale_factor), float(w * scale_factor)

    v_sat = float(np.clip(v, -v_max, v_max))
    w_sat = float(np.clip(w, -w_max, w_max))
    return v_sat, w_sat


def unicycle_to_wheels(
    v: float,
    w: float,
    r: float = WHEEL_RADIUS,
    L: float = TRACK_WIDTH,
) -> Tuple[float, float]:
    """Quy đổi từ vận tốc unicycle (v, w) sang tốc độ góc bánh xe (w_right, w_left)."""
    w_r = (v + 0.5 * w * L) / r
    w_l = (v - 0.5 * w * L) / r
    return w_r, w_l


def wheels_to_unicycle(
    w_r: float,
    w_l: float,
    r: float = WHEEL_RADIUS,
    L: float = TRACK_WIDTH,
) -> Tuple[float, float]:
    """Quy đổi từ tốc độ góc bánh xe (w_right, w_left) sang vận tốc unicycle (v, w)."""
    v = r * (w_r + w_l) / 2.0
    w = r * (w_r - w_l) / L
    return v, w


class DelayQueue:
    """Hàng đợi FIFO lưu trữ tín hiệu điều khiển mô phỏng độ trễ truyền thông / chấp hành."""

    def __init__(self, delay_steps: int = 0):
        self.delay_steps = max(0, int(delay_steps))
        self.queue: deque[Tuple[float, float]] = deque()
        self.reset()

    def reset(self) -> None:
        """Khởi tạo lại hàng đợi với các giá trị 0."""
        self.queue.clear()
        for _ in range(self.delay_steps):
            self.queue.append((0.0, 0.0))

    def push_pop(self, v: float, w: float) -> Tuple[float, float]:
        """Đẩy lệnh mới vào và lấy lệnh cũ nhất ra sau khoảng trễ."""
        if self.delay_steps <= 0:
            return v, w
        self.queue.append((v, w))
        return self.queue.popleft()


def step(
    state: np.ndarray,
    v: float,
    w: float,
    dt: float = DT,
    method: str = "euler",
) -> np.ndarray:
    """
    Tích phân động học robot unicycle trong 1 bước thời gian dt:
    x' = v * cos(theta)
    y' = v * sin(theta)
    theta' = w
    Hỗ trợ phương pháp Euler và Runge-Kutta bậc 4 (RK4).
    """
    x, y, theta = state[0], state[1], state[2]

    if method == "euler":
        x_next = x + v * np.cos(theta) * dt
        y_next = y + v * np.sin(theta) * dt
        theta_next = wrap(theta + w * dt)
        return np.array([x_next, y_next, theta_next], dtype=np.float64)

    if method == "rk4":
        def f(s: np.ndarray) -> np.ndarray:
            return np.array([v * np.cos(s[2]), v * np.sin(s[2]), w], dtype=np.float64)

        k1 = f(state)
        k2 = f(state + 0.5 * dt * k1)
        k3 = f(state + 0.5 * dt * k2)
        k4 = f(state + dt * k3)

        s_next = state + (dt / 6.0) * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
        s_next[2] = wrap(s_next[2])
        return s_next

    raise ValueError(f"Phương pháp tích phân không hỗ trợ: {method}")


def measure_state(
    true_state: np.ndarray,
    noise: Noise,
    rng: np.random.Generator,
) -> np.ndarray:
    """Tạo trạng thái đo có nhiễu Gaussian và bias góc yaw."""
    x_noise = rng.normal(0.0, noise.sig_pos) if noise.sig_pos > 0.0 else 0.0
    y_noise = rng.normal(0.0, noise.sig_pos) if noise.sig_pos > 0.0 else 0.0
    yaw_noise = rng.normal(0.0, noise.sig_yaw) if noise.sig_yaw > 0.0 else 0.0

    x_meas = true_state[0] + x_noise
    y_meas = true_state[1] + y_noise
    theta_meas = wrap(true_state[2] + noise.bias_yaw + yaw_noise)

    return np.array([x_meas, y_meas, theta_meas], dtype=np.float64)


def apply_actuator_noise(
    v: float,
    w: float,
    noise: Noise,
    rng: np.random.Generator,
) -> Tuple[float, float]:
    """Cộng nhiễu ngẫu nhiên vào tín hiệu chấp hành trước khi truyền tới động cơ."""
    v_noise = rng.normal(0.0, noise.sig_v) if noise.sig_v > 0.0 else 0.0
    w_noise = rng.normal(0.0, noise.sig_w) if noise.sig_w > 0.0 else 0.0
    return float(v + v_noise), float(w + w_noise)
