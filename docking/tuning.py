"""
Mô-đun tinh chỉnh tham số công bằng (Fair Tuning) cho hai bộ điều khiển.
Sử dụng Random Search với đúng N=300 lần đánh giá mỗi bộ trên cùng tập tư thế và chuỗi nhiễu.
Hàm mục tiêu: J = -ty_le_thanh_cong + 0.01 * thoi_gian_tb + 0.5 * ty_le_overshoot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import json
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Tuple
import numpy as np

from config import (
    SEED_TUNING,
    DEFAULT_POLAR_GAINS,
    DEFAULT_PID_GAINS,
    X_INIT_MIN,
    X_INIT_MAX,
    Y_INIT_MIN,
    Y_INIT_MAX,
    THETA_INIT_MIN,
    THETA_INIT_MAX,
    MAX_TIME,
    Noise,
)
from controllers import PolarController, DualPIDController
from sim import run_episode
from stability import check_stability_conditions


def generate_poses(num_poses: int, seed: int) -> List[np.ndarray]:
    """Sinh danh sách tư thế xuất phát phân bố đều trong không gian làm việc."""
    rng = np.random.default_rng(seed)
    poses = []
    for _ in range(num_poses):
        x = rng.uniform(X_INIT_MIN, X_INIT_MAX)
        y = rng.uniform(Y_INIT_MIN, Y_INIT_MAX)
        theta = rng.uniform(THETA_INIT_MIN, THETA_INIT_MAX)
        poses.append(np.array([x, y, theta], dtype=np.float64))
    return poses


def evaluate_polar_candidate(args: Tuple[Dict[str, float], List[np.ndarray], Noise, int]) -> Tuple[float, Dict[str, Any]]:
    """Đánh giá 1 bộ gain Polar trên toàn bộ tập tư thế."""
    gains, poses, noise, base_seed = args
    ctrl = PolarController(
        k_rho=gains["k_rho"],
        k_alpha=gains["k_alpha"],
        k_beta=gains["k_beta"],
    )

    n_poses = len(poses)
    successes = 0
    overshoots = 0
    times = []

    for idx, p in enumerate(poses):
        ep_seed = base_seed + idx
        res = run_episode(ctrl, init_pose=p, noise=noise, seed=ep_seed)
        if res["ok"]:
            successes += 1
            times.append(res["t"])
        else:
            if res["reason"] == "overshoot":
                overshoots += 1
            times.append(MAX_TIME)

    success_rate = successes / n_poses
    overshoot_rate = overshoots / n_poses
    mean_time = float(np.mean(times))
    cost = -success_rate + 0.01 * mean_time + 0.5 * overshoot_rate

    return cost, {
        "gains": gains,
        "cost": cost,
        "success_rate": success_rate,
        "mean_time": mean_time,
        "overshoot_rate": overshoot_rate,
    }


def evaluate_pid_candidate(args: Tuple[Dict[str, float], List[np.ndarray], Noise, int]) -> Tuple[float, Dict[str, Any]]:
    """Đánh giá 1 bộ gain DualPID trên toàn bộ tập tư thế."""
    gains, poses, noise, base_seed = args
    ctrl = DualPIDController(
        kp_v=gains["kp_v"],
        ki_v=gains["ki_v"],
        kd_v=gains["kd_v"],
        kp_w=gains["kp_w"],
        ki_w=gains["ki_w"],
        kd_w=gains["kd_w"],
        k_y=gains["k_y"],
    )

    n_poses = len(poses)
    successes = 0
    overshoots = 0
    times = []

    for idx, p in enumerate(poses):
        ep_seed = base_seed + idx
        res = run_episode(ctrl, init_pose=p, noise=noise, seed=ep_seed)
        if res["ok"]:
            successes += 1
            times.append(res["t"])
        else:
            if res["reason"] == "overshoot":
                overshoots += 1
            times.append(MAX_TIME)

    success_rate = successes / n_poses
    overshoot_rate = overshoots / n_poses
    mean_time = float(np.mean(times))
    cost = -success_rate + 0.01 * mean_time + 0.5 * overshoot_rate

    return cost, {
        "gains": gains,
        "cost": cost,
        "success_rate": success_rate,
        "mean_time": mean_time,
        "overshoot_rate": overshoot_rate,
    }


def tune_polar(
    poses: List[np.ndarray],
    noise: Noise,
    n_evals: int = 300,
    search_seed: int = 101,
    num_workers: int = 4,
) -> Dict[str, Any]:
    """Tinh chỉnh bộ điều khiển tọa độ cực với đúng n_evals lần thử."""
    rng = np.random.default_rng(search_seed)
    candidates = []

    # Ứng viên 0: Gain khởi điểm
    candidates.append(dict(DEFAULT_POLAR_GAINS))

    # Sinh các ứng viên tiếp theo trong miền tìm kiếm ổn định
    while len(candidates) < n_evals:
        k_rho = float(rng.uniform(0.2, 1.2))
        k_alpha = float(rng.uniform(0.8, 3.2))
        k_beta = float(rng.uniform(-2.2, -0.2))

        # Ưu tiên ứng viên thỏa điều kiện ổn định cục bộ
        cond = check_stability_conditions(k_rho, k_alpha, k_beta)
        if cond["local_stability"]:
            candidates.append({
                "k_rho": round(k_rho, 4),
                "k_alpha": round(k_alpha, 4),
                "k_beta": round(k_beta, 4),
            })

    tasks = [(cand, poses, noise, 5000) for cand in candidates]

    if num_workers > 1:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(evaluate_polar_candidate, tasks))
    else:
        results = [evaluate_polar_candidate(t) for t in tasks]

    # Tìm ứng viên tốt nhất (cost nhỏ nhất)
    best_cost = float("inf")
    best_info = None
    for cost, info in results:
        if cost < best_cost:
            best_cost = cost
            best_info = info

    initial_info = results[0][1]

    return {
        "controller": "PolarController",
        "initial_gains": DEFAULT_POLAR_GAINS,
        "initial_result": initial_info,
        "best_gains": best_info["gains"],
        "best_result": best_info,
        "all_evaluations_count": len(results),
    }


def tune_pid(
    poses: List[np.ndarray],
    noise: Noise,
    n_evals: int = 300,
    search_seed: int = 202,
    num_workers: int = 4,
) -> Dict[str, Any]:
    """Tinh chỉnh bộ điều khiển DualPID với đúng n_evals lần thử."""
    rng = np.random.default_rng(search_seed)
    candidates = []

    # Ứng viên 0: Gain khởi điểm
    candidates.append(dict(DEFAULT_PID_GAINS))

    while len(candidates) < n_evals:
        kp_v = float(rng.uniform(0.4, 2.0))
        ki_v = float(rng.uniform(0.0, 0.04))
        kd_v = float(rng.uniform(0.01, 0.25))

        kp_w = float(rng.uniform(1.2, 4.8))
        ki_w = float(rng.uniform(0.0, 0.04))
        kd_w = float(rng.uniform(0.05, 0.4))

        k_y = float(rng.uniform(0.8, 3.5))

        candidates.append({
            "kp_v": round(kp_v, 4),
            "ki_v": round(ki_v, 4),
            "kd_v": round(kd_v, 4),
            "kp_w": round(kp_w, 4),
            "ki_w": round(ki_w, 4),
            "kd_w": round(kd_w, 4),
            "k_y": round(k_y, 4),
        })

    tasks = [(cand, poses, noise, 5000) for cand in candidates]

    if num_workers > 1:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            results = list(executor.map(evaluate_pid_candidate, tasks))
    else:
        results = [evaluate_pid_candidate(t) for t in tasks]

    best_cost = float("inf")
    best_info = None
    for cost, info in results:
        if cost < best_cost:
            best_cost = cost
            best_info = info

    initial_info = results[0][1]

    return {
        "controller": "DualPIDController",
        "initial_gains": DEFAULT_PID_GAINS,
        "initial_result": initial_info,
        "best_gains": best_info["gains"],
        "best_result": best_info,
        "all_evaluations_count": len(results),
    }


def run_tuning(output_path: str = "results/best_gains.json", num_workers: int = 8) -> Dict[str, Any]:
    """Thực thi toàn bộ quy trình tinh chỉnh công bằng và lưu kết quả ra file JSON."""
    print("=== BẮT ĐẦU TINH CHỈNH CÔNG BẰNG (FAIR TUNING) ===")
    print(f"Ngân sách: đúng N=300 đánh giá/bộ điều khiển.")
    print(f"Tập TUNING: 100 tư thế xuất phát (seed {SEED_TUNING}), kịch bản S2 (nhiễu đo 1cm, 1 độ).")

    # Sinh 100 tư thế tập tuning
    tuning_poses = generate_poses(num_poses=100, seed=SEED_TUNING)
    s2_noise = Noise(sig_pos=0.01, sig_yaw=np.radians(1.0), sig_v=0.0, sig_w=0.0, delay_steps=0)

    print("\n1. Đang tinh chỉnh PolarController (300 ứng viên)...")
    polar_res = tune_polar(tuning_poses, s2_noise, n_evals=300, search_seed=101, num_workers=num_workers)
    print(f"   Gain khởi điểm: {polar_res['initial_gains']} -> J = {polar_res['initial_result']['cost']:.4f}")
    print(f"   Gain tối ưu:    {polar_res['best_gains']} -> J = {polar_res['best_result']['cost']:.4f}")
    print(f"   Tỷ lệ thành công cải thiện: {polar_res['initial_result']['success_rate']*100:.1f}% -> {polar_res['best_result']['success_rate']*100:.1f}%")

    print("\n2. Đang tinh chỉnh DualPIDController (300 ứng viên)...")
    pid_res = tune_pid(tuning_poses, s2_noise, n_evals=300, search_seed=202, num_workers=num_workers)
    print(f"   Gain khởi điểm: {pid_res['initial_gains']} -> J = {pid_res['initial_result']['cost']:.4f}")
    print(f"   Gain tối ưu:    {pid_res['best_gains']} -> J = {pid_res['best_result']['cost']:.4f}")
    print(f"   Tỷ lệ thành công cải thiện: {pid_res['initial_result']['success_rate']*100:.1f}% -> {pid_res['best_result']['success_rate']*100:.1f}%")

    tuning_data = {
        "polar": polar_res,
        "pid": pid_res,
    }

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(tuning_data, f, indent=2, ensure_ascii=False)

    print(f"\nĐã lưu kết quả gain tối ưu vào: {out_file.resolve()}")
    return tuning_data


if __name__ == "__main__":
    run_tuning(output_path="results/best_gains.json", num_workers=8)
