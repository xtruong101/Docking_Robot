"""
Các bộ điều khiển bám dock cho robot vi sai:
1. PolarController (Hệ tọa độ cực Siegwart / Aicardi)
2. DualPID (PID hai vòng: vận tốc dài outer loop, vận tốc góc inner loop)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from typing import Tuple, Optional
import numpy as np

from config import (
    DT,
    V_MAX,
    W_MAX,
    RHO_FREEZE_DEFAULT,
    HYSTERESIS_BAND,
    DEFAULT_POLAR_GAINS,
    DEFAULT_PID_GAINS,
)
from robot import wrap, saturate


class PolarController:
    """
    Bộ điều khiển tọa độ cực (Siegwart / Aicardi).
    Trạng thái cực:
    rho = sqrt((-x)^2 + (-y)^2)
    alpha = wrap(atan2(-y, -x) - theta)
    beta = wrap(-theta - alpha)
    Luật điều khiển:
    v = k_rho * rho
    w = k_alpha * alpha + k_beta * beta
    """

    def __init__(
        self,
        k_rho: float = DEFAULT_POLAR_GAINS["k_rho"],
        k_alpha: float = DEFAULT_POLAR_GAINS["k_alpha"],
        k_beta: float = DEFAULT_POLAR_GAINS["k_beta"],
        rho_freeze: float = RHO_FREEZE_DEFAULT,
        enable_freeze: bool = True,
        enable_hysteresis: bool = True,
        scale_saturation: bool = False,
    ):
        self.k_rho = float(k_rho)
        self.k_alpha = float(k_alpha)
        self.k_beta = float(k_beta)
        self.rho_freeze = float(rho_freeze)
        self.enable_freeze = bool(enable_freeze)
        self.enable_hysteresis = bool(enable_hysteresis)
        self.scale_saturation = bool(scale_saturation)

        # Trạng thái nội tại
        self.in_backwards_mode: bool = False
        self.frozen_alpha: Optional[float] = None
        self.frozen_beta: Optional[float] = None
        self.reset()

    def reset(self) -> None:
        """Đặt lại trạng thái của bộ điều khiển cho tập chạy mới."""
        self.in_backwards_mode = False
        self.frozen_alpha = None
        self.frozen_beta = None

    def compute(self, measured_state: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Tính toán lệnh điều khiển (v, w) từ tư thế đo (x, y, theta).
        Trả về: (v, w, rho, alpha)
        """
        x, y, theta = measured_state[0], measured_state[1], measured_state[2]
        dx = -x
        dy = -y
        rho = float(np.hypot(dx, dy))

        raw_alpha = float(wrap(np.arctan2(dy, dx) - theta))
        raw_beta = float(wrap(-theta - raw_alpha))

        # Xử lý đóng băng gần dock (rho < rho_freeze) để chống chập chờn do nhiễu
        if self.enable_freeze and (rho < self.rho_freeze):
            if self.frozen_alpha is None:
                self.frozen_alpha = raw_alpha
                self.frozen_beta = raw_beta
            alpha = self.frozen_alpha
            beta = self.frozen_beta
        else:
            self.frozen_alpha = None
            self.frozen_beta = None
            alpha = raw_alpha
            beta = raw_beta

        # Xử lý quay lưng về phía dock (|alpha| > pi/2) với trễ hysteresis
        abs_alpha = abs(alpha)
        if self.enable_hysteresis:
            enter_threshold = np.pi / 2.0 + HYSTERESIS_BAND
            exit_threshold = np.pi / 2.0 - HYSTERESIS_BAND
            if not self.in_backwards_mode:
                if abs_alpha > enter_threshold:
                    self.in_backwards_mode = True
            else:
                if abs_alpha < exit_threshold:
                    self.in_backwards_mode = False
        else:
            self.in_backwards_mode = abs_alpha > (np.pi / 2.0)

        # Tính luật điều khiển
        if self.in_backwards_mode:
            # Quay tại chỗ hướng về phía trạm sạc
            v_cmd = 0.0
            w_cmd = self.k_alpha * alpha
        else:
            v_cmd = self.k_rho * rho
            w_cmd = self.k_alpha * alpha + self.k_beta * beta

        # Bão hòa vận tốc
        v_sat, w_sat = saturate(
            v_cmd,
            w_cmd,
            v_max=V_MAX,
            w_max=W_MAX,
            scale=self.scale_saturation,
        )

        return v_sat, w_sat, rho, alpha


