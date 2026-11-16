"""
Chạy toàn bộ các kịch bản thực nghiệm S1 - S5, quét hệ số nhiễu k, và nghiên cứu bóc tách (ablation study).
Lưu toàn bộ dữ liệu thống kê ra results/*.csv.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import json
from concurrent.futures import ProcessPoolExecutor
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

from config import (
    SEED_TEST,
    DEFAULT_POLAR_GAINS,
    DEFAULT_PID_GAINS,
    S1_REPRESENTATIVE_POSES,
    Noise,
)
from controllers import PolarController, DualPIDController
from sim import run_episode
from stats import compute_metrics, mcnemar_test_paired, wilcoxon_test_paired
from tuning import generate_poses


def load_best_gains() -> Tuple[Dict[str, float], Dict[str, float]]:
    """Đọc gain đã tinh chỉnh từ file JSON (nếu có), hoặc trả về gain mặc định."""
    possible_paths = [
        Path("results/best_gains.json"),
        Path("docking/results/best_gains.json"),
        Path(__file__).parent / "results" / "best_gains.json",
    ]
    for p in possible_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    polar_g = data["polar"]["best_gains"]
                    pid_g = data["pid"]["best_gains"]
                    return polar_g, pid_g
            except Exception:
                pass
    return DEFAULT_POLAR_GAINS, DEFAULT_PID_GAINS


def generate_s4_poses(num_poses: int, seed: int = SEED_TEST + 4) -> List[np.ndarray]:
    """
    Sinh các tư thế khó cho kịch bản S4:
    - Loại 1: Rất lệch bên (|y| >= 1.5 và x >= -1.0)
    - Loại 2: Gần dock (x in [-0.5, -0.3]) với hướng lệch lớn (|theta| >= 2.0 rad)
    """
    rng = np.random.default_rng(seed)
    poses = []
    half = num_poses // 2
    # Loại 1
    for _ in range(half):
        x = rng.uniform(-1.0, -0.5)
        sign_y = rng.choice([-1.0, 1.0])
        y = sign_y * rng.uniform(1.5, 2.0)
        theta = rng.uniform(-np.pi, np.pi)
        poses.append(np.array([x, y, theta], dtype=np.float64))

    # Loại 2
    for _ in range(num_poses - half):
        x = rng.uniform(-0.5, -0.3)
        y = rng.uniform(-1.0, 1.0)
        sign_th = rng.choice([-1.0, 1.0])
        theta = sign_th * rng.uniform(2.0, np.pi)
        poses.append(np.array([x, y, theta], dtype=np.float64))

    return poses


def _eval_single_episode(args: Tuple[str, Dict[str, Any], np.ndarray, Noise, int]) -> Dict[str, Any]:
    """Helper đơn luồng để chạy 1 episode song song."""
    ctrl_type, gains, pose, noise, ep_seed = args
    if ctrl_type == "polar":
        ctrl = PolarController(**gains)
    else:
        ctrl = DualPIDController(**gains)

    res = run_episode(ctrl, init_pose=pose, noise=noise, seed=ep_seed)
    # Loại bỏ các mảng lớn để tiết kiệm bộ nhớ khi truyền dữ liệu IPC
    return {
        "ok": res["ok"],
        "reason": res["reason"],
        "t": res["t"],
        "e_pos": res["e_pos"],
        "e_yaw": res["e_yaw"],
        "energy": res["energy"],
        "path_length": res["path_length"],
    }


def run_paired_experiment(
    polar_gains: Dict[str, Any],
    pid_gains: Dict[str, Any],
    poses: List[np.ndarray],
    noise: Noise,
    base_seed: int = 10000,
    num_workers: int = 8,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Chạy đánh giá ghép cặp cho cả hai bộ điều khiển trên cùng tư thế và cùng seed chuỗi nhiễu."""
    polar_tasks = [("polar", polar_gains, p, noise, base_seed + i) for i, p in enumerate(poses)]
    pid_tasks = [("pid", pid_gains, p, noise, base_seed + i) for i, p in enumerate(poses)]

    if num_workers > 1:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            polar_results = list(executor.map(_eval_single_episode, polar_tasks))
            pid_results = list(executor.map(_eval_single_episode, pid_tasks))
    else:
        polar_results = [_eval_single_episode(t) for t in polar_tasks]
        pid_results = [_eval_single_episode(t) for t in pid_tasks]

    return polar_results, pid_results


