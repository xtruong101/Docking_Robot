"""
Phân tích và kiểm chứng ổn định cho bộ điều khiển tọa độ cực (Siegwart / Aicardi).
Bao gồm tuyến tính hóa quanh gốc, phổ trị riêng, kiểm tra điều kiện giải tích và kiểm tra số.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from typing import Dict, Any, Tuple
import numpy as np

from config import DEFAULT_POLAR_GAINS, S1_REPRESENTATIVE_POSES
from controllers import PolarController
from sim import run_episode


def get_linear_system_matrix(k_rho: float, k_alpha: float, k_beta: float) -> np.ndarray:
    """
    Ma trận hệ tuyến tính hóa A quanh gốc:
    [rho', alpha', beta']^T = A * [rho, alpha, beta]^T
    A = [
        [-k_rho,         0,       0],
        [     0, -(k_alpha - k_rho), -k_beta],
        [     0,    -k_rho,       0]
    ]
    """
    A = np.array([
        [-k_rho, 0.0, 0.0],
        [0.0, -(k_alpha - k_rho), -k_beta],
        [0.0, -k_rho, 0.0]
    ], dtype=np.float64)
    return A


def compute_eigenvalues(k_rho: float, k_alpha: float, k_beta: float) -> np.ndarray:
    """Tính các trị riêng của ma trận hệ tuyến tính hóa."""
    A = get_linear_system_matrix(k_rho, k_alpha, k_beta)
    eigenvalues = np.linalg.eigvals(A)
    return eigenvalues


def check_stability_conditions(
    k_rho: float,
    k_alpha: float,
    k_beta: float,
) -> Dict[str, Any]:
    """
    Kiểm tra các điều kiện ổn định:
    1. Ổn định tiệm cận cục bộ (Hurwitz):
       k_rho > 0, k_beta < 0, và (k_alpha - k_rho) > 0.
    2. Điều kiện không đổi chiều chuyển động (Siegwart):
       k_alpha + (5/3)*k_beta - (2/pi)*k_rho > 0.
    """
    c1 = (k_rho > 0.0)
    c2 = (k_beta < 0.0)
    c3 = ((k_alpha - k_rho) > 0.0)
    local_stability = c1 and c2 and c3

    reversal_metric = k_alpha + (5.0 / 3.0) * k_beta - (2.0 / np.pi) * k_rho
    no_reversal = reversal_metric > 0.0

    eigenvalues = compute_eigenvalues(k_rho, k_alpha, k_beta)
    max_real_eig = float(np.max(np.real(eigenvalues)))
    spectral_stability = (max_real_eig < 0.0)

    is_stable = local_stability and no_reversal and spectral_stability

    return {
        "k_rho": k_rho,
        "k_alpha": k_alpha,
        "k_beta": k_beta,
        "c1_k_rho_pos": c1,
        "c2_k_beta_neg": c2,
        "c3_k_alpha_minus_k_rho_pos": c3,
        "local_stability": local_stability,
        "reversal_metric": reversal_metric,
        "no_reversal": no_reversal,
        "spectral_stability": spectral_stability,
        "is_stable": is_stable,
        "eigenvalues": eigenvalues,
        "max_real_eigenvalue": max_real_eig,
    }


def numerical_monotonicity_check(
    controller: PolarController = None,
    num_poses: int = 60,
    seed: int = 42,
) -> Dict[str, Any]:
    """
    Kiểm tra số: mô phỏng không nhiễu từ >= 50 tư thế ban đầu phân bố đều/ngẫu nhiên.
    Đánh giá xem rho(t) có giảm đơn điệu về 0 hay không.
    """
    if controller is None:
        controller = PolarController()

    rng = np.random.default_rng(seed)
    monotonic_count = 0
    non_monotonic_count = 0
    results_list = []

    # Tạo tập tư thế bao phủ không gian làm việc
    poses = []
    # Thêm 3 tư thế đại diện S1
    for p in S1_REPRESENTATIVE_POSES:
        poses.append(p.copy())

    # Thêm các tư thế ngẫu nhiên để đủ num_poses
    for _ in range(num_poses - len(poses)):
        x0 = rng.uniform(-3.0, -0.5)
        y0 = rng.uniform(-2.0, 2.0)
        th0 = rng.uniform(-np.pi, np.pi)
        poses.append(np.array([x0, y0, th0]))

    for p in poses:
        res = run_episode(controller, init_pose=p, noise=None, seed=seed)
        rho_arr = res["rho"]
        # Đánh giá đơn điệu: rho sau không lớn hơn rho trước (cho phép sai số số học 1e-4)
        diffs = np.diff(rho_arr)
        # Chỉ xét giai đoạn trước khi vào vùng bám dock cực gần (< 0.02 m)
        active_diffs = diffs[rho_arr[:-1] > 0.03]
        if len(active_diffs) == 0:
            is_monotonic = True
        else:
            is_monotonic = bool(np.all(active_diffs <= 1e-4))

        if is_monotonic and res["ok"]:
            monotonic_count += 1
        else:
            non_monotonic_count += 1

        results_list.append({
            "pose": p.tolist(),
            "ok": res["ok"],
            "reason": res["reason"],
            "monotonic": is_monotonic,
            "final_rho": float(rho_arr[-1]),
        })

    return {
        "total_poses": len(poses),
        "monotonic_count": monotonic_count,
        "non_monotonic_count": non_monotonic_count,
        "monotonic_ratio": monotonic_count / len(poses),
        "details": results_list,
    }


def generate_stability_map_data(
    k_rho: float = DEFAULT_POLAR_GAINS["k_rho"],
    k_alpha_range: Tuple[float, float] = (0.1, 4.0),
    k_beta_range: Tuple[float, float] = (-3.0, 0.5),
    grid_size: int = 150,
) -> Dict[str, Any]:
    """Tạo lưới dữ liệu không gian tham số (k_alpha, k_beta) để vẽ bản đồ ổn định."""
    alpha_vals = np.linspace(k_alpha_range[0], k_alpha_range[1], grid_size)
    beta_vals = np.linspace(k_beta_range[0], k_beta_range[1], grid_size)
    A_grid, B_grid = np.meshgrid(alpha_vals, beta_vals)

    status_grid = np.zeros_like(A_grid, dtype=int)
    max_real_eig_grid = np.zeros_like(A_grid, dtype=float)

    for i in range(grid_size):
        for j in range(grid_size):
            ka = A_grid[i, j]
            kb = B_grid[i, j]
            check = check_stability_conditions(k_rho, ka, kb)
            max_real_eig_grid[i, j] = check["max_real_eigenvalue"]

            # Phân loại trạng thái:
            # 0: Không ổn định (max real eig >= 0 hoặc beta >= 0 hoặc ka <= k_rho)
            # 1: Ổn định tiệm cận nhưng có nguy cơ đổi chiều (reversal)
            # 2: Ổn định hoàn toàn và không đổi chiều chuyển động
            if check["local_stability"] and check["spectral_stability"]:
                if check["no_reversal"]:
                    status_grid[i, j] = 2  # Thỏa toàn bộ
                else:
                    status_grid[i, j] = 1  # Ổn định nhưng có đổi chiều
            else:
                status_grid[i, j] = 0

    return {
        "k_rho": k_rho,
        "A_grid": A_grid,
        "B_grid": B_grid,
        "status_grid": status_grid,
        "max_real_eig_grid": max_real_eig_grid,
    }
