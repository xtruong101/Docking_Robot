"""
Mô-đun vẽ và xuất toàn bộ 10 đồ thị kỹ thuật (PNG 300 dpi và PDF vector).
Nhãn trục bằng tiếng Việt có đơn vị chuẩn, thiết kế trực quan, khoa học.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

import json
from typing import Dict, Any, List
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

from config import (
    V_MAX,
    W_MAX,
    POS_TOLERANCE,
    YAW_TOLERANCE,
    OVERSHOOT_X_LIMIT,
    S1_REPRESENTATIVE_POSES,
    DEFAULT_POLAR_GAINS,
    DEFAULT_PID_GAINS,
    Noise,
)
from controllers import PolarController, DualPIDController
from sim import run_episode
from stability import generate_stability_map_data, check_stability_conditions
from experiments import load_best_gains, generate_s4_poses
from stats import compute_metrics, wilson_ci

# Cài đặt cấu hình đồ họa Matplotlib
plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.autolayout"] = True


def save_fig(fig: plt.Figure, name: str, output_dir: Path) -> None:
    """Lưu hình ảnh ở cả hai định dạng PNG 300 dpi và PDF vector."""
    png_path = output_dir / f"{name}.png"
    pdf_path = output_dir / f"{name}.pdf"
    fig.savefig(png_path, dpi=300, bbox_inches="tight")
    fig.savefig(pdf_path, bbox_inches="tight")
    plt.close(fig)
    print(f"  Đã lưu: {png_path.name} & {pdf_path.name}")


def plot_fig1_coordinate_system(output_dir: Path) -> None:
    """Hình 1: Sơ đồ hệ tọa độ dock và robot."""
    fig, ax = plt.subplots(figsize=(8, 6))

    # Vẽ trục tọa độ toàn cục O-xy
    ax.axhline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.axvline(0, color="black", linestyle="--", linewidth=0.8, alpha=0.7)

    # Vùng dock và dung sai
    dock_box = patches.Rectangle((-0.1, -0.15), 0.1, 0.3, facecolor="#e0e0e0", edgecolor="black", linewidth=1.5, hatch="//", label="Trạm sạc (Dock)")
    ax.add_patch(dock_box)

    # Vùng dung sai vị trí (2cm)
    tol_circle = patches.Circle((0, 0), radius=POS_TOLERANCE, facecolor="#a8e6cf", edgecolor="#1b5e20", linestyle="--", alpha=0.6, label=f"Vùng dung sai vị trí ({POS_TOLERANCE*100:.0f} cm)")
    ax.add_patch(tol_circle)

    # Đường giới hạn vượt dock (overshoot limit x = 0.05 m)
    ax.axvline(OVERSHOOT_X_LIMIT, color="red", linestyle=":", linewidth=2.0, label=f"Giới hạn vượt dock (x = {OVERSHOOT_X_LIMIT} m)")

    # Trục hướng dock (+x)
    ax.annotate("", xy=(0.25, 0.0), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color="red", lw=2.5))
    ax.text(0.26, 0.02, "Trục Dock (+x)", color="red", fontsize=11, fontweight="bold")

    # Robot tại vị trí minh họa (-1.0, 0.6, 30 độ)
    rx, ry, rth = -1.0, 0.6, np.radians(35.0)
    robot_radius = 0.12
    robot_circle = patches.Circle((rx, ry), radius=robot_radius, facecolor="#bbdefb", edgecolor="#0d47a1", linewidth=2.0, label="Robot vi sai")
    ax.add_patch(robot_circle)

    # Hai bánh xe
    L_half = 0.115
    for sign in [-1, 1]:
        wx = rx - sign * L_half * np.sin(rth)
        wy = ry + sign * L_half * np.cos(rth)
        wheel_rect = patches.Rectangle((wx - 0.03, wy - 0.015), 0.06, 0.03, angle=np.degrees(rth), facecolor="black", edgecolor="black")
        ax.add_patch(wheel_rect)

    # Hướng robot theta
    head_len = 0.3
    hx = rx + head_len * np.cos(rth)
    hy = ry + head_len * np.sin(rth)
    ax.annotate("", xy=(hx, hy), xytext=(rx, ry), arrowprops=dict(arrowstyle="-|>", color="#0d47a1", lw=2.5))
    ax.text(hx + 0.02, hy + 0.02, r"Góc hướng $\theta$", color="#0d47a1", fontsize=11)

    # Đường ngắm từ robot tới dock (line of sight)
    ax.plot([rx, 0], [ry, 0], color="purple", linestyle="--", linewidth=1.5, label=r"Khoảng cách $\rho$ tới dock")
    ax.text((rx + 0) / 2.0 - 0.1, (ry + 0) / 2.0 + 0.05, r"$\rho = \sqrt{x^2+y^2}$", color="purple", fontsize=11)

    # Chú thích góc alpha và beta
    ax.text(rx + 0.1, ry - 0.05, r"$\alpha$: Góc ngắm lệch", color="#c2185b", fontsize=10)
    ax.text(0.05, -0.1, r"$\beta$: Góc tiếp cận dock", color="#00796b", fontsize=10)

    ax.set_xlim(-1.5, 0.6)
    ax.set_ylim(-0.5, 1.0)
    ax.set_xlabel("Trục X (m)", fontsize=12)
    ax.set_ylabel("Trục Y (m)", fontsize=12)
    ax.set_title("Hình 1: Sơ đồ hệ tọa độ Dock và Robot vi sai", fontsize=14, fontweight="bold")
    ax.set_aspect("equal")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="upper left", fontsize=9)

    save_fig(fig, "fig1_dock_robot_coordinate_system", output_dir)


def plot_fig2_s1_trajectories(polar_gains: Dict[str, Any], pid_gains: Dict[str, Any], output_dir: Path) -> None:
    """Hình 2: Quỹ đạo S1 từ 3 tư thế đại diện xếp chồng hai bộ điều khiển có mũi tên hướng."""
    fig, ax = plt.subplots(figsize=(9, 7))

    ctrl_polar = PolarController(**polar_gains)
    ctrl_pid = DualPIDController(**pid_gains)

    colors = ["#1976d2", "#e64a19", "#388e3c"]
    labels_pose = [
        "Tư thế 1: Phía trước (-2, 0, 0)",
        "Tư thế 2: Lệch bên (-1.5, 1.5, 0)",
        "Tư thế 3: Quay lưng (-1.5, 0.5, π)",
    ]

    # Vẽ dock và vùng dung sai
    ax.add_patch(patches.Circle((0, 0), radius=POS_TOLERANCE, facecolor="#a8e6cf", edgecolor="#1b5e20", linestyle="--", alpha=0.7, label=f"Vùng đích (r={POS_TOLERANCE*100:.0f}cm)"))
    ax.axvline(OVERSHOOT_X_LIMIT, color="red", linestyle=":", label=f"Overshoot (x>{OVERSHOOT_X_LIMIT}m)")

    for idx, pose in enumerate(S1_REPRESENTATIVE_POSES):
        res_pol = run_episode(ctrl_polar, pose, noise=None)
        res_pid = run_episode(ctrl_pid, pose, noise=None)

        traj_pol = res_pol["traj"]
        traj_pid = res_pid["traj"]

        c = colors[idx]
        # Vẽ đường quỹ đạo
        ax.plot(traj_pol[:, 0], traj_pol[:, 1], color=c, linestyle="-", linewidth=2.2, label=f"Polar - {labels_pose[idx]}" if idx == 0 else None)
        ax.plot(traj_pid[:, 0], traj_pid[:, 1], color=c, linestyle="--", linewidth=2.0, alpha=0.85, label=f"DualPID - {labels_pose[idx]}" if idx == 0 else None)

        # Đánh dấu điểm bắt đầu
        ax.plot(pose[0], pose[1], marker="o", color=c, markersize=8)
        ax.text(pose[0] - 0.05, pose[1] + 0.08, f"P{idx+1}", fontweight="bold", color=c, fontsize=11)

        # Thêm mũi tên hướng dọc đường đi cho Polar
        step_arrow = max(1, len(traj_pol) // 8)
        for s in range(0, len(traj_pol), step_arrow):
            px, py, pth = traj_pol[s, 0], traj_pol[s, 1], traj_pol[s, 2]
            ax.annotate("", xy=(px + 0.08 * np.cos(pth), py + 0.08 * np.sin(pth)), xytext=(px, py), arrowprops=dict(arrowstyle="-|>", color=c, lw=1.2))

    # Dummy lines cho legend kiểu bộ điều khiển
    ax.plot([], [], color="black", linestyle="-", linewidth=2, label="Bộ điều khiển Polar (Liền)")
    ax.plot([], [], color="black", linestyle="--", linewidth=2, label="Bộ điều khiển DualPID (Đứt)")

    ax.set_xlabel("Vị trí X (m)", fontsize=12)
    ax.set_ylabel("Vị trí Y (m)", fontsize=12)
    ax.set_title("Hình 2: So sánh quỹ đạo S1 từ 3 tư thế đại diện", fontsize=14, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.set_aspect("equal")
    ax.legend(loc="lower left", fontsize=9)

    save_fig(fig, "fig2_s1_trajectories", output_dir)


def plot_fig3_s1_time_response(polar_gains: Dict[str, Any], pid_gains: Dict[str, Any], output_dir: Path) -> None:
    """Hình 3: Đáp ứng thời gian v(t), w(t), rho(t), e_theta(t) của S1 cho cả hai bộ."""
    # Chọn tư thế 2 (lệch bên) để thấy rõ đáp ứng động học
    pose = S1_REPRESENTATIVE_POSES[1]  # (-1.5, 1.5, 0)
    ctrl_pol = PolarController(**polar_gains)
    ctrl_pid = DualPIDController(**pid_gains)

    res_pol = run_episode(ctrl_pol, pose, noise=None)
    res_pid = run_episode(ctrl_pid, pose, noise=None)

    fig, axes = plt.subplots(2, 2, figsize=(11, 8), sharex=True)

    # 1. Vận tốc dài v(t)
    axes[0, 0].plot(res_pol["time_array"], res_pol["v"], label="Polar", color="#1976d2", linewidth=2)
    axes[0, 0].plot(res_pid["time_array"], res_pid["v"], label="DualPID", color="#e64a19", linestyle="--", linewidth=2)
    axes[0, 0].axhline(V_MAX, color="red", linestyle=":", label=f"Giới hạn V_MAX ({V_MAX} m/s)")
    axes[0, 0].set_ylabel("Vận tốc dài v (m/s)", fontsize=11)
    axes[0, 0].set_title("(a) Vận tốc dài v(t)", fontsize=12, fontweight="bold")
    axes[0, 0].grid(True, linestyle=":", alpha=0.6)
    axes[0, 0].legend(loc="upper right", fontsize=9)

    # 2. Vận tốc góc w(t)
    axes[0, 1].plot(res_pol["time_array"], res_pol["w"], label="Polar", color="#1976d2", linewidth=2)
    axes[0, 1].plot(res_pid["time_array"], res_pid["w"], label="DualPID", color="#e64a19", linestyle="--", linewidth=2)
    axes[0, 1].axhline(W_MAX, color="red", linestyle=":")
    axes[0, 1].axhline(-W_MAX, color="red", linestyle=":", label=f"Giới hạn ±W_MAX (±{W_MAX} rad/s)")
    axes[0, 1].set_ylabel("Vận tốc góc ω (rad/s)", fontsize=11)
    axes[0, 1].set_title("(b) Vận tốc góc ω(t)", fontsize=12, fontweight="bold")
    axes[0, 1].grid(True, linestyle=":", alpha=0.6)
    axes[0, 1].legend(loc="upper right", fontsize=9)

    # 3. Khoảng cách rho(t)
    axes[1, 0].plot(res_pol["time_array"], res_pol["rho"], label="Polar", color="#1976d2", linewidth=2)
    axes[1, 0].plot(res_pid["time_array"], res_pid["rho"], label="DualPID", color="#e64a19", linestyle="--", linewidth=2)
    axes[1, 0].axhline(POS_TOLERANCE, color="green", linestyle=":", label=f"Ngưỡng thành công ({POS_TOLERANCE*100:.0f} cm)")
    axes[1, 0].set_xlabel("Thời gian t (s)", fontsize=11)
    axes[1, 0].set_ylabel("Khoảng cách ρ (m)", fontsize=11)
    axes[1, 0].set_title("(c) Khoảng cách tới dock ρ(t)", fontsize=12, fontweight="bold")
    axes[1, 0].grid(True, linestyle=":", alpha=0.6)
    axes[1, 0].legend(loc="upper right", fontsize=9)

    # 4. Sai số góc
    axes[1, 1].plot(res_pol["time_array"], np.degrees(res_pol["heading_err"]), label=r"Polar ($\alpha$)", color="#1976d2", linewidth=2)
    axes[1, 1].plot(res_pid["time_array"], np.degrees(res_pid["heading_err"]), label=r"DualPID ($e_\theta$)", color="#e64a19", linestyle="--", linewidth=2)
    axes[1, 1].set_xlabel("Thời gian t (s)", fontsize=11)
    axes[1, 1].set_ylabel("Sai số góc (độ)", fontsize=11)
    axes[1, 1].set_title("(d) Sai số định hướng", fontsize=12, fontweight="bold")
    axes[1, 1].grid(True, linestyle=":", alpha=0.6)
    axes[1, 1].legend(loc="upper right", fontsize=9)

    fig.suptitle("Hình 3: Đáp ứng động học tín hiệu điều khiển và trạng thái (Tư thế P2: (-1.5, 1.5, 0))", fontsize=13, fontweight="bold")
    save_fig(fig, "fig3_s1_time_response", output_dir)


def plot_fig4_multi_pose(polar_gains: Dict[str, Any], pid_gains: Dict[str, Any], test_poses: List[np.ndarray], output_dir: Path) -> None:
    """Hình 4: Quỹ đạo nhiều tư thế (≈20) mỗi bộ, hai panel cạnh nhau."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 6), sharey=True)

    ctrl_pol = PolarController(**polar_gains)
    ctrl_pid = DualPIDController(**pid_gains)

    poses_sample = test_poses[:20]

    for ax, ctrl, title, color in zip([ax1, ax2], [ctrl_pol, ctrl_pid], ["Bộ điều khiển Tọa độ cực (Polar)", "Bộ điều khiển Hai vòng PID (DualPID)"], ["#1976d2", "#e64a19"]):
        ax.add_patch(patches.Circle((0, 0), radius=POS_TOLERANCE, facecolor="#a8e6cf", edgecolor="#1b5e20", linestyle="--", alpha=0.8, label=f"Đích ({POS_TOLERANCE*100:.0f}cm)"))
        ax.axvline(OVERSHOOT_X_LIMIT, color="red", linestyle=":", label="Overshoot")

        for p in poses_sample:
            res = run_episode(ctrl, p, noise=None)
            traj = res["traj"]
            ax.plot(traj[:, 0], traj[:, 1], color=color, alpha=0.7, linewidth=1.5)
            ax.plot(p[0], p[1], marker="o", color=color, markersize=4)

        ax.set_xlabel("Trục X (m)", fontsize=11)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.6)
        ax.set_aspect("equal")
        ax.legend(loc="lower left", fontsize=9)

    ax1.set_ylabel("Trục Y (m)", fontsize=11)
    fig.suptitle("Hình 4: Quỹ đạo hội tụ từ 20 tư thế khởi đầu ngẫu nhiên", fontsize=14, fontweight="bold")
    save_fig(fig, "fig4_multi_pose_trajectories", output_dir)


