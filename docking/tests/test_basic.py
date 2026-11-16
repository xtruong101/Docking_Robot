"""
Bộ kiểm thử tự động bắt buộc (pytest) cho hệ thống docking robot vi sai.
Kiểm tra tính đúng đắn của các hàm toán học, bộ điều khiển, tính tái lập và tiêu chí thành công.
"""

import sys
from pathlib import Path
import numpy as np
import pytest

# Thêm đường dẫn thư mục gốc docking vào sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    V_MAX,
    W_MAX,
    POS_TOLERANCE,
    YAW_TOLERANCE,
    Noise,
)
from robot import wrap, saturate, step
from controllers import PolarController, DualPIDController
from sim import run_episode
from stability import check_stability_conditions


def test_wrap_in_half_open_interval():
    """wrap() phải luôn trả về góc nằm trong nửa khoảng (-pi, pi]."""
    test_angles = [
        0.0,
        np.pi,
        -np.pi,
        3.0 * np.pi,
        -3.0 * np.pi,
        100.0,
        -100.0,
        np.pi / 2.0,
        -np.pi / 2.0,
        np.pi - 1e-12,
        -np.pi + 1e-12,
        2.0 * np.pi,
        -2.0 * np.pi,
    ]
    for angle in test_angles:
        w = wrap(angle)
        assert -np.pi < w <= np.pi, f"Thất bại với góc {angle}: wrap cho {w}"

    # Kiểm tra với mảng numpy
    arr = np.linspace(-10.0 * np.pi, 10.0 * np.pi, 1000)
    w_arr = wrap(arr)
    assert np.all(w_arr > -np.pi) and np.all(w_arr <= np.pi)


def test_no_noise_nominal_pose_success():
    """Không nhiễu, tư thế (-2, 0, 0): cả hai bộ điều khiển đều phải docking thành công."""
    nominal_pose = np.array([-2.0, 0.0, 0.0])

    # 1. Bộ điều khiển Polar
    polar_ctrl = PolarController()
    res_polar = run_episode(polar_ctrl, init_pose=nominal_pose, noise=None, seed=42)
    assert res_polar["ok"], f"Polar controller thất bại tại (-2,0,0): reason={res_polar['reason']}"
    assert res_polar["e_pos"] <= POS_TOLERANCE
    assert res_polar["e_yaw"] <= YAW_TOLERANCE

    # 2. Bộ điều khiển DualPID
    pid_ctrl = DualPIDController()
    res_pid = run_episode(pid_ctrl, init_pose=nominal_pose, noise=None, seed=42)
    assert res_pid["ok"], f"DualPID controller thất bại tại (-2,0,0): reason={res_pid['reason']}"
    assert res_pid["e_pos"] <= POS_TOLERANCE
    assert res_pid["e_yaw"] <= YAW_TOLERANCE


def test_saturation_limits_strictly_respected():
    """Bão hòa vận tốc luôn được tuân thủ: |v| <= V_MAX, |w| <= W_MAX tại mọi bước."""
    # Thử nghiệm với các lệnh cực lớn
    v_huge, w_huge = saturate(100.0, -50.0, scale=False)
    assert abs(v_huge) <= V_MAX + 1e-9
    assert abs(w_huge) <= W_MAX + 1e-9

    v_scaled, w_scaled = saturate(10.0, 10.0, scale=True)
    assert abs(v_scaled) <= V_MAX + 1e-9
    assert abs(w_scaled) <= W_MAX + 1e-9

    # Kiểm tra trong toàn bộ episode mô phỏng có tư thế khởi đầu lệch lớn
    pose_large_yaw = np.array([-2.0, 1.5, np.pi * 0.9])
    polar_ctrl = PolarController()
    res = run_episode(polar_ctrl, init_pose=pose_large_yaw, noise=None)
    assert np.all(np.abs(res["v"]) <= V_MAX + 1e-9)
    assert np.all(np.abs(res["w"]) <= W_MAX + 1e-9)


def test_reproducibility_bit_for_bit():
    """Tái lập: cùng seed cho cùng kết quả từng bit đối với cả hai bộ điều khiển khi có nhiễu."""
    init_pose = np.array([-1.5, 1.0, 0.5])
    noise = Noise(sig_pos=0.01, sig_yaw=0.02, sig_v=0.01, sig_w=0.05, delay_steps=3)
    seed = 12345

    # Lượt 1
    ctrl1 = PolarController()
    res1 = run_episode(ctrl1, init_pose=init_pose, noise=noise, seed=seed)

    # Lượt 2
    ctrl2 = PolarController()
    res2 = run_episode(ctrl2, init_pose=init_pose, noise=noise, seed=seed)

    assert res1["ok"] == res2["ok"]
    assert res1["reason"] == res2["reason"]
    assert res1["t"] == res2["t"]
    assert np.array_equal(res1["traj"], res2["traj"]), "Quỹ đạo trạng thái thật không trùng khớp từng bit!"
    assert np.array_equal(res1["v"], res2["v"]), "Mảng vận tốc dài không trùng khớp từng bit!"
    assert np.array_equal(res1["w"], res2["w"]), "Mảng vận tốc góc không trùng khớp từng bit!"


def test_stability_conditions():
    """Điều kiện ổn định trả về True với gain (0.5, 1.5, -0.5) và False với k_beta > 0."""
    # Cặp gain danh định chuẩn
    cond_nominal = check_stability_conditions(k_rho=0.5, k_alpha=1.5, k_beta=-0.5)
    assert cond_nominal["local_stability"] is True
    assert cond_nominal["no_reversal"] is True
    assert cond_nominal["spectral_stability"] is True
    assert cond_nominal["is_stable"] is True

    # Trường hợp k_beta > 0 (vi phạm điều kiện ổn định)
    cond_unstable = check_stability_conditions(k_rho=0.5, k_alpha=1.5, k_beta=0.5)
    assert cond_unstable["c2_k_beta_neg"] is False
    assert cond_unstable["local_stability"] is False
    assert cond_unstable["is_stable"] is False

    # Trường hợp k_alpha <= k_rho (vi phạm Hurwitz)
    cond_unstable_alpha = check_stability_conditions(k_rho=0.5, k_alpha=0.3, k_beta=-0.5)
    assert cond_unstable_alpha["local_stability"] is False


def test_success_criteria_evaluated_on_true_state():
    """
    Tiêu chí thành công phải dùng TRẠNG THÁI THẬT, không dùng trạng thái đo.
    Kiểm tra bằng cách đặt nhiễu đo cực lớn (ví dụ sig_pos=5.0m, sig_yaw=pi)
    nhưng robot thực tế đặt ngay tại vị trí thành công (0,0,0).
    """
    near_dock_pose = np.array([-0.01, 0.005, 0.01])  # Trong khoảng dung sai 2cm và 3 độ
    extreme_noise = Noise(sig_pos=5.0, sig_yaw=np.pi, delay_steps=0)

    ctrl = PolarController()
    res = run_episode(ctrl, init_pose=near_dock_pose, noise=extreme_noise, max_steps=5, seed=999)

    # Robot phải đạt thành công ngay tại bước đầu tiên bất kể nhiễu đo lớn cỡ nào
    assert res["ok"] is True, "Hệ thống phải nhận diện thành công dựa trên trạng thái thật!"
    assert res["reason"] == "success"
    assert res["e_pos"] <= POS_TOLERANCE
    assert res["e_yaw"] <= YAW_TOLERANCE
