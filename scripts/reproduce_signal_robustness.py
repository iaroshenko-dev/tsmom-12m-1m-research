"""Post-archive reconstruction of COMPOUND/SUM 12m signal robustness comparison.
NOT part of the frozen original code. Archived result is immutable.
"""
from pathlib import Path
import numpy as np, pandas as pd
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data/vendor/trendfollowing/resources/futures'
OUT=ROOT/'generated/reproduction'
OUT.mkdir(parents=True,exist_ok=True)
r=pd.read_csv(DATA/'tf_system_data_usd_returns.csv',index_col=0,parse_dates=True).astype(float)
c=pd.read_csv(DATA/'tf_system_data_volume_costs.csv',index_col=0,parse_dates=True).astype(float).reindex_like(r)
logr=np.log1p(r); mret=np.expm1(logr.resample('ME').sum(min_count=1)); mcost=c.resample('ME').last().reindex(mret.index)
lag=r.shift(1); alpha=1/61
em=lag.ewm(alpha=alpha,adjust=False,min_periods=60).mean();e2=lag.pow(2).ewm(alpha=alpha,adjust=False,min_periods=60).mean()
mvol=np.sqrt(261*(e2-em.pow(2)).clip(lower=0)).resample('ME').last().reindex(mret.index)
valid=mret.notna().rolling(12,min_periods=12).sum().eq(12)&mvol.notna()&(mvol>0)
sigs={'COMPOUND':np.sign(np.expm1(np.log1p(mret).rolling(12,min_periods=12).sum())), 'SUM':np.sign(mret.rolling(12,min_periods=12).sum())}
periods={'MOP_1985_2009':('1985-01-01','2009-12-31'),'POST_2009':('2010-01-01',None),'POST_2020':('2020-01-01',None)}
rows=[]
for name,sig in sigs.items():
    availability=valid&sig.notna(); n=availability.sum(axis=1).replace(0,np.nan)
    targets=((0.4/mvol)*sig).where(availability,0).div(n,axis=0).fillna(0)
    w=targets.shift(1).fillna(0); gross=(w*mret.fillna(0)).sum(axis=1)
    costs=((w-w.shift(1).fillna(0)).abs()*mcost.ffill().bfill()).sum(axis=1)
    for period,(s,e) in periods.items():
        for label, series in [('gross',gross),('net_1x',gross-costs)]:
            z=series.loc[s:e]; wealth=(1+z).cumprod()
            rows.append(dict(signal_def=name,period=period,cost_case=label,months=len(z),ann_mean=12*z.mean(),ann_vol=np.sqrt(12)*z.std(ddof=1),sharpe=(12*z.mean())/(np.sqrt(12)*z.std(ddof=1)),cagr=wealth.iloc[-1]**(12/len(z))-1))
out=pd.DataFrame(rows)
out.to_csv(OUT/'signal_definition_robustness.csv',index=False)
arch=pd.read_csv(ROOT/'results/signal_definition_robustness.csv')
assert list(out.columns)==list(arch.columns) and out.shape==arch.shape
for col in out.columns:
    if pd.api.types.is_numeric_dtype(out[col]):
        if not np.allclose(out[col],arch[col],atol=1e-10,rtol=1e-10,equal_nan=True):
            raise AssertionError('Reconstruction disagrees with archive in '+col)
    elif not out[col].equals(arch[col]):
        raise AssertionError('Reconstruction label mismatch in '+col)
print('Reconstructed signal robustness matches original archived 12x8 CSV.')