def plot_fig5_boxplots(df_metrics: pd.DataFrame, all_raw_data: Dict[str, Any], output_dir: Path) -> None:
    """Hình 5: Boxplot sai số vị trí, sai số hướng, thời gian theo kịch bản S2–S5."""
    scenarios = ["S2", "S3", "S4", "S5"]
    fig, axes = plt.subplots(1, 3, figsize=(14, 5))

    # Chuẩn bị dữ liệu boxplot ghép cặp
    data_pos = {"Polar": [], "DualPID": []}
    data_yaw = {"Polar": [], "DualPID": []}
    data_time = {"Polar": [], "DualPID": []}

    for sc in scenarios:
        if sc in all_raw_data:
            p_res = all_raw_data[sc]["polar"]
            d_res = all_raw_data[sc]["pid"]

            data_pos["Polar"].append([r["e_pos"] for r in p_res])
            data_pos["DualPID"].append([r["e_pos"] for r in d_res])

            data_yaw["Polar"].append([np.degrees(r["e_yaw"]) for r in p_res])
            data_yaw["DualPID"].append([np.degrees(r["e_yaw"]) for r in d_res])

            # Chỉ lấy thời gian của ca thành công
            data_time["Polar"].append([r["t"] for r in p_res if r["ok"]])
            data_time["DualPID"].append([r["t"] for r in d_res if r["ok"]])

    # Vẽ cho từng trục
    width = 0.35
    x = np.arange(len(scenarios))

    titles = [
        "(a) Sai số vị trí cuối cùng (m)",
        "(b) Sai số góc hướng cuối cùng (độ)",
        "(c) Thời gian docking ca thành công (s)",
    ]

    for ax_idx, (data_dict, title) in enumerate(zip([data_pos, data_yaw, data_time], titles)):
        ax = axes[ax_idx]
        bp1 = ax.boxplot(data_dict["Polar"], positions=x - width/2.0, widths=width * 0.8, patch_artist=True, boxprops=dict(facecolor="#90caf9", color="#1976d2"), medianprops=dict(color="#0d47a1", lw=1.5), showfliers=False)
        bp2 = ax.boxplot(data_dict["DualPID"], positions=x + width/2.0, widths=width * 0.8, patch_artist=True, boxprops=dict(facecolor="#ffab91", color="#e64a19"), medianprops=dict(color="#bf360c", lw=1.5), showfliers=False)

        ax.set_xticks(x)
        ax.set_xticklabels(scenarios, fontsize=11)
        ax.set_title(title, fontsize=11, fontweight="bold")
        ax.grid(True, linestyle=":", alpha=0.6)

        if ax_idx == 0:
            ax.set_ylabel("Giá trị", fontsize=11)
            ax.legend([bp1["boxes"][0], bp2["boxes"][0]], ["Polar", "DualPID"], loc="upper left", fontsize=9)

    fig.suptitle("Hình 5: Phân bố sai số và thời gian docking qua các kịch bản S2 - S5", fontsize=13, fontweight="bold")
    save_fig(fig, "fig5_boxplots_s2_s5", output_dir)


