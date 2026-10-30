# Quant Research №2 — Literature TSMOM
Frozen protocol v0.2 — 2026-10-14

## Primary hypothesis
Canonical Moskowitz–Ooi–Pedersen time-series momentum:
- signal: sign of each instrument's own past 12-month excess return;
- holding period: next 1 month;
- diversified futures/forwards universe;
- point-in-time volatility scaling;
- no stop-loss, no take-profit, no discretionary filters.

The primary specification is frozen. We do not change 12m/1m after seeing results.

## Core tests
1. Canonical TSMOM + volatility scaling.
2. Same volatility scaling, always long.
3. TSMOM without volatility scaling.
4. Random-sign placebo preserving dates, instruments and risk weights.
5. Historical-mean control: position based on the sign of each instrument's expanding/lagged historical mean excess return.

Control 5 is added before our own backtest after reviewing Huang, Li, Wang & Zhou (JFE 2020), who argue that TSMOM portfolio profitability can resemble a strategy based on historical sample means and therefore does not by itself establish return predictability.

## Periods fixed before results
- Original-paper / discovery era: through 2009.
- Post-paper test: 2010 onward.
- Recent regime: 2020 onward.

The post-2009 result is the primary credibility test.

## Costs
Report:
- gross;
- base realistic transaction costs;
- 2x costs;
- 3x costs.

No cost parameter may be chosen because it turns the result positive.

## Required outputs
For every strategy/control:
- annualized arithmetic mean excess return;
- annualized volatility;
- Sharpe ratio;
- compounded wealth/CAGR where meaningful;
- max drawdown;
- skewness;
- turnover;
- cost drag;
- yearly and subperiod returns;
- asset-class attribution;
- number of active instruments through time.

Inference:
- calendar/block bootstrap confidence intervals;
- TSMOM vs always-long;
- TSMOM vs historical-mean control;
- scaled vs unscaled;
- TSMOM vs random-sign placebo.

## Verdict rule
Do not call it a serious tradable candidate unless:
- net expectancy is positive post-2009;
- performance is not concentrated in one asset or short regime;
- the trend signal adds value versus same-risk controls;
- modestly higher costs do not erase the result;
- implementation is point-in-time and free of look-ahead/survivorship mistakes.

## Anti-overfitting rule
No grid search over alternative lookbacks or holding periods until the canonical 12m/1m result is recorded and frozen.
