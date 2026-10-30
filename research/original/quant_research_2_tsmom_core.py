"""
Quant Research #2 — canonical 12m/1m TSMOM core.

Input contract:
- daily_excess_returns.csv: index column `date`; remaining columns are instrument
  daily simple excess returns (decimal, e.g. 0.001 = 0.1%).
- optional daily_cost_per_unit_turnover.csv: same shape or broadcastable; cost
  in return units per 1.0 change in portfolio weight.

This is intentionally a small, readable reference implementation.
It does not optimize lookbacks.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

AF = 260
LOOKBACK_MONTHS = 12
VOL_COM = 60.0
TARGET_VOL_PER_ASSET = 0.40
EPS = 1e-12


def ewma_vol(daily_returns: pd.DataFrame) -> pd.DataFrame:
    # Ex-ante only: shift by one day before variance estimate is used.
    var = daily_returns.pow(2).ewm(com=VOL_COM, adjust=False, min_periods=60).mean()
    return np.sqrt(AF * var).shift(1)


def month_end_returns(daily_returns: pd.DataFrame) -> pd.DataFrame:
    # Compound simple daily excess returns to calendar-month returns.
    return (1.0 + daily_returns).resample("ME").prod() - 1.0


def trailing_12m_signal(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    trailing = (1.0 + monthly_returns).rolling(LOOKBACK_MONTHS, min_periods=LOOKBACK_MONTHS).apply(
        np.prod, raw=True
    ) - 1.0
    return np.sign(trailing)


def lagged_historical_mean_signal(monthly_returns: pd.DataFrame) -> pd.DataFrame:
    # Expanding mean known at each month-end, lagged before next-month application.
    return np.sign(monthly_returns.expanding(min_periods=12).mean())


def build_monthly_weights(
    daily_returns: pd.DataFrame,
    signal_kind: str = "tsmom",
    volatility_scaling: bool = True,
) -> pd.DataFrame:
    mret = month_end_returns(daily_returns)

    if signal_kind == "tsmom":
        signal = trailing_12m_signal(mret)
    elif signal_kind == "always_long":
        signal = pd.DataFrame(1.0, index=mret.index, columns=mret.columns)
    elif signal_kind == "historical_mean":
        signal = lagged_historical_mean_signal(mret)
    else:
        raise ValueError(signal_kind)

    if volatility_scaling:
        dvol = ewma_vol(daily_returns)
        # last ex-ante vol observation available at each month-end
        mvol = dvol.resample("ME").last().reindex(mret.index)
        weights = signal * TARGET_VOL_PER_ASSET / mvol.clip(lower=EPS)
    else:
        weights = signal.copy()

    # Equal-weight across available instruments.
    available = weights.notna().sum(axis=1).replace(0, np.nan)
    weights = weights.div(available, axis=0)

    # Decision at month-end t applies to month t+1.
    return weights.shift(1)


def portfolio_returns(
    daily_returns: pd.DataFrame,
    weights_monthly: pd.DataFrame,
) -> pd.Series:
    mret = month_end_returns(daily_returns)
    w = weights_monthly.reindex(mret.index)
    return (w * mret).sum(axis=1, min_count=1).dropna()


def metrics(r: pd.Series) -> dict:
    r = r.dropna()
    if len(r) < 2:
        return {}
    ann_mean = 12 * r.mean()
    ann_vol = np.sqrt(12) * r.std(ddof=1)
    wealth = (1 + r).cumprod()
    dd = wealth / wealth.cummax() - 1
    return {
        "n_months": len(r),
        "annualized_arithmetic_mean": ann_mean,
        "annualized_volatility": ann_vol,
        "sharpe": ann_mean / ann_vol if ann_vol > 0 else np.nan,
        "cagr": wealth.iloc[-1] ** (12 / len(r)) - 1,
        "max_drawdown": dd.min(),
        "skew": r.skew(),
    }


def run_core(daily_returns: pd.DataFrame) -> pd.DataFrame:
    specs = [
        ("TSMOM_scaled", "tsmom", True),
        ("AlwaysLong_scaled", "always_long", True),
        ("TSMOM_unscaled", "tsmom", False),
        ("HistoricalMean_scaled", "historical_mean", True),
    ]
    rows = []
    for name, signal, scaled in specs:
        w = build_monthly_weights(daily_returns, signal, scaled)
        r = portfolio_returns(daily_returns, w)
        for period_name, start in [("FULL", None), ("POST_2009", "2010-01-01"), ("POST_2020", "2020-01-01")]:
            z = r if start is None else r.loc[start:]
            row = {"strategy": name, "period": period_name}
            row.update(metrics(z))
            rows.append(row)
    return pd.DataFrame(rows)


if __name__ == "__main__":
    df = pd.read_csv("daily_excess_returns.csv", index_col=0, parse_dates=True).sort_index()
    out = run_core(df)
    out.to_csv("quant_research_2_core_results.csv", index=False)
    print(out.to_string(index=False))
