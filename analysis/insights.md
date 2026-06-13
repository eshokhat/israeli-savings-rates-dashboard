# Key Insights — Israeli Children's Savings Plans

Analysis based on data from 9 Israeli banks, covering May 2025 – June 2026.
Three rate types: Fixed (No Linkage), Fixed (CPI-Linked), Variable (Prime Spread).

---

## 1. Mizrahi-Tefahot leads today; Leumi leads historically

As of June 2026, **Mizrahi-Tefahot** offers the highest Fixed (No Linkage) rate at **4.45%**,
narrowly ahead of Leumi (3.94%) and Discount (3.36%). However, over the full observation
period, **Leumi** holds the highest average Fixed (No Linkage) rate at **3.94%** with lower
volatility (StdDev 0.42, Δ 2.40) compared to Mizrahi-Tefahot (StdDev 0.65, Δ 3.45).

The all-time peak in the dataset: **Mizrahi-Tefahot, Fixed Deposit (No Early Withdrawal),
Under 18, Fixed (No Linkage) — 5.00%** on 08 March 2026.

For **Fixed (CPI-Linked)**, **Discount** leads both today (2.35%) and historically (avg 1.94%).

---

## 2. Yahav is a consistent underperformer — with one exception

Yahav ranks last or near-last across almost every metric:
- Lowest Fixed (No Linkage) today: **3.10%** vs market leader 4.45%
- Most aggressive Variable spread: **−4.75%** today (market worst)
- Lowest average Fixed (No Linkage): **2.02%** over the full period

The single exception: Yahav has the **most stable CPI-Linked rate** in the market
(Δ = 0.05, StdDev = 0.008) — it simply barely moves. This is a specialised bank
(primarily serving military personnel) and not a competitive choice for general savings.

---

## 3. Variable (Prime Spread) rates are frozen by bank policy, not market forces

Q5 analysis shows Variable spreads barely changed across 14 months — monthly deltas
typically below 0.01%. Banks are not competing on Variable spreads; they set a fixed
discount to Prime Rate and leave it unchanged. The actual yield for Variable products
is driven entirely by Bank of Israel Prime Rate decisions (~4.5% currently), not by
inter-bank competition.

**Reading Variable rates:** a spread of −0.80% (Mizrahi-Tefahot, best in market today)
means actual yield ≈ 4.5% − 0.80% = **3.70%**. A spread of −4.75% (Yahav, worst)
means actual yield ≈ **−0.25%** — a real loss in nominal terms.

---

## 4. The market is in a slow but consistent downward trend

Fixed (No Linkage) rates declined from ~2.57% (May 2025) to ~2.47% (June 2026) at
market average — a ~4% drop over 14 months. This is consistent with Bank of Israel's
monetary easing cycle. Fixed (CPI-Linked) shows more month-to-month volatility but
follows a similar mild downward trend (0.80% → 0.76% market average).

---

## 5. Most savings plans are age-segregated — not dual-audience products

Q4 analysis reveals that most bank-plan combinations appear exclusively in either
Under 18 OR Above 18 programs, not both. A side-by-side gap comparison (Under 18
minus Above 18) is only calculable for a subset of products. Where both exist,
the differences are small — the major differentiator is the plan type and bank,
not the age group.

---

## 6. Mercantile Discount and Discount are the most stable Fixed (No Linkage) banks

For savers who prioritise predictability over peak rate:
- **Discount**: Δ = 1.88, StdDev = 0.34 (Stable tier)
- **Mercantile Discount**: Δ = 2.05, StdDev = 0.37 (Stable tier)

International Bank, Massad, and Otsar Ha-Hayal show the highest volatility
(Δ = 3.30) despite offering lower average rates — the worst combination for
a conservative saver.

---

## 7. Best current deals by use case (as of June 2026)

| Use case | Bank | Rate | Type |
|---|---|---|---|
| Highest fixed rate, any plan | Mizrahi-Tefahot | 4.45% | Fixed (No Linkage) |
| Most stable fixed rate | Discount | 1.88% Δ | Fixed (No Linkage) |
| Best CPI-linked rate | Discount | 2.35% | Fixed (CPI-Linked) |
| Best Variable spread | Mizrahi-Tefahot | −0.80% | Variable (Prime Spread) |
| Best historical deal (Under 18) | Mizrahi-Tefahot | 5.00% | Fixed (No Linkage) |

---

## Known Limitations

- Data covers May 2025 – June 2026 only (API limitation — no earlier history available).
- Variable (Prime Spread) values are spreads, not absolute yields.
  Actual yield = Prime Rate (~4.5%) + Spread.
- Prime Rate history not integrated — true Variable yield comparison requires
  joining with Bank of Israel rate data (planned for next iteration).
- Q4 gap analysis limited by age-segregated product structure in the source data.