def plot_fig6_success_rates(df_metrics: pd.DataFrame, output_dir: Path) -> None:
    """Hình 6: Cột tỷ lệ thành công theo kịch bản kèm thanh sai số Wilson 95%."""
    scenarios = ["S1", "S2", "S3", "S4", "S5"]
    x = np.arange(len(scenarios))
    width = 0.35

    polar_rows = df_metrics[df_metrics["controller"] == "Polar"]
    pid_rows = df_metrics[df_metrics["controller"] == "DualPID"]

    p_succ = [polar_rows[polar_rows["scenario"] == sc]["success_rate"].values[0] * 100 for sc in scenarios]
    p_err_low = [max(0.0, p_succ[i] - polar_rows[polar_rows["scenario"] == sc]["ci_lower"].values[0] * 100) for i, sc in enumerate(scenarios)]
    p_err_high = [max(0.0, polar_rows[polar_rows["scenario"] == sc]["ci_upper"].values[0] * 100 - p_succ[i]) for i, sc in enumerate(scenarios)]

    d_succ = [pid_rows[pid_rows["scenario"] == sc]["success_rate"].values[0] * 100 for sc in scenarios]
    d_err_low = [max(0.0, d_succ[i] - pid_rows[pid_rows["scenario"] == sc]["ci_lower"].values[0] * 100) for i, sc in enumerate(scenarios)]
    d_err_high = [max(0.0, pid_rows[pid_rows["scenario"] == sc]["ci_upper"].values[0] * 100 - d_succ[i]) for i, sc in enumerate(scenarios)]

    fig, ax = plt.subplots(figsize=(9, 6))

    bars1 = ax.bar(x - width/2.0, p_succ, width, yerr=[p_err_low, p_err_high], capsize=5, label="Polar Controller", color="#1976d2", edgecolor="black")
    bars2 = ax.bar(x + width/2.0, d_succ, width, yerr=[d_err_low, d_err_high], capsize=5, label="DualPID Controller", color="#e64a19", edgecolor="black")

    # Ghi số % lên đầu cột
    for bar in bars1:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h + 2.0, f"{h:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#0d47a1")
    for bar in bars2:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2.0, h + 2.0, f"{h:.1f}%", ha="center", va="bottom", fontsize=9, fontweight="bold", color="#bf360c")

    ax.set_ylabel("Tỷ lệ docking thành công (%)", fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios, fontsize=11)
    ax.set_ylim(0, 115)
    ax.set_title("Hình 6: Tỷ lệ thành công theo kịch bản (kèm khoảng tin cậy Wilson 95%)", fontsize=13, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6, axis="y")
    ax.legend(loc="upper right", fontsize=10)

    save_fig(fig, "fig6_success_rates_wilson", output_dir)