def run_all_scenarios(
    num_runs: int = 300,
    num_workers: int = 8,
    output_dir: str = "results",
) -> Dict[str, Any]:
    """Thực thi toàn bộ các kịch bản S1 - S5, quét k, và ablation study."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    polar_gains, pid_gains = load_best_gains()
    print("Sử dụng bộ gain:")
    print("  Polar:", polar_gains)
    print("  PID:  ", pid_gains)

    # Tập 300 tư thế kiểm thử độc lập (seed 2024)
    test_poses = generate_poses(num_poses=num_runs, seed=SEED_TEST)
    s4_poses = generate_s4_poses(num_poses=num_runs, seed=SEED_TEST + 4)

    # Định nghĩa cấu hình các kịch bản
    scenarios = {
        "S1": {
            "name": "S1 (Lý tưởng, không nhiễu)",
            "poses": test_poses,
            "noise": Noise(),
        },
        "S2": {
            "name": "S2 (Nhiễu đo 1cm, 1°)",
            "poses": test_poses,
            "noise": Noise(sig_pos=0.01, sig_yaw=np.radians(1.0)),
        },
        "S3": {
            "name": "S3 (Nhiễu chấp hành 0.01m/s, 0.05rad/s + trễ 75ms)",
            "poses": test_poses,
            "noise": Noise(sig_v=0.01, sig_w=0.05, delay_steps=4),  # 4 * 0.02s = 80ms ~ 75ms
        },
        "S4": {
            "name": "S4 (Tư thế khó: lệch lớn / sát dock)",
            "poses": s4_poses,
            "noise": Noise(sig_pos=0.005, sig_yaw=np.radians(0.5)),
        },
        "S5": {
            "name": "S5 (Nhiễu tổng hợp cao: 2cm, 3°, 0.02m/s, 0.1rad/s, trễ 100ms)",
            "poses": test_poses,
            "noise": Noise(sig_pos=0.02, sig_yaw=np.radians(3.0), sig_v=0.02, sig_w=0.1, delay_steps=5),
        },
    }

    metrics_rows = []
    tests_rows = []
    all_raw_data = {}

    print("\n--- ĐANG CHẠY CÁC KỊCH BẢN S1 - S5 (n=300 mỗi kịch bản) ---")
    for sc_key, sc_info in scenarios.items():
        print(f"Chạy kịch bản {sc_info['name']}...")
        pol_res, pid_res = run_paired_experiment(
            polar_gains=polar_gains,
            pid_gains=pid_gains,
            poses=sc_info["poses"],
            noise=sc_info["noise"],
            base_seed=10000 + int(sc_key[1]) * 1000,
            num_workers=num_workers,
        )

        all_raw_data[sc_key] = {"polar": pol_res, "pid": pid_res}

        pol_metrics = compute_metrics(pol_res)
        pid_metrics = compute_metrics(pid_res)

        pol_metrics.update({"scenario": sc_key, "controller": "Polar"})
        pid_metrics.update({"scenario": sc_key, "controller": "DualPID"})
        metrics_rows.extend([pol_metrics, pid_metrics])

        # Kiểm định giả thuyết ghép cặp
        mcnemar = mcnemar_test_paired(pol_res, pid_res)
        wilcoxon = wilcoxon_test_paired(pol_res, pid_res)

        tests_rows.append({
            "scenario": sc_key,
            "polar_success_rate": pol_metrics["success_rate"],
            "pid_success_rate": pid_metrics["success_rate"],
            "mcnemar_stat": mcnemar["statistic"],
            "mcnemar_p_val": mcnemar["p_value"],
            "mcnemar_sig_005": mcnemar["significant_005"],
            "wilcoxon_stat": wilcoxon["statistic"],
            "wilcoxon_p_val": wilcoxon["p_value"],
            "wilcoxon_sig_005": wilcoxon["significant_005"],
        })

    # Lưu metrics S1-S5 ra CSV
    df_metrics = pd.DataFrame(metrics_rows)
    df_metrics.to_csv(out_dir / "scenario_metrics.csv", index=False)
    df_tests = pd.DataFrame(tests_rows)
    df_tests.to_csv(out_dir / "mcnemar_wilcoxon.csv", index=False)

    # --- THỰC HIỆN QUÉT HỆ SỐ NHIỄU k TRÊN BỘ NHIỄU S5 ---
    print("\n--- ĐANG CHẠY QUÉT HỆ SỐ NHIỄU k (k in {0, 0.5, 1, 1.5, 2, 3, 4}) ---")
    k_vals = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0]
    sweep_poses = test_poses[:100]  # Dùng 100 tư thế cho mỗi điểm quét để cân bằng tốc độ
    sweep_rows = []

    for k in k_vals:
        noise_k = Noise(
            sig_pos=0.02 * k,
            sig_yaw=np.radians(3.0) * k,
            sig_v=0.02 * k,
            sig_w=0.1 * k,
            delay_steps=5,  # Giữ trễ 100ms
        )
        pol_res, pid_res = run_paired_experiment(
            polar_gains=polar_gains,
            pid_gains=pid_gains,
            poses=sweep_poses,
            noise=noise_k,
            base_seed=20000 + int(k * 10),
            num_workers=num_workers,
        )
        pol_m = compute_metrics(pol_res)
        pid_m = compute_metrics(pid_res)

        sweep_rows.append({
            "k": k,
            "polar_success_rate": pol_m["success_rate"],
            "polar_ci_low": pol_m["ci_lower"],
            "polar_ci_high": pol_m["ci_upper"],
            "pid_success_rate": pid_m["success_rate"],
            "pid_ci_low": pid_m["ci_lower"],
            "pid_ci_high": pid_m["ci_upper"],
        })

    df_sweep = pd.DataFrame(sweep_rows)
    df_sweep.to_csv(out_dir / "sweep_k.csv", index=False)

    # --- NGHIÊN CỨU BÓC TÁCH (ABLATION STUDY) ---
    print("\n--- ĐANG CHẠY THỰC NGHIỆM BÓC TÁCH (ABLATION STUDY) ---")
    ablation_poses = test_poses[:100]
    ablation_noise = Noise(sig_pos=0.015, sig_yaw=np.radians(2.0), sig_v=0.01, sig_w=0.05, delay_steps=3)

    ablation_rows = []

    # 1. Polar Ablation
    polar_configs = [
        ("Polar (Gốc đầy đủ: có Freeze, có Hysteresis)", {"enable_freeze": True, "enable_hysteresis": True}),
        ("Polar (Không Freeze gần dock)", {"enable_freeze": False, "enable_hysteresis": True}),
        ("Polar (Không Hysteresis quay lưng)", {"enable_freeze": True, "enable_hysteresis": False}),
    ]
    for name, cfg in polar_configs:
        g = dict(polar_gains)
        g.update(cfg)
        tasks = [("polar", g, p, ablation_noise, 30000 + i) for i, p in enumerate(ablation_poses)]
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            res = list(executor.map(_eval_single_episode, tasks))
        m = compute_metrics(res)
        ablation_rows.append({
            "system": "Polar",
            "variant": name,
            "success_rate": m["success_rate"],
            "time_mean": m["time_mean"],
            "overshoot_rate": m["overshoot_rate"],
            "e_pos_mean": m["e_pos_mean"],
        })

    # 2. PID Ablation
    pid_configs = [
        ("PID (Gốc đầy đủ: có Lọc D, có Anti-windup)", {"enable_filter_d": True, "enable_anti_windup": True}),
        ("PID (Không Lọc D)", {"enable_filter_d": False, "enable_anti_windup": True}),
        ("PID (Không Anti-windup)", {"enable_filter_d": True, "enable_anti_windup": False}),
    ]
    for name, cfg in pid_configs:
        g = dict(pid_gains)
        g.update(cfg)
        tasks = [("pid", g, p, ablation_noise, 40000 + i) for i, p in enumerate(ablation_poses)]
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            res = list(executor.map(_eval_single_episode, tasks))
        m = compute_metrics(res)
        ablation_rows.append({
            "system": "DualPID",
            "variant": name,
            "success_rate": m["success_rate"],
            "time_mean": m["time_mean"],
            "overshoot_rate": m["overshoot_rate"],
            "e_pos_mean": m["e_pos_mean"],
        })

    df_ablation = pd.DataFrame(ablation_rows)
    df_ablation.to_csv(out_dir / "ablation.csv", index=False)

    print(f"\nĐã xuất toàn bộ kết quả CSV vào thư mục: {out_dir.resolve()}")
    return {
        "metrics": df_metrics,
        "tests": df_tests,
        "sweep": df_sweep,
        "ablation": df_ablation,
        "raw_data": all_raw_data,
    }


if __name__ == "__main__":
    run_all_scenarios(num_runs=300, num_workers=8, output_dir="results")
