from collections import defaultdict

from qverify_simulation.config import CHSH_IDEAL
from qverify_simulation.statistics.chsh import chsh_corr


def relative_error_cal(approximate_value, true_value):
    try:
        error = (approximate_value - true_value) / abs(true_value)
        return round(error, 3)
    except ZeroDivisionError:
        return None


def average_and_normalize_probabilities(*dicts):
    combined = defaultdict(lambda: [0, 0])
    for d in dicts:
        for val, prob in d.items():
            combined[val][0] += prob
            combined[val][1] += 1
    averaged_dict = {val: total / num for val, (total, num) in combined.items()}
    total_sum = sum(averaged_dict.values())
    normalized_dict = {val: prob / total_sum for val, prob in averaged_dict.items()}
    return {val: round(prob, 3) for val, prob in normalized_dict.items()}


def compute_error_dist_eb(res, BA, BB, num_qubits, bin_size=5):
    error_dist = {}
    for k, v in res.items():
        parts = k[::-1].split(" ")
        rai, rbi = parts[0], parts[1]
        chsh_i = chsh_corr(rai, rbi, BA, BB)
        if chsh_i is None:
            continue
        re_i = relative_error_cal(chsh_i, CHSH_IDEAL)
        if re_i is None:
            continue
        pct = round(100.0 * abs(re_i) / bin_size) * bin_size
        pct = min(float(pct), 100.0)
        error_dist[pct] = error_dist.get(pct, 0) + v
    return error_dist


def compute_error_dist_pm(res, RA, BA, BB, num_qubits, bin_size=5):
    error_dist = {}
    for k, v in res.items():
        rbi = k[::-1]
        chsh_i = chsh_corr(RA, rbi, BA, BB)
        if chsh_i is None:
            continue
        re_i = relative_error_cal(chsh_i, CHSH_IDEAL)
        if re_i is None:
            continue
        pct = round(100.0 * abs(re_i) / bin_size) * bin_size
        pct = min(float(pct), 100.0)
        error_dist[pct] = error_dist.get(pct, 0) + v
    return error_dist