def plot_fig7_sweep_noise(df_sweep: pd.DataFrame, output_dir: Path) -> None:
    """Hình 7: Đường tỷ lệ thành công theo hệ số nhiễu (quét k)."""
    fig, ax = plt.subplots(figsize=(8, 5.5))

    k = df_sweep["k"]
    p_rate = df_sweep["polar_success_rate"] * 100
    p_low = df_sweep["polar_ci_low"] * 100
    p_high = df_sweep["polar_ci_high"] * 100

    d_rate = df_sweep["pid_success_rate"] * 100
    d_low = df_sweep["pid_ci_low"] * 100
    d_high = df_sweep["pid_ci_high"] * 100

    ax.plot(k, p_rate, marker="o", linewidth=2.2, color="#1976d2", label="Polar Controller")
    ax.fill_between(k, p_low, p_high, color="#90caf9", alpha=0.35)

    ax.plot(k, d_rate, marker="s", linewidth=2.2, color="#e64a19", linestyle="--", label="DualPID Controller")
    ax.fill_between(k, d_low, d_high, color="#ffab91", alpha=0.35)

    ax.set_xlabel("Hệ số nhân cường độ nhiễu k (trên nền kịch bản S5)", fontsize=11)
    ax.set_ylabel("Tỷ lệ thành công (%)", fontsize=11)
    ax.set_ylim(-5, 105)
    ax.set_title("Hình 7: Độ nhạy và độ bền vững trước mức tăng nhiễu k", fontsize=13, fontweight="bold")
    ax.grid(True, linestyle=":", alpha=0.6)
    ax.legend(loc="lower left", fontsize=10)

    save_fig(fig, "fig7_sweep_noise", output_dir)


