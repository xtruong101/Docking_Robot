"""
Mô phỏng một tập chạy (episode) docking của robot vi sai.
Đánh giá tiêu chí thành công trên trạng thái THẬT, hỗ trợ nhiễu và độ trễ.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from typing import Dict, Any, Optional
import numpy as np

from config import (
    DT,
    MAX_STEPS,
    POS_TOLERANCE,
    YAW_TOLERANCE,
    OVERSHOOT_X_LIMIT,
    Noise,
)
from robot import (
    step,
    wrap,
    DelayQueue,
    measure_state,
    apply_actuator_noise,
)


def run_episode(
    controller: Any,
    init_pose: np.ndarray,
    noise: Optional[Noise] = None,
    max_steps: int = MAX_STEPS,
    dt: float = DT,
    method: str = "euler",
    seed: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Chạy một tập mô phỏng docking từ tư thế ban đầu init_pose = [x, y, theta].
    
    Tham số:
        controller: Bộ điều khiển (PolarController hoặc DualPIDController)
        init_pose: Tư thế ban đầu thật [x, y, theta]
        noise: Đối tượng cấu hình nhiễu (mặc định không nhiễu)
        max_steps: Số bước tối đa (3000 bước tương ứng 60s)
        dt: Chu kỳ lấy mẫu (0.02s)
        method: Phương pháp tích phân ("euler" hoặc "rk4")
        seed: Hạt giống ngẫu nhiên để tái lập bit-for-bit
        
    Trả về:
        dict chứa:
            ok: bool (docking thành công hay không)
            reason: str ('success', 'timeout', 'overshoot', 'wrong_heading')
            t: float (thời gian docking tính bằng giây)
            e_pos: float (sai số vị trí cuối cùng, mét)
            e_yaw: float (sai số góc hướng cuối cùng, rad)
            traj: np.ndarray shape (N, 3) (quỹ đạo trạng thái THẬT)
            traj_meas: np.ndarray shape (N, 3) (quỹ đạo đo lường)
            v: np.ndarray shape (N,) (vận tốc dài lệnh)
            w: np.ndarray shape (N,) (vận tốc góc lệnh)
            time_array: np.ndarray shape (N,) (mảng thời gian)
            rho: np.ndarray shape (N,) (khoảng cách tới dock)
            heading_err: np.ndarray shape (N,) (sai số góc alpha hoặc e_theta)
            energy: float (năng lượng điều khiển tích phân v^2 + w^2)
            path_length: float (chiều dài quãng đường thực tế)
    """
    if noise is None:
        noise = Noise()

    # Khởi tạo bộ sinh số ngẫu nhiên độc lập cho từng episode
    rng = np.random.default_rng(seed)

    # Đặt lại trạng thái bộ điều khiển và hàng đợi trễ
    controller.reset()
    delay_queue = DelayQueue(delay_steps=noise.delay_steps)

    # Khởi tạo trạng thái thật
    true_state = np.array(init_pose, dtype=np.float64)
    true_state[2] = wrap(true_state[2])

    # Danh sách lưu vết dữ liệu
    traj_list = []
    traj_meas_list = []
    v_list = []
    w_list = []
    rho_list = []
    heading_err_list = []

    success = False
    reason = "timeout"
    step_count = 0

    for k in range(max_steps):
        step_count = k
        x, y, theta = true_state[0], true_state[1], true_state[2]
        dist = float(np.hypot(x, y))
        yaw_err = float(abs(wrap(theta)))

        # Lưu trạng thái thật hiện tại
        traj_list.append(true_state.copy())

        # 1. Kiểm tra điều kiện thất bại do vượt dock (overshoot) trên trạng thái THẬT
        if x > OVERSHOOT_X_LIMIT:
            success = False
            reason = "overshoot"
            v_list.append(0.0)
            w_list.append(0.0)
            rho_list.append(dist)
            heading_err_list.append(yaw_err)
            traj_meas_list.append(true_state.copy())
            break

        # 2. Kiểm tra điều kiện thành công trên trạng thái THẬT
        if dist <= POS_TOLERANCE and yaw_err <= YAW_TOLERANCE:
            success = True
            reason = "success"
            v_list.append(0.0)
            w_list.append(0.0)
            rho_list.append(dist)
            heading_err_list.append(yaw_err)
            traj_meas_list.append(true_state.copy())
            break

        # 3. Đo lường trạng thái có nhiễu (bộ điều khiển chỉ quan sát trạng thái này)
        measured_state = measure_state(true_state, noise, rng)
        traj_meas_list.append(measured_state.copy())

        # 4. Tính toán lệnh điều khiển
        v_cmd, w_cmd, rho_val, h_err = controller.compute(measured_state)
        v_list.append(v_cmd)
        w_list.append(w_cmd)
        rho_list.append(rho_val)
        heading_err_list.append(h_err)

        # 5. Đưa qua trễ truyền thông
        v_delayed, w_delayed = delay_queue.push_pop(v_cmd, w_cmd)

        # 6. Cộng nhiễu cơ cấu chấp hành
        v_act, w_act = apply_actuator_noise(v_delayed, w_delayed, noise, rng)

        # 7. Tích phân động học sang bước tiếp theo
        true_state = step(true_state, v_act, w_act, dt=dt, method=method)

    else:
        # Hết max_steps mà chưa dừng
        step_count = max_steps
        traj_list.append(true_state.copy())
        traj_meas_list.append(true_state.copy())
        v_list.append(0.0)
        w_list.append(0.0)
        dist = float(np.hypot(true_state[0], true_state[1]))
        yaw_err = float(abs(wrap(true_state[2])))
        rho_list.append(dist)
        heading_err_list.append(yaw_err)

        if true_state[0] > OVERSHOOT_X_LIMIT:
            reason = "overshoot"
        elif dist <= POS_TOLERANCE and yaw_err > YAW_TOLERANCE:
            reason = "wrong_heading"
        else:
            reason = "timeout"
        success = False

    # Chuyển đổi sang mảng numpy
    traj_arr = np.array(traj_list, dtype=np.float64)
    traj_meas_arr = np.array(traj_meas_list, dtype=np.float64)
    v_arr = np.array(v_list, dtype=np.float64)
    w_arr = np.array(w_list, dtype=np.float64)
    rho_arr = np.array(rho_list, dtype=np.float64)
    heading_err_arr = np.array(heading_err_list, dtype=np.float64)

    final_time = float(step_count * dt)
    final_e_pos = float(np.hypot(traj_arr[-1, 0], traj_arr[-1, 1]))
    final_e_yaw = float(abs(wrap(traj_arr[-1, 2])))

    # Tính quãng đường và năng lượng điều khiển
    if len(traj_arr) > 1:
        diffs = np.diff(traj_arr[:, :2], axis=0)
        path_length = float(np.sum(np.hypot(diffs[:, 0], diffs[:, 1])))
    else:
        path_length = 0.0

    control_energy = float(np.sum(v_arr**2 + w_arr**2) * dt)

    time_arr = np.arange(len(traj_arr)) * dt

    return {
        "ok": success,
        "reason": reason,
        "t": final_time,
        "e_pos": final_e_pos,
        "e_yaw": final_e_yaw,
        "traj": traj_arr,
        "traj_meas": traj_meas_arr,
        "v": v_arr,
        "w": w_arr,
        "time_array": time_arr,
        "rho": rho_arr,
        "heading_err": heading_err_arr,
        "energy": control_energy,
        "path_length": path_length,
    }
