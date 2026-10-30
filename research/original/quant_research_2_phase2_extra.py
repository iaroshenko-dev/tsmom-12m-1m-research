from pathlib import Path
import pandas as pd, numpy as np, json
B=Path('/mnt/data/quant_research_2_phase2')
# reload script namespace without redoing placebo? Importing executes heavy. Instead reconstruct needed raw panels compactly.
ROOT=Path('/mnt/data/quant_research_2_wheel/trendfollowing/resources/futures')
AF=261.; delta=60/61; alpha=1-delta; target=0.40
r=pd.read_csv(ROOT/'tf_system_data_usd_returns.csv',index_col=0,parse_dates=True).astype(float)
c=pd.read_csv(ROOT/'tf_system_data_volume_costs.csv',index_col=0,parse_dates=True).astype(float).reindex_like(r)
desc=pd.read_csv(ROOT/'tf_system_data_descriptive_df.csv'); groups=desc.set_index('ticker')['group_data']
logr=np.log1p(r); mret=np.expm1(logr.resample('ME').sum(min_count=1)); mcost=c.resample('ME').last().reindex(mret.index)
lag=r.shift(1); em=lag.ewm(alpha=alpha,adjust=False,min_periods=60).mean(); e2=lag.pow(2).ewm(alpha=alpha,adjust=False,min_periods=60).mean(); mvol=np.sqrt(AF*(e2-em.pow(2)).clip(lower=0)).resample('ME').last().reindex(mret.index)
trail_comp=np.expm1(np.log1p(mret).rolling(12,min_periods=12).sum()); sig=np.sign(trail_comp)
trail_sum=mret.rolling(12,min_periods=12).sum(); sig_sum=np.sign(trail_sum)
valid=mret.notna().rolling(12,min_periods=12).sum().eq(12)&mvol.notna()&(mvol>0)
# signal implementation agreement
mask=valid & sig.notna() & sig_sum.notna()
agree=(sig.where(mask)==sig_sum.where(mask)).stack().mean()
pd.DataFrame([{'signal_compound_vs_sum_agreement':agree,'n_signal_obs':int(mask.sum().sum())}]).to_csv(B/'signal_definition_robustness.csv',index=False)

# rebuild primary monthly return and individual raw strategies
n=valid.sum(axis=1).replace(0,np.nan)
raw_w=(target/mvol)*sig.where(valid)
target_port=raw_w.div(n,axis=0).fillna(0)
w=target_port.shift(1).fillna(0)
gross=(w*mret.fillna(0)).sum(axis=1)
turn=(w-w.shift(1).fillna(0)).abs(); cost=(turn*mcost.ffill().bfill()).sum(axis=1); net=gross-cost

# Standalone moving-block bootstrap vs zero
rng=np.random.default_rng(20261014)
def boot(s,nboot=10000,block=12):
    s=s.dropna().to_numpy(float); n=len(s); starts=np.arange(n-block+1); k=int(np.ceil(n/block)); vals=np.empty(nboot)
    for i in range(nboot):
        ids=rng.choice(starts,size=k,replace=True); sample=np.concatenate([s[j:j+block] for j in ids])[:n]; vals[i]=12*sample.mean()
    return {'n_months':n,'ann_mean':12*s.mean(),'ci95_low':np.quantile(vals,.025),'ci95_high':np.quantile(vals,.975),'p_mean_le_zero':np.mean(vals<=0)}
periods={'MOP_1985_2009':('1985-01-01','2009-12-31'),'POST_2009':('2010-01-01',None),'POST_2020':('2020-01-01',None)}
boots=[]
for name,(st,en) in periods.items():
    for case,ser in [('gross',gross),('net_1x',net),('net_2x',gross-2*cost),('net_3x',gross-3*cost)]:
        z=ser.loc[st:en]; d=boot(z); d.update(period=name,cost_case=case); boots.append(d)
pd.DataFrame(boots).to_csv(B/'standalone_block_bootstrap.csv',index=False)

# per-instrument 40%-vol target strategy, no 1/N divisor, with costs
inst_target=raw_w.fillna(0)
inst_w=inst_target.shift(1).fillna(0)
inst_g=inst_w*mret.fillna(0)
inst_turn=(inst_w-inst_w.shift(1).fillna(0)).abs(); inst_cost=inst_turn*mcost.ffill().bfill(); inst_net=inst_g-inst_cost
per=[]
for period,(st,en) in periods.items():
    for col in r.columns:
        z=inst_net.loc[st:en,col]
        active=inst_w.loc[st:en,col].ne(0)
        # only months after strategy is available; preserve months with zero realized pnl while active
        z=z[active]
        if len(z)<24: continue
        am=12*z.mean(); av=np.sqrt(12)*z.std(ddof=1)
        per.append({'period':period,'ticker':col,'asset_class':groups.get(col),'months':len(z),'ann_net_mean':am,'ann_vol':av,'sharpe':am/av if av>0 else np.nan})
per=pd.DataFrame(per); per.to_csv(B/'per_contract_results.csv',index=False)
per_summary=per.groupby(['period','asset_class']).agg(n_contracts=('ticker','size'),positive_mean_share=('ann_net_mean',lambda x:(x>0).mean()),median_ann_mean=('ann_net_mean','median'),median_sharpe=('sharpe','median')).reset_index()
all_summary=per.groupby('period').agg(n_contracts=('ticker','size'),positive_mean_share=('ann_net_mean',lambda x:(x>0).mean()),median_ann_mean=('ann_net_mean','median'),median_sharpe=('sharpe','median')).reset_index(); all_summary['asset_class']='ALL'
pd.concat([all_summary,per_summary],ignore_index=True).to_csv(B/'per_contract_summary.csv',index=False)

# Regime concentration diagnostics, explicitly diagnostic (not a model-selection rule)
diag=[]
for label,ser in [('gross',gross),('net_1x',net)]:
    z=ser.loc['2020':]
    for name,zz in [('2020_2026',z),('2020_2026_ex_2022',z[z.index.year!=2022]),('2023_2026',z.loc['2023':])]:
        am=12*zz.mean(); av=np.sqrt(12)*zz.std(ddof=1)
        diag.append({'return_case':label,'window':name,'months':len(zz),'ann_mean':am,'ann_vol':av,'sharpe':am/av if av>0 else np.nan,'cumulative':(1+zz).prod()-1})
pd.DataFrame(diag).to_csv(B/'regime_concentration_diagnostics.csv',index=False)

print('Signal definition agreement',agree)
print('\nBOOTSTRAP')
print(pd.DataFrame(boots).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('\nPER CONTRACT')
print(pd.concat([all_summary,per_summary],ignore_index=True).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('\nREGIME')
print(pd.DataFrame(diag).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
