"""Credit score + 50% FOIR capacity. Pure Python, no Django imports.

Inputs are plain tuples so the same function serves the dashboard, CSV and KFS.
  blocks: (t_start_s, work_min, credited_mwh)   sales: (at_ms, amount_paise)  [confirmed only]
Credited energy is already the >300 W filtered figure (firmware side).
"""
DAY = 86400
REV_PER_KWH = 150.0   # Rs of output per productive kWh: calibrate per trade with pilot data
NET_MARGIN = 0.35     # share of revenue that is household income
FOIR = 0.50           # max share of income that may go to EMIs
TENURE = 12           # months
LIMIT_MIN, LIMIT_MAX, STEP = 5000, 50000, 500


def score(blocks, sales, alerts=0, now=0.0, rev_per_kwh=REV_PER_KWH):
    def win(days):
        lo = now - days * DAY
        b = [x for x in blocks if x[0] >= lo]
        return b, sum(x[2] for x in b) / 1e6, sum(x[1] for x in b) / 60, sum(a for t, a in sales if t / 1000 >= lo) / 100
    b30, kwh30, h30, sold30 = win(30)
    b90, kwh90, _, _ = win(90)
    active_days = len({int(x[0] // DAY) for x in b30})
    consistency = min(1.0, active_days / 30)
    # seasonality: last 30 days vs the 90-day monthly average (1.0 = steady)
    seasonality = round(kwh30 / (kwh90 / 3), 2) if kwh90 else 0.0
    est = kwh30 * rev_per_kwh
    flags = []
    if alerts:
        flags.append(f"{alerts} tamper alert(s): field audit")
    if sold30 and est and not 0.5 <= sold30 / est <= 2.0:
        flags.append("logged sales and energy-estimated revenue differ by more than 2x")
    # conservative: lend against the lower of the two revenue signals
    revenue = min(sold30, est) if sold30 else 0.0
    if not sold30:
        flags.append("no confirmed sales logged in 30 days")
    emi = revenue * NET_MARGIN * FOIR
    limit = int(emi * TENURE * consistency // STEP * STEP)
    limit = 0 if limit < LIMIT_MIN or alerts else min(limit, LIMIT_MAX)
    return {"kwh30": round(kwh30, 1), "workHours30": round(h30, 1), "activeDays30": active_days,
            "consistency": round(consistency, 2), "seasonality": seasonality,
            "energyRevenue30": round(est), "loggedSales30": round(sold30), "monthlyIncome": round(revenue * NET_MARGIN),
            "emiCapacity": round(emi), "tenureMonths": TENURE, "limit": limit, "flags": flags, "blocks90": len(b90)}


def _demo():
    now = 100 * DAY
    blocks = [(now - d * DAY, 480, 2_000_000) for d in range(30)]       # 2 kWh/day for 30 days
    r = score(blocks, [(now * 1000 - 1000, 1_000_000)], now=now)         # Rs 10,000 logged
    assert r["kwh30"] == 60 and r["energyRevenue30"] == 9000 and r["consistency"] == 1.0, r
    assert r["emiCapacity"] == 1575 and r["limit"] == 18900 // 500 * 500, r   # 9000*.35*.5=1575 *12
    assert score(blocks, [], now=now)["limit"] == 0                      # no sales -> no limit
    assert score(blocks, [(now * 1000, 1_000_000)], alerts=1, now=now)["limit"] == 0
    assert score([], [], now=now)["limit"] == 0


if __name__ == "__main__":
    _demo()
    print("scoring ok")
