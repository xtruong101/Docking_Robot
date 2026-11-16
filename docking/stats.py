"""
Thống kê, chỉ số hiệu năng và kiểm định giả thuyết ý nghĩa thống kê.
Bao gồm khoảng tin cậy Wilson 95%, kiểm định McNemar và kiểm định Wilcoxon signed-rank.
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from scipy import stats


def wilson_ci(k: int, n: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Tính khoảng tin cậy Wilson 95% cho tỷ lệ thành công p = k / n.
    Trả về (ci_lower, ci_upper).
    """
    if n <= 0:
        return 0.0, 0.0
    p = float(k) / float(n)
    z = float(stats.norm.ppf(1.0 - (1.0 - confidence) / 2.0))
    denom = 1.0 + (z**2) / float(n)
    center = (p + (z**2) / (2.0 * float(n))) / denom
    half_width = (z * np.sqrt((p * (1.0 - p) / float(n)) + (z**2) / (4.0 * float(n)**2))) / denom
    ci_lower = max(0.0, float(center - half_width))
    ci_upper = min(1.0, float(center + half_width))
    return ci_lower, ci_upper


def compute_metrics(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Tính toán toàn bộ các chỉ số thống kê từ danh sách kết quả các tập chạy:
    - Tỷ lệ thành công kèm khoảng tin cậy Wilson 95%
    - Thời gian docking (mean +- std, median trên các ca thành công)
    - Tỷ lệ timeout, overshoot, sai hướng
    - Sai số vị trí và hướng cuối cùng
    - Chiều dài quỹ đạo và năng lượng điều khiển tích phân
    """
    n_total = len(results)
    if n_total == 0:
        return {}

    n_success = sum(1 for r in results if r["ok"])
    success_rate = n_success / n_total
    ci_low, ci_high = wilson_ci(n_success, n_total)

    n_overshoot = sum(1 for r in results if r["reason"] == "overshoot")
    overshoot_rate = n_overshoot / n_total

    n_timeout = sum(1 for r in results if r["reason"] == "timeout")
    timeout_rate = n_timeout / n_total

    n_wrong_heading = sum(1 for r in results if r["reason"] == "wrong_heading")
    wrong_heading_rate = n_wrong_heading / n_total

    # Thời gian docking chỉ tính trên các ca THÀNH CÔNG
    succ_times = [r["t"] for r in results if r["ok"]]
    if succ_times:
        time_mean = float(np.mean(succ_times))
        time_std = float(np.std(succ_times))
        time_median = float(np.median(succ_times))
    else:
        time_mean = float("nan")
        time_std = float("nan")
        time_median = float("nan")

    e_pos_all = [r["e_pos"] for r in results]
    e_yaw_all = [r["e_yaw"] for r in results]
    path_all = [r["path_length"] for r in results]
    energy_all = [r["energy"] for r in results]

    return {
        "n_total": n_total,
        "n_success": n_success,
        "success_rate": success_rate,
        "ci_lower": ci_low,
        "ci_upper": ci_high,
        "overshoot_rate": overshoot_rate,
        "timeout_rate": timeout_rate,
        "wrong_heading_rate": wrong_heading_rate,
        "time_mean": time_mean,
        "time_std": time_std,
        "time_median": time_median,
        "e_pos_mean": float(np.mean(e_pos_all)),
        "e_pos_std": float(np.std(e_pos_all)),
        "e_pos_median": float(np.median(e_pos_all)),
        "e_yaw_mean": float(np.mean(e_yaw_all)),
        "e_yaw_std": float(np.std(e_yaw_all)),
        "e_yaw_median": float(np.median(e_yaw_all)),
        "path_mean": float(np.mean(path_all)),
        "path_std": float(np.std(path_all)),
        "energy_mean": float(np.mean(energy_all)),
        "energy_std": float(np.std(energy_all)),
    }


def mcnemar_test_paired(
    results_a: List[Dict[str, Any]],
    results_b: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Kiểm định McNemar cho biến định tính nhị phân ghép cặp (Thành công / Thất bại).
    Bảng tiếp liên 2x2:
                 B Thắng    B Thua
    A Thắng         n11       n10
    A Thua          n01       n00
    """
    assert len(results_a) == len(results_b), "Hai tập kết quả phải có cùng số phần tử ghép cặp!"
    n = len(results_a)

    n11 = 0  # Cả hai cùng thành công
    n10 = 0  # A thành công, B thất bại
    n01 = 0  # A thất bại, B thành công
    n00 = 0  # Cả hai cùng thất bại

    for ra, rb in zip(results_a, results_b):
        a_ok = ra["ok"]
        b_ok = rb["ok"]
        if a_ok and b_ok:
            n11 += 1
        elif a_ok and not b_ok:
            n10 += 1
        elif not a_ok and b_ok:
            n01 += 1
        else:
            n00 += 1

    table = [[n11, n10], [n01, n00]]

    # Nếu không có sự khác biệt nào giữa hai bên
    if n10 + n01 == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "table": table,
            "significant_005": False,
        }

    try:
        # Sử dụng kiểm định chính xác (exact binomial) nếu b + c < 25
        exact = (n10 + n01) < 25
        res = stats.mcnemar(table, exact=exact, correction=True)
        stat = float(res.statistic)
        pval = float(res.pvalue)
    except Exception:
        # Tự tính theo phân phối chuẩn có hiệu chỉnh liên tục
        b, c = n10, n01
        stat = (abs(b - c) - 1.0)**2 / (b + c)
        pval = float(1.0 - stats.chi2.cdf(stat, df=1))

    return {
        "statistic": stat,
        "p_value": pval,
        "table": table,
        "significant_005": pval < 0.05,
    }


def wilcoxon_test_paired(
    results_a: List[Dict[str, Any]],
    results_b: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Kiểm định phi tham số Wilcoxon signed-rank cho thời gian docking ghép cặp
    trên các ca mà CẢ HAI BỘ ĐIỀU KHIỂN CÙNG THÀNH CÔNG.
    """
    t_a = []
    t_b = []
    for ra, rb in zip(results_a, results_b):
        if ra["ok"] and rb["ok"]:
            t_a.append(ra["t"])
            t_b.append(rb["t"])

    n_pairs = len(t_a)
    if n_pairs < 10:
        return {
            "statistic": float("nan"),
            "p_value": float("nan"),
            "n_pairs": n_pairs,
            "significant_005": False,
            "note": "Số cặp cùng thành công < 10, không đủ độ tin cậy thực hiện Wilcoxon",
        }

    diffs = np.array(t_a) - np.array(t_b)
    # Loại bỏ trường hợp hiệu số đúng bằng 0
    diffs_nonzero = diffs[diffs != 0.0]
    if len(diffs_nonzero) < 5:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "n_pairs": n_pairs,
            "significant_005": False,
        }

    res = stats.wilcoxon(t_a, t_b)
    stat = float(res.statistic)
    pval = float(res.pvalue)

    return {
        "statistic": stat,
        "p_value": pval,
        "n_pairs": n_pairs,
        "significant_005": pval < 0.05,
    }
