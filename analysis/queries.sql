-- ============================================================
-- queries.sql
-- Israeli Savings Plans — analytical SQL layer (DuckDB)
-- ============================================================
-- Run against: data/savings.duckdb
-- Each query answers one of the seven business questions from the README
-- ============================================================

-- ── Q1. Which bank offers the highest and lowest rate today? ─────────────────

WITH latest AS (
    SELECT
        BANK_EN,
        RateType,
        RateValue,
        INTERESTSDATE,
        ROW_NUMBER() OVER (
            PARTITION BY BANK_EN, RateType
            ORDER BY INTERESTSDATE DESC
        ) AS rn
    FROM savings_rates
    WHERE RateValue IS NOT NULL
),
ranked AS (
    SELECT
        BANK_EN,
        RateType,
        RateValue,
        INTERESTSDATE                                           AS AsOfDate,
        RANK() OVER (PARTITION BY RateType ORDER BY RateValue DESC) AS RankDesc,
        RANK() OVER (PARTITION BY RateType ORDER BY RateValue ASC)  AS RankAsc
    FROM latest
    WHERE rn = 1
)
SELECT
    BANK_EN,
    RateType,
    ROUND(RateValue, 4)  AS LatestRate,
    AsOfDate,
    CASE
        WHEN RankDesc = 1 THEN 'Highest'
        WHEN RankAsc  = 1 THEN 'Lowest'
        ELSE 'Mid-range'
    END                  AS Position
FROM ranked
WHERE RankDesc = 1 OR RankAsc = 1
ORDER BY RateType, RankDesc;


-- ── Q2. Average rate per bank and plan type ──────────────────────────────────

SELECT
    COALESCE(BANK_EN,       '— ALL BANKS —')     AS Bank,
    COALESCE(SAVINGSPLAN_EN,'— ALL PLANS —')     AS Plan,
    COALESCE(RateType,      '— ALL TYPES —')     AS RateType,
    ROUND(AVG(RateValue), 4)                     AS AvgRate,
    COUNT(*)                                     AS Observations
FROM savings_rates
WHERE RateValue IS NOT NULL
GROUP BY ROLLUP (BANK_EN, SAVINGSPLAN_EN, RateType)
ORDER BY Bank, Plan, RateType;


-- ── Q3. Rate distribution across banks — percentile spread ──────────────────

SELECT
    BANK_EN,
    RateType,
    ROUND(AVG(RateValue),                             4) AS AvgRate,
    ROUND(STDDEV(RateValue),                          4) AS StdDev,
    ROUND(PERCENTILE_CONT(0.25) WITHIN GROUP
          (ORDER BY RateValue),                       4) AS P25,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP
          (ORDER BY RateValue),                       4) AS Median,
    ROUND(PERCENTILE_CONT(0.75) WITHIN GROUP
          (ORDER BY RateValue),                       4) AS P75,
    ROUND(MAX(RateValue) - MIN(RateValue),            4) AS Delta
FROM savings_rates
WHERE RateValue IS NOT NULL
GROUP BY BANK_EN, RateType
ORDER BY AvgRate DESC;


-- ── Q4. Do rates differ between Under-18 and Above-18 programs? ─────────────

WITH age_pivot AS (
    SELECT
        BANK_EN,
        SAVINGSPLAN_EN,
        RateType,
        ROUND(AVG(RateValue) FILTER (
            WHERE SAVINGSPROGRAMBYAGE_EN = 'Under 18'), 4) AS AvgRate_Under18,
        ROUND(AVG(RateValue) FILTER (
            WHERE SAVINGSPROGRAMBYAGE_EN = 'Above 18'), 4) AS AvgRate_Above18
    FROM savings_rates
    WHERE RateValue IS NOT NULL
    GROUP BY BANK_EN, SAVINGSPLAN_EN, RateType
)
SELECT
    BANK_EN,
    SAVINGSPLAN_EN,
    RateType,
    AvgRate_Under18,
    AvgRate_Above18,
    ROUND(AvgRate_Under18 - AvgRate_Above18, 4) AS Gap_Under_vs_Above
FROM age_pivot
WHERE AvgRate_Under18 IS NOT NULL
   OR AvgRate_Above18 IS NOT NULL
ORDER BY ABS(COALESCE(AvgRate_Under18, 0) - COALESCE(AvgRate_Above18, 0)) DESC;


-- ── Q5. Interest rate trend over time — MoM change with LAG ─────────────────

WITH monthly AS (
    SELECT
        YEAR_MONTH,
        MIN(INTERESTSDATE) AS PeriodStart,
        RateType,
        ROUND(AVG(RateValue), 4) AS AvgRate
    FROM savings_rates
    WHERE RateValue IS NOT NULL
    GROUP BY YEAR_MONTH, RateType
),
with_lag AS (
    SELECT
        YEAR_MONTH,
        RateType,
        AvgRate,
        LAG(AvgRate) OVER (
            PARTITION BY RateType ORDER BY PeriodStart
        ) AS PrevMonthRate,
        ROUND(AvgRate - LAG(AvgRate) OVER (
            PARTITION BY RateType ORDER BY PeriodStart
        ), 4) AS MoM_Delta
    FROM monthly
)
SELECT
    YEAR_MONTH      AS "Year-Month",
    RateType        AS "Rate Type",
    AvgRate         AS "Avg Rate (%)",
    PrevMonthRate,
    MoM_Delta       AS "MoM Δ",
    CASE
        WHEN MoM_Delta > 0 THEN '↑ Rising'
        WHEN MoM_Delta < 0 THEN '↓ Falling'
        WHEN MoM_Delta = 0 THEN '→ Stable'
        ELSE 'n/a'
    END AS Trend
FROM with_lag
ORDER BY "Rate Type", "Year-Month";


-- ── Q6. Volatility ranking — how stable is each bank? ───────────────────────

WITH vol AS (
    SELECT
        BANK_EN,
        RateType,
        ROUND(MAX(RateValue) - MIN(RateValue), 4) AS Delta,
        ROUND(STDDEV(RateValue),               4) AS StdDev,
        COUNT(*)                                  AS Observations
    FROM savings_rates
    WHERE RateValue IS NOT NULL
    GROUP BY BANK_EN, RateType
)
SELECT
    BANK_EN,
    RateType,
    Delta,
    StdDev,
    Observations,
    NTILE(3) OVER (PARTITION BY RateType ORDER BY Delta ASC) AS StabilityTier,
    -- 1 = most stable, 3 = most volatile
    CASE NTILE(3) OVER (PARTITION BY RateType ORDER BY Delta ASC)
        WHEN 1 THEN 'Stable'
        WHEN 2 THEN 'Moderate'
        WHEN 3 THEN 'Volatile'
    END AS StabilityLabel
FROM vol
ORDER BY RateType, Delta ASC;


-- ── Q7. Best deal finder — top rate per age group and plan, latest date ──────

SELECT
    BANK_EN,
    SAVINGSPLAN_EN,
    SAVINGSPROGRAMBYAGE_EN,
    RateType,
    ROUND(RateValue, 4) AS BestRate,
    INTERESTSDATE       AS AsOfDate
FROM savings_rates
WHERE RateValue IS NOT NULL
  AND RateValue > 0          -- exclude nominal-loss rates
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY SAVINGSPLAN_EN, SAVINGSPROGRAMBYAGE_EN, RateType
    ORDER BY RateValue DESC, INTERESTSDATE DESC
) = 1
ORDER BY SAVINGSPROGRAMBYAGE_EN, SAVINGSPLAN_EN, RateType;
