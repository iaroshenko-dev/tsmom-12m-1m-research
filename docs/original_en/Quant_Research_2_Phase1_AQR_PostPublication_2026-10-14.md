# Quant Research №2 — Phase 1
## AQR published TSMOM factor: post-publication check

Protocol: frozen v0.2 before inspecting our own results.

### Data boundary
This phase uses the published AQR monthly aggregate Time Series Momentum factor series
(12-month lookback / 1-month holding period). The public factor series is aggregate-level,
not the unpublished daily 58-instrument panel.

The public replication source used for the numerical series states that the factor returns
are gross of transaction costs, slippage and fees. Therefore Phase 1 is a persistence test
of the published gross factor, not yet a live-tradability test.

### Main result

| Period | Months | Ann. arithmetic mean | Ann. vol | Sharpe | CAGR | Max DD |
|---|---:|---:|---:|---:|---:|---:|
| 2010-2019 | 120 | 6.04% | 12.96% | 0.466 | 5.34% | -22.72% |
| 2020-Jan 2025 | 61 | 2.64% | 14.29% | 0.184 | 1.64% | -24.56% |
| 2010-Jan 2025 | 181 | 4.89% | 13.39% | 0.365 | 4.08% | -27.77% |

The post-paper effect is positive but much weaker than the headline full-history
performance commonly associated with TSMOM. Recent 2020+ performance is weak and
strongly helped by 2022.

### Calendar years
2010 +12.81%
2011 -0.48%
2012 +0.44%
2013 +18.67%
2014 +19.10%
2015 +18.35%
2016 -11.07%
2017 +6.63%
2018 -8.79%
2019 +3.19%
2020 -6.81%
2021 -4.56%
2022 +24.72%
2023 -8.15%
2024 +3.75%
2025 Jan only +2.73%

### Uncertainty
12-month moving-block bootstrap of annualized arithmetic mean:
- 2010-Jan 2025: 95% interval about [-0.99%, +11.34%], P(mean <= 0) ~5.1%
- 2010-2019: about [-0.63%, +13.94%], P(mean <= 0) ~3.8%
- 2020-Jan 2025: about [-7.69%, +14.66%], P(mean <= 0) ~31.4%

### Phase-1 verdict
The canonical published TSMOM factor does not disappear immediately after the original
paper period, but the effect attenuates substantially. This is not yet evidence of an
executable edge because:
1. the series is gross of costs;
2. it is an aggregate factor, so we cannot independently rebuild the same-risk
   always-long, historical-mean and random-sign controls from the AQR public data alone;
3. the recent 2020+ evidence is weak and regime-dependent.

Phase 2 requires a daily multi-asset futures panel with costs. The identified open
candidate is the 84-futures 1959-2026 dataset distributed with the `trendfollowing`
package by Sepp & Lucic. The dataset is designed to include daily USD returns,
benchmarks, volume-based costs and metadata.