def plot_fig8_stability(polar_gains: Dict[str, Any], output_dir: Path) -> None:
    """Hình 8: Bản đồ vùng ổn định gain và phổ trị riêng (Section 5)."""
    k_rho = polar_gains.get("k_rho", DEFAULT_POLAR_GAINS["k_rho"])
    map_data = generate_stability_map_data(k_rho=k_rho, grid_size=120)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5))

    # 1. Bản đồ vùng ổn định
    # 0: Không ổn định, 1: Ổn định có đổi chiều, 2: Ổn định không đổi chiều
    cax = ax1.contourf(map_data["A_grid"], map_data["B_grid"], map_data["status_grid"], levels=[-0.5, 0.5, 1.5, 2.5], colors=["#ef9a9a", "#fff59d", "#a5d6a7"])

    # Đường ranh giới lý thuyết: k_alpha - k_rho = 0
    alpha_line = np.linspace(0.1, 4.0, 100)
    ax1.axvline(k_rho, color="blue", linestyle="--", label=r"Hurwitz: $k_\alpha = k_\rho$")
    ax1.axhline(0, color="black", linestyle="--", label=r"Hurwitz: $k_\beta = 0$")

    # Đường không đảo chiều: k_alpha + 5/3*k_beta - 2/pi*k_rho = 0 => k_beta = -3/5 * (k_alpha - 2/pi*k_rho)
    beta_reversal = -0.6 * (alpha_line - (2.0 / np.pi) * k_rho)
    ax1.plot(alpha_line, beta_reversal, color="purple", linestyle="-.", label="Ranh giới không đổi chiều")

    # Đánh dấu gain đã chọn
    ka_sel = polar_gains.get("k_alpha", DEFAULT_POLAR_GAINS["k_alpha"])
    kb_sel = polar_gains.get("k_beta", DEFAULT_POLAR_GAINS["k_beta"])
    ax1.plot(ka_sel, kb_sel, marker="*", color="red", markersize=14, label=f"Gain đã chọn ({ka_sel:.2f}, {kb_sel:.2f})")

    ax1.set_xlabel(r"Hệ số $k_\alpha$", fontsize=12)
    ax1.set_ylabel(r"Hệ số $k_\beta$", fontsize=12)
    ax1.set_title(f"(a) Vùng ổn định (k_rho = {k_rho:.2f})", fontsize=12, fontweight="bold")
    ax1.set_ylim(-3.0, 0.5)
    ax1.set_xlim(0.1, 4.0)
    ax1.legend(loc="lower left", fontsize=8)
    ax1.grid(True, linestyle=":", alpha=0.6)

    # 2. Phổ trị riêng lớn nhất max(Re(lambda)) khi quét k_alpha
    ka_sweep = np.linspace(0.2, 4.0, 100)
    for kb in [-0.2, -0.6, -1.2, -2.0]:
        max_eigs = []
        for ka in ka_sweep:
            ch = check_stability_conditions(k_rho, ka, kb)
            max_eigs.append(ch["max_real_eigenvalue"])
        ax2.plot(ka_sweep, max_eigs, label=f"$k_\\beta = {kb}$", linewidth=1.8)

    ax2.axhline(0, color="red", linestyle=":", label="Ngưỡng ổn định Re=0")
    ax2.set_xlabel(r"Hệ số $k_\alpha$", fontsize=12)
    ax2.set_ylabel(r"$\max(\mathrm{Re}(\lambda))$", fontsize=12)
    ax2.set_title(r"(b) Phần thực trị riêng lớn nhất $\max(\mathrm{Re}(\lambda))$", fontsize=12, fontweight="bold")
    ax2.grid(True, linestyle=":", alpha=0.6)
    ax2.legend(loc="upper right", fontsize=9)

    fig.suptitle("Hình 8: Phân tích ổn định lý thuyết bộ điều khiển tọa độ cực", fontsize=14, fontweight="bold")
    save_fig(fig, "fig8_stability_analysis", output_dir)