class PID:
    """Bộ điều khiển PID 1 chiều với anti-windup, bộ lọc vi phân thông thấp và bão hòa."""

    def __init__(
        self,
        kp: float,
        ki: float,
        kd: float,
        dt: float = DT,
        out_min: float = -1e6,
        out_max: float = 1e6,
        i_max: float = 1.0,
        alpha_filter: float = 0.8,
        enable_anti_windup: bool = True,
        enable_filter_d: bool = True,
    ):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.dt = float(dt)
        self.out_min = float(out_min)
        self.out_max = float(out_max)
        self.i_max = float(i_max)
        self.alpha_filter = float(alpha_filter)
        self.enable_anti_windup = bool(enable_anti_windup)
        self.enable_filter_d = bool(enable_filter_d)

        self.integral: float = 0.0
        self.prev_error: float = 0.0
        self.prev_d_filtered: float = 0.0
        self.first_step: bool = True
        self.reset()

    def reset(self) -> None:
        """Đặt lại trạng thái tích phân và vi phân."""
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_d_filtered = 0.0
        self.first_step = True

    def compute(self, error: float) -> float:
        """Tính đầu ra PID cho sai số hiện tại."""
        # Thành phần tỷ lệ P
        p_term = self.kp * error

        # Thành phần tích phân I kèm anti-windup
        if self.enable_anti_windup:
            self.integral = float(np.clip(self.integral + error * self.dt, -self.i_max, self.i_max))
        else:
            self.integral += error * self.dt
        i_term = self.ki * self.integral

        # Thành phần vi phân D kèm bộ lọc thông thấp
        if self.first_step:
            d_raw = 0.0
            self.first_step = False
        else:
            d_raw = (error - self.prev_error) / self.dt if self.dt > 0.0 else 0.0

        if self.enable_filter_d:
            d_filtered = self.alpha_filter * self.prev_d_filtered + (1.0 - self.alpha_filter) * d_raw
        else:
            d_filtered = d_raw

        self.prev_d_filtered = d_filtered
        self.prev_error = error
        d_term = self.kd * d_filtered

        # Tổng hợp và bão hòa đầu ra
        u = p_term + i_term + d_term
        u_sat = float(np.clip(u, self.out_min, self.out_max))
        return u_sat


class DualPIDController:
    """
    Bộ điều khiển PID hai vòng:
    - Vòng ngoài: v = PID_v(rho) * max(0, cos(e_theta))
    - Vòng trong: theta_ref = -arctan(k_y * y), e_theta = wrap(theta_ref - theta), w = PID_w(e_theta)
    - Cơ chế quay lưng giống bộ cực (quay tại chỗ khi |e_theta| > pi/2) để so sánh công bằng.
    """

    def __init__(
        self,
        kp_v: float = DEFAULT_PID_GAINS["kp_v"],
        ki_v: float = DEFAULT_PID_GAINS["ki_v"],
        kd_v: float = DEFAULT_PID_GAINS["kd_v"],
        kp_w: float = DEFAULT_PID_GAINS["kp_w"],
        ki_w: float = DEFAULT_PID_GAINS["ki_w"],
        kd_w: float = DEFAULT_PID_GAINS["kd_w"],
        k_y: float = DEFAULT_PID_GAINS["k_y"],
        enable_filter_d: bool = True,
        enable_anti_windup: bool = True,
        scale_saturation: bool = False,
    ):
        self.k_y = float(k_y)
        self.scale_saturation = bool(scale_saturation)

        # PID vận tốc dài (chỉ chạy tiến >= 0)
        self.pid_v = PID(
            kp=kp_v,
            ki=ki_v,
            kd=kd_v,
            dt=DT,
            out_min=0.0,
            out_max=V_MAX,
            i_max=V_MAX,
            alpha_filter=0.8,
            enable_anti_windup=enable_anti_windup,
            enable_filter_d=enable_filter_d,
        )

        # PID vận tốc góc
        self.pid_w = PID(
            kp=kp_w,
            ki=ki_w,
            kd=kd_w,
            dt=DT,
            out_min=-W_MAX,
            out_max=W_MAX,
            i_max=W_MAX,
            alpha_filter=0.8,
            enable_anti_windup=enable_anti_windup,
            enable_filter_d=enable_filter_d,
        )

        self.in_backwards_mode: bool = False
        self.reset()

    def reset(self) -> None:
        """Đặt lại trạng thái bộ điều khiển cho lượt chạy mới."""
        self.pid_v.reset()
        self.pid_w.reset()
        self.in_backwards_mode = False

    def compute(self, measured_state: np.ndarray) -> Tuple[float, float, float, float]:
        """
        Tính lệnh điều khiển (v, w) từ tư thế đo (x, y, theta).
        Trả về: (v, w, rho, e_theta)
        """
        x, y, theta = measured_state[0], measured_state[1], measured_state[2]
        dx = -x
        dy = -y
        rho = float(np.hypot(dx, dy))

        # Tính góc định hướng tham chiếu theo trường vector bám trục x
        theta_ref = float(-np.arctan(self.k_y * y))
        e_theta = float(wrap(theta_ref - theta))

        # Chế độ quay tại chỗ khi góc lệch lớn (|e_theta| > pi/2) có hysteresis
        abs_e_theta = abs(e_theta)
        enter_threshold = np.pi / 2.0 + HYSTERESIS_BAND
        exit_threshold = np.pi / 2.0 - HYSTERESIS_BAND

        if not self.in_backwards_mode:
            if abs_e_theta > enter_threshold:
                self.in_backwards_mode = True
        else:
            if abs_e_theta < exit_threshold:
                self.in_backwards_mode = False

        if self.in_backwards_mode:
            v_cmd = 0.0
            w_cmd = self.pid_w.compute(e_theta)
        else:
            v_raw = self.pid_v.compute(rho)
            cos_factor = max(0.0, float(np.cos(e_theta)))
            v_cmd = v_raw * cos_factor
            w_cmd = self.pid_w.compute(e_theta)

        # Bão hòa vận tốc
        v_sat, w_sat = saturate(
            v_cmd,
            w_cmd,
            v_max=V_MAX,
            w_max=W_MAX,
            scale=self.scale_saturation,
        )

        return v_sat, w_sat, rho, e_theta
