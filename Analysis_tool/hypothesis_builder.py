from itertools import count

import numpy as np

def fact(n):
    return 1 if n==0 else n * fact(n-1)

def bino(n, k):
    return fact(n)//(fact(n-int(k))*fact(int(k)))

########################################################################################################################

def n_antecedent(ant, d):
    key_ = list(ant.keys())[0]
    data = d[key_]

    return {key for key in data.keys() if (set(data[key].split(';')).intersection(ant[key_])) != set()}

def n_consequent(conseq, d):
    key_ = list(conseq.keys())[0]
    data = d[key_]

    return {key for key in data.keys() if (set(data[key].split(';')).intersection(conseq[key_])) != set()}

def odds_ratio(conf, br, su, n_ant, n):

    if conf == 1:
        return np.nan if (n_ant / n) - br + su == 1 else float("inf")

    if 1 - (n_ant / n) - br + su == 0:
        return np.nan if br == su else 0

    if br == su:
        return np.nan if conf == 0 else float("inf")

    denom = conf / (1 - conf)
    num = (br - su) / (1 - (n_ant / n) - br + su)

    return denom / num

def p_value(br, n_ant, n_j, n):
    func = lambda k: (bino(n_ant, k) * bino(n-n_ant, n*br-k)) / bino(n, n*br)
    return sum([func(i) for i in range(n_j, int(min(n_ant, n*br))+1)])

def q_value(pre_reports: list[dict], number):

    ordering_function = lambda x: x["p_value"]
    pre_reports.sort(key=ordering_function)
    m = len(pre_reports)

    count = 0
    for i in range(m, 0, -1):
        print(f"q_values calculated: {count}/{number}", end="\r")
        count += 1
        pre_reports[i - 1]["q_value"] = (
            min(1, min([(m / j) * pre_reports[j - 1]["p_value"] for j in range(i, m + 1)])))
    return

def hypothesis_tester(antecedent, consequent, data):

    k = list(data.keys())[0]
    N = len(data[k])

    if N == 0:
        raise "Error, illegal input!!!"

    reduced_set_x = n_antecedent(antecedent, data)
    reduced_set_y = n_consequent(consequent, data)

    n_xy = len(reduced_set_x.intersection(reduced_set_y))

    n_x = len(reduced_set_x)
    n_y = len(reduced_set_y)

    sup = n_xy / N
    base = n_y / N

    con = n_xy / n_x if n_x != 0 else np.nan
    lif = np.nan if np.isnan(con) else (
    float("inf") if base == 0 else con / base)

    pr_x = n_x / N
    lev = sup - pr_x * base

    p = p_value(base, n_x, n_xy, N)

    return {
            "antecedent": antecedent,
            "consequent": consequent,

            "n_antecedent": n_x,
            "n_joint": n_xy,

            "support": sup,
            "confidence": con,
            "base_rate": base,
            "lift": lif,
            "leverage": lev,

            "odds_ratio": odds_ratio(con, base, sup, n_x, N),
            "p_value": p,
        }
