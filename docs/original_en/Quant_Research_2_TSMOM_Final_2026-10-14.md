# Quant Research №2 — Literature TSMOM
## Final independent review — 2026-10-14

## 1. Research question

Does the canonical Moskowitz–Ooi–Pedersen 12-month / 1-month time-series-momentum rule contain a robust, executable edge when tested independently on a broad futures panel, after realistic transaction costs and against controls that do not require 12-month return predictability?

This project was frozen before the Phase-2 results were inspected.

## 2. Data

Source artifact:
`trendfollowing-1.3.1-py3-none-any.whl`

SHA-256:
`76beb7a35b22cb2784df98bb20a6d9ca5803c4df761398b877db765bd6562c9a`

The hash matches the official PyPI 1.3.1 wheel.

Packaged futures data:
- 84 contracts
- 17,487 daily observations
- 1959-07-02 through 2026-07-10
- 21 equity index futures
- 16 bonds
- 4 short-term interest-rate contracts
- 10 FX
- 7 energy
- 6 metals
- 20 agriculture

The wheel also contains daily one-way volume-based transaction-cost schedules.

No missing next-month return exposure was found for an active TSMOM position in the tested monthly strategy.

## 3. Frozen primary specification

At each month-end t:

1. Compute the sign of each instrument's cumulative excess return over the previous 12 months.
2. LONG if positive; SHORT if negative.
3. Estimate ex-ante annualized volatility using lagged daily returns only:
   - EWMA center of mass = 60 trading days;
   - delta = 60/61;
   - annualization = 261.
4. Individual notional scaling = `40% / ex-ante volatility`.
5. Equal-weight the scaled positions over all instruments available at that month-end.
6. Hold the resulting weights during the following calendar month.
7. Rebalance monthly.
8. No stop loss, take profit, discretionary filters or optimized lookback.

Transaction costs:
- packaged one-way volume-based cost × absolute change in portfolio notional;
- tested at 1x, 2x and 3x the published schedule.

## 4. Controls fixed before results

- `AlwaysLong_scaled`: always LONG the same tradeable universe with exactly the same volatility scaling.
- `HistoricalMean_scaled`: LONG/SHORT according to the sign of the instrument's historical sample mean return; this does not require 12-month predictability.
- `TSMOM_unscaled`: the same 12-month sign signal without volatility scaling.
- `RandomSign`: random +/- directions using the same absolute volatility-scaled risk weights.

## 5. Primary result

### 1985–2009 — original-paper era

Canonical TSMOM:

| Cost | Annual arithmetic mean | Annual vol | Sharpe | CAGR | Max DD |
|---|---:|---:|---:|---:|---:|
| Gross | 19.54% | 13.53% | 1.44 | 20.30% | -18.77% |
| 1x cost | 18.00% | 13.52% | 1.33 | 18.50% | -19.03% |
| 2x cost | 16.47% | 13.51% | 1.22 | 16.71% | -22.28% |
| 3x cost | 14.93% | 13.52% | 1.10 | 14.95% | -25.41% |

This reproduces the basic historical finding: old-sample trend following is exceptionally strong.

### 2010–2026-07 — post-paper period

| Cost | Annual arithmetic mean | Annual vol | Sharpe | CAGR | Max DD |
|---|---:|---:|---:|---:|---:|
| Gross | 6.60% | 12.26% | 0.54 | 6.01% | -18.29% |
| 1x cost | 5.87% | 12.26% | 0.48 | 5.25% | -20.45% |
| 2x cost | 5.14% | 12.25% | 0.42 | 4.49% | -22.55% |
| 3x cost | 4.41% | 12.25% | 0.36 | 3.73% | -24.60% |

The standalone strategy remains economically positive and survives even 3x the published transaction-cost schedule.

Calendar-block bootstrap for base-cost post-2009 mean:
- observed: +5.87% annual arithmetic mean
- approximate 95% interval: +0.59% to +11.97%
- bootstrap P(mean <= 0): 1.39%

So the post-2009 standalone result is not easily explained by sampling noise around zero.

## 6. The decisive control result

The important question is not merely whether TSMOM makes money.

At base transaction costs, 2010–2026:

| Strategy | Annual mean | Vol | Sharpe | CAGR | Max DD |
|---|---:|---:|---:|---:|---:|
| TSMOM scaled | 5.87% | 12.26% | 0.48 | 5.25% | -20.45% |
| Always Long, same vol scaling | 10.24% | 15.72% | 0.65 | 9.37% | -33.08% |
| Historical Mean, same scaling | 8.91% | 13.98% | 0.64 | 8.22% | -32.82% |
| TSMOM unscaled | 1.17% | 5.19% | 0.22 | 1.04% | -19.02% |

Paired 12-month-block bootstrap of annual mean differences:

### TSMOM minus Always Long, 2010–2026
- difference: -4.37%/year
- 95% interval: -12.71% to +6.68%
- no evidence that TSMOM beats the same volatility-scaled always-long exposure.

### TSMOM minus Historical Mean, 2010–2026
- difference: -3.04%/year
- 95% interval: -10.95% to +7.53%
- no evidence that the 12-month signal adds value over a rule that requires no 12-month return predictability.

This fails the pre-specified criterion that the trend signal itself must add value versus same-risk controls.

## 7. Long vs short leg

Gross annual contribution:

### 1985–2009
- LONG: +18.08%
- SHORT: +1.45%

### 2010–2026
- LONG: +8.51%
- SHORT: -1.91%

### 2020–2026
- LONG: +5.99%
- SHORT: +0.07% gross; approximately negative after allocated trading costs.

The modern strategy is therefore dominated by the long leg rather than by symmetric directional timing.

## 8. Volatility scaling matters enormously

Post-2009:

- scaled TSMOM net mean: +5.87%, Sharpe 0.48
- unscaled TSMOM net mean: +1.17%, Sharpe 0.22

The strategy's attractive headline performance depends materially on risk scaling, consistent with published criticism that volatility scaling contributes substantially to TSMOM results.

## 9. Random-sign placebo

Using 3,000 random-sign portfolios with the same dates, instruments and absolute volatility-scaled weights:

### 2010–2026 gross
- actual TSMOM annual mean: +6.60%
- median random-sign annual mean: approximately 0.0%
- 95th percentile random: +1.98%
- fraction random >= actual: 0 / 3,000

### 2020–2026 gross
- actual: +6.07%
- 95th percentile random: +3.24%
- fraction random >= actual: 0.23%

The TSMOM direction is therefore much better than arbitrary random signs.

However, this does **not** rescue the predictability claim: an always-long rule and the historical-mean rule perform as well or better. Random signs throw away persistent positive drift that these controls retain.

## 10. Cross-market robustness

Standalone per-contract 40%-vol-scaled TSMOM, net of base costs:

### 1985–2009
- 73 of 78 eligible contracts had positive mean returns: 93.6%

### 2010–2026
- 60 of 84 positive: 71.4%
- median contract annual mean: +5.88%
- median contract Sharpe: 0.14

By class, post-2009 positive-share:
- Bonds: 16/16
- STIR: 4/4
- Agriculture: 14/20
- Energy: 5/7
- Equities: 14/21
- Metals: 4/6
- FX: 3/10

The effect is broad enough not to be a one-contract artifact, but it is no longer universal.

## 11. Recent-regime concentration

2020–2026 base-cost TSMOM:
- +5.29% annual arithmetic mean
- Sharpe 0.41

But:
- excluding 2022: +1.21%/year, Sharpe 0.11
- 2023–2026-07: approximately 0.0%/year, Sharpe approximately 0

Recent asset-class net contribution:
- Agriculture: about +4.13%/year
- Bonds: +0.98%
- Energy: +0.54%
- STIR: +0.32%
- Metals: +0.12%
- FX: approximately 0%
- Equities: -0.79%

Thus most of the recent positive result is concentrated in agriculture and the strong 2022 trend regime.

The 2020+ 12-month-block bootstrap interval for base-cost mean includes zero:
- approximately -2.11% to +15.90%
- P(mean <= 0): 7.77%

## 12. Signal-definition robustness

The primary implementation uses compounded 12-month excess return.

A robustness implementation uses the arithmetic sum of the 12 monthly excess returns.

Signal directions agree on about 97.27% of eligible instrument-months.

Post-2009 base-cost:
- compounded signal: +5.87% annual mean, Sharpe 0.48
- summed signal: +6.89% annual mean, Sharpe 0.57

The central conclusion does not depend on this implementation detail.

## 13. Final verdict

### What survived

The canonical 12m/1m diversified TSMOM rule is **not bullshit** in the same sense as the failed H1 Liquidity Research execution model.

On this independent 84-market panel it:
- produces positive post-2009 returns;
- survives realistic published costs;
- survives 2x and 3x cost stress;
- is positive across a majority of individual contracts;
- beats random direction assignment decisively.

### What did not survive

It fails our stronger pre-registered question:

> Does the 12-month trend signal itself demonstrate a unique, robust predictive edge?

No.

Post-2009:
- same-risk Always Long has a higher Sharpe and mean;
- Historical Mean has a higher Sharpe and mean;
- the paired differences are not positive;
- the short leg is negative;
- removing volatility scaling leaves a weak strategy;
- the recent result is heavily concentrated in 2022/agriculture.

Therefore **Quant Research №2 v0.2 fails the pre-defined "serious trend-signal edge" threshold**, despite the strategy having positive standalone historical expectancy.

The clean interpretation is:

> Diversified futures trend following remains an economically real and historically profitable portfolio construction rule, but this test does not establish that its modern profitability is caused by 12-month return predictability. Much of the performance is consistent with long-run asset premia/drift plus volatility scaling and favorable trend regimes.

## 14. Limitations

1. The 84-contract packaged universe and continuous-futures construction were not independently reconstructed from raw exchange data.
2. Universe selection may contain ex-post design choices / survivorship characteristics that cannot be removed from the wheel alone.
3. The supplied cost schedule includes estimated transaction costs but does not fully prove real implementation cost for every venue, broker, roll and portfolio size.
4. The 40%-per-instrument volatility normalization produces substantial gross notional leverage; post-2009 average gross leverage is about 8.3x before netting.
5. No margin/funding-capital constraint, exchange position limit, tax, management fee or performance fee is modeled.
6. These limitations make the test optimistic for live implementation, not pessimistic.

## 15. Research status

Quant Research №2 is CLOSED under protocol v0.2.

Do not optimize lookback periods, filters or execution on this dataset and call the result confirmation of v0.2.

Any future alternative trend-following design must be registered as a new exploratory hypothesis.