def plot_fig9_heatmap(polar_gains: Dict[str, Any], pid_gains: Dict[str, Any], output_dir: Path) -> None:
    """Hình 9: Heatmap tỷ lệ thành công theo vị trí xuất phát (x0, y0) trung bình theo theta0."""
    x_bins = np.linspace(-3.0, -0.5, 7)
    y_bins = np.linspace(-2.0, 2.0, 7)

    nx = len(x_bins) - 1
    ny = len(y_bins) - 1

    ctrl_pol = PolarController(**polar_gains)
    ctrl_pid = DualPIDController(**pid_gains)
    s2_noise = Noise(sig_pos=0.01, sig_yaw=np.radians(1.0))

    grid_pol = np.zeros((ny, nx))
    grid_pid = np.zeros((ny, nx))

    # Đánh giá 6 góc định hướng ngẫu nhiên cho mỗi ô lưới
    theta_samples = np.linspace(-np.pi, np.pi, 6, endpoint=False)

    for i in range(ny):
        y_mid = 0.5 * (y_bins[i] + y_bins[i+1])
        for j in range(nx):
            x_mid = 0.5 * (x_bins[j] + x_bins[j+1])
            pol_ok_cnt = 0
            pid_ok_cnt = 0
            for idx, th in enumerate(theta_samples):
                p = np.array([x_mid, y_mid, th])
                r_pol = run_episode(ctrl_pol, p, noise=s2_noise, seed=100 + idx)
                r_pid = run_episode(ctrl_pid, p, noise=s2_noise, seed=100 + idx)
                if r_pol["ok"]:
                    pol_ok_cnt += 1
                if r_pid["ok"]:
                    pid_ok_cnt += 1
            grid_pol[i, j] = pol_ok_cnt / len(theta_samples) * 100
            grid_pid[i, j] = pid_ok_cnt / len(theta_samples) * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5.5), sharey=True)

    im1 = ax1.imshow(grid_pol, origin="lower", extent=[x_bins[0], x_bins[-1], y_bins[0], y_bins[-1]], cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax1.set_xlabel("Vị trí X0 (m)", fontsize=11)
    ax1.set_ylabel("Vị trí Y0 (m)", fontsize=11)
    ax1.set_title("Polar Controller", fontsize=12, fontweight="bold")

    im2 = ax2.imshow(grid_pid, origin="lower", extent=[x_bins[0], x_bins[-1], y_bins[0], y_bins[-1]], cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")
    ax2.set_xlabel("Vị trí X0 (m)", fontsize=11)
    ax2.set_title("DualPID Controller", fontsize=12, fontweight="bold")

    fig.colorbar(im2, ax=[ax1, ax2], label="Tỷ lệ thành công (%)", orientation="vertical", fraction=0.03, pad=0.04)
    fig.suptitle("Hình 9: Bản đồ nhiệt (Heatmap) tỷ lệ thành công theo không gian vị trí ban đầu (x0, y0)", fontsize=13, fontweight="bold")
    save_fig(fig, "fig9_heatmap_success_map", output_dir)


def plot_fig10_ablation(df_ablation: pd.DataFrame, output_dir: Path) -> None:
    """Hình 10: Ablation study cho hai bộ điều khiển."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))

    polar_df = df_ablation[df_ablation["system"] == "Polar"]
    pid_df = df_ablation[df_ablation["system"] == "DualPID"]

    # Rút gọn nhãn hiển thị
    labels_polar = ["Gốc đầy đủ", "Không Freeze", "Không Hysteresis"]
    rates_polar = polar_df["success_rate"].values * 100

    labels_pid = ["Gốc đầy đủ", "Không Lọc D", "Không Anti-windup"]
    rates_pid = pid_df["success_rate"].values * 100

    # 1. Panel Polar
    bars1 = ax1.bar(labels_polar, rates_polar, color=["#1976d2", "#42a5f5", "#90caf9"], edgecolor="black", width=0.55)
    ax1.set_ylabel("Tỷ lệ thành công (%)", fontsize=11)
    ax1.set_title("(a) Bóc tách: Bộ điều khiển Tọa độ cực (Polar)", fontsize=11, fontweight="bold")
    ax1.set_ylim(0, 115)
    ax1.grid(True, linestyle=":", alpha=0.6, axis="y")
    for b in bars1:
        h = b.get_height()
        ax1.text(b.get_x() + b.get_width()/2.0, h + 2.0, f"{h:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    # 2. Panel PID
    bars2 = ax2.bar(labels_pid, rates_pid, color=["#e64a19", "#ff7043", "#ffab91"], edgecolor="black", width=0.55)
    ax2.set_ylabel("Tỷ lệ thành công (%)", fontsize=11)
    ax2.set_title("(b) Bóc tách: Bộ điều khiển Hai vòng PID (DualPID)", fontsize=11, fontweight="bold")
    ax2.set_ylim(0, 115)
    ax2.grid(True, linestyle=":", alpha=0.6, axis="y")
    for b in bars2:
        h = b.get_height()
        ax2.text(b.get_x() + b.get_width()/2.0, h + 2.0, f"{h:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")

    fig.suptitle("Hình 10: Đánh giá vai trò của từng thành phần kỹ thuật (Ablation Study)", fontsize=13, fontweight="bold")
    save_fig(fig, "fig10_ablation_study", output_dir)


def generate_all_plots(figures_dir: str = "figures", results_dir: str = "results") -> None:
    """Hàm chính sinh toàn bộ 10 hình vẽ kỹ thuật theo yêu cầu mục 9."""
    fig_dir = Path(figures_dir)
    fig_dir.mkdir(parents=True, exist_ok=True)
    res_dir = Path(results_dir)

    print("=== BẮT ĐẦU VẼ TOÀN BỘ 10 HÌNH KỸ THUẬT (PNG 300 dpi & PDF) ===")

    polar_gains, pid_gains = load_best_gains()

    # Đọc dữ liệu thực nghiệm đã chạy
    df_metrics = pd.read_csv(res_dir / "scenario_metrics.csv")
    df_sweep = pd.read_csv(res_dir / "sweep_k.csv")
    df_ablation = pd.read_csv(res_dir / "ablation.csv")

    from tuning import generate_poses
    from config import SEED_TEST
    test_poses = generate_poses(300, seed=SEED_TEST)

    # Chạy lại một số lượt nhanh để lấy phân bố thô cho boxplot nếu cần
    from experiments import run_paired_experiment, Noise
    all_raw_data = {}
    for sc in ["S2", "S3", "S4", "S5"]:
        if sc == "S2":
            ns = Noise(sig_pos=0.01, sig_yaw=np.radians(1.0))
            ps = test_poses[:80]
        elif sc == "S3":
            ns = Noise(sig_v=0.01, sig_w=0.05, delay_steps=4)
            ps = test_poses[:80]
        elif sc == "S4":
            ns = Noise(sig_pos=0.005, sig_yaw=np.radians(0.5))
            ps = generate_s4_poses(80)
        else:
            ns = Noise(sig_pos=0.02, sig_yaw=np.radians(3.0), sig_v=0.02, sig_w=0.1, delay_steps=5)
            ps = test_poses[:80]
        p_res, d_res = run_paired_experiment(polar_gains, pid_gains, ps, ns, base_seed=50000, num_workers=4)
        all_raw_data[sc] = {"polar": p_res, "pid": d_res}

    print("1. Đang vẽ Hình 1: Sơ đồ hệ tọa độ dock và robot...")
    plot_fig1_coordinate_system(fig_dir)

    print("2. Đang vẽ Hình 2: Quỹ đạo S1 từ 3 tư thế đại diện...")
    plot_fig2_s1_trajectories(polar_gains, pid_gains, fig_dir)

    print("3. Đang vẽ Hình 3: Đáp ứng thời gian v(t), w(t), rho(t), e_theta(t)...")
    plot_fig3_s1_time_response(polar_gains, pid_gains, fig_dir)

    print("4. Đang vẽ Hình 4: Quỹ đạo nhiều tư thế (2 panel)...")
    plot_fig4_multi_pose(polar_gains, pid_gains, test_poses, fig_dir)

    print("5. Đang vẽ Hình 5: Boxplot sai số và thời gian S2 - S5...")
    plot_fig5_boxplots(df_metrics, all_raw_data, fig_dir)

    print("6. Đang vẽ Hình 6: Cột tỷ lệ thành công (thanh sai số Wilson 95%)...")
    plot_fig6_success_rates(df_metrics, fig_dir)

    print("7. Đang vẽ Hình 7: Đường tỷ lệ thành công theo hệ số nhiễu k...")
    plot_fig7_sweep_noise(df_sweep, fig_dir)

    print("8. Đang vẽ Hình 8: Bản đồ vùng ổn định gain và phổ trị riêng...")
    plot_fig8_stability(polar_gains, fig_dir)

    print("9. Đang vẽ Hình 9: Heatmap tỷ lệ thành công theo (x0, y0)...")
    plot_fig9_heatmap(polar_gains, pid_gains, fig_dir)

    print("10. Đang vẽ Hình 10: Ablation study...")
    plot_fig10_ablation(df_ablation, fig_dir)

    print(f"\nĐÃ HOÀN TẤT SINH 10 BỘ ĐỒ THỊ TRONG: {fig_dir.resolve()}")


if __name__ == "__main__":
    generate_all_plots(figures_dir="figures", results_dir="results")
