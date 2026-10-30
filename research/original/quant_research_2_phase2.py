from pathlib import Path
import pandas as pd
import numpy as np
import json, math, hashlib, time

ROOT=Path('/mnt/data/quant_research_2_wheel/trendfollowing/resources/futures')
OUT=Path('/mnt/data/quant_research_2_phase2')
OUT.mkdir(exist_ok=True)

AF_DAILY=261.0
DELTA=60.0/61.0
ALPHA=1.0-DELTA
TARGET_VOL=0.40
MIN_VOL_DAYS=60
MIN_HISTORY_MONTHS=12
RNG_SEED=20261014

# ---------------- load ----------------
def load_panel(name):
    p=ROOT/name
    df=pd.read_csv(p,index_col=0,parse_dates=True)
    df.index=pd.to_datetime(df.index)
    return df.sort_index()

r=load_panel('tf_system_data_usd_returns.csv').astype(float)
c=load_panel('tf_system_data_volume_costs.csv').astype(float).reindex_like(r)
desc=pd.read_csv(ROOT/'tf_system_data_descriptive_df.csv')
group_map=desc.set_index('ticker')['group_data']

# integrity / QA
assert list(r.columns)==list(c.columns)
assert len(r.columns)==84

# Monthly simple return from daily simple returns. min_count=1 preserves NaN for all-missing months.
logr=np.log1p(r)
msum=logr.resample('ME').sum(min_count=1)
mret=np.expm1(msum)
mcost=c.resample('ME').last().reindex(mret.index)

# Exact MOP-style EWMA mean/variance using only lagged daily returns.
lag=r.shift(1)
ewm_mean=lag.ewm(alpha=ALPHA,adjust=False,min_periods=MIN_VOL_DAYS).mean()
ewm_second=(lag.pow(2)).ewm(alpha=ALPHA,adjust=False,min_periods=MIN_VOL_DAYS).mean()
var=(ewm_second-ewm_mean.pow(2)).clip(lower=0)
annvol=np.sqrt(AF_DAILY*var)
mvol=annvol.resample('ME').last().reindex(mret.index)

# trailing 12m compounded excess return including formation month t
trail_log=np.log1p(mret).rolling(12,min_periods=12).sum()
trail12=np.expm1(trail_log)
tsmom_sig=np.sign(trail12)

# Require exactly 12 nonmissing monthly observations and valid ex-ante vol.
valid12=mret.notna().rolling(12,min_periods=12).sum().eq(12)
base_available=valid12 & mvol.notna() & (mvol>0) & tsmom_sig.notna()

# TSH: sign of expanding historical sample mean monthly excess return; same tradeable set for apples-to-apples.
hist_mean=mret.expanding(min_periods=12).mean()
tsh_sig=np.sign(hist_mean)

# weight builder: target weights decided at month-end t, applied during t+1.
def target_weights(signal, scaled=True):
    available=base_available & signal.notna()
    n=available.sum(axis=1).replace(0,np.nan)
    if scaled:
        raw=(TARGET_VOL/mvol)*signal
    else:
        raw=signal.astype(float)
    w=raw.where(available,0.0).div(n,axis=0).fillna(0.0)
    return w

TARGETS={
    'TSMOM_scaled': target_weights(tsmom_sig, True),
    'AlwaysLong_scaled': target_weights(pd.DataFrame(1.0,index=mret.index,columns=mret.columns), True),
    'HistoricalMean_scaled': target_weights(tsh_sig, True),
    'TSMOM_unscaled': target_weights(tsmom_sig, False),
}

# apply target formed t to month t+1; rebalance at start of each return month.
def run_strategy(target):
    w=target.shift(1).fillna(0.0)
    # Any nonzero weight paired with missing return is a data-quality issue; record it.
    missing_exposure=((w!=0)&mret.isna())
    inst_gross=w*mret.fillna(0.0)
    gross=inst_gross.sum(axis=1)
    turnover=(w-w.shift(1).fillna(0.0)).abs()
    costs=turnover*mcost.fillna(method='ffill').fillna(method='bfill')
    cost=costs.sum(axis=1)
    out=pd.DataFrame({
        'gross':gross,
        'cost_1x':cost,
        'net_1x':gross-cost,
        'net_2x':gross-2*cost,
        'net_3x':gross-3*cost,
        'turnover':turnover.sum(axis=1),
        'gross_leverage':w.abs().sum(axis=1),
        'active_instruments':(w!=0).sum(axis=1),
        'missing_exposures':missing_exposure.sum(axis=1),
    })
    return out, w, inst_gross, costs

RESULTS={}
DETAIL={}
for name,w in TARGETS.items():
    RESULTS[name], *DETAIL[name]=run_strategy(w)

# Start when MOP broad sample convention becomes relevant; full dataset shown only as robustness.
PERIODS={
    'FULL_1960_2026':('1960-01-01',None),
    'MOP_1985_2009':('1985-01-01','2009-12-31'),
    'POST_2009':('2010-01-01',None),
    'POST_2020':('2020-01-01',None),
}

# metrics

def metrics(s, turnover=None, cost=None, leverage=None, active=None):
    s=s.dropna()
    if len(s)<2: return {}
    ann_mean=12*s.mean()
    ann_vol=np.sqrt(12)*s.std(ddof=1)
    wealth=(1+s).cumprod()
    dd=wealth/wealth.cummax()-1
    # CAGR only if wealth stays positive and final positive.
    cagr=np.nan
    if (1+s).gt(0).all() and wealth.iloc[-1]>0:
        cagr=wealth.iloc[-1]**(12/len(s))-1
    d={
        'months':len(s),
        'ann_arith_mean':ann_mean,
        'ann_vol':ann_vol,
        'sharpe':ann_mean/ann_vol if ann_vol>0 else np.nan,
        'cagr':cagr,
        'max_drawdown':dd.min(),
        'skew':s.skew(),
        'positive_month_share':(s>0).mean(),
        'total_growth':wealth.iloc[-1]-1,
    }
    if turnover is not None: d['ann_turnover']=12*turnover.reindex(s.index).mean()
    if cost is not None: d['ann_cost_drag']=12*cost.reindex(s.index).mean()
    if leverage is not None: d['avg_gross_leverage']=leverage.reindex(s.index).mean()
    if active is not None: d['avg_active_instruments']=active.reindex(s.index).mean()
    return d

rows=[]
for strat,res in RESULTS.items():
    for period,(start,end) in PERIODS.items():
        z=res.loc[start:end]
        for retcol,cost_mult in [('gross',0),('net_1x',1),('net_2x',2),('net_3x',3)]:
            row={'strategy':strat,'period':period,'cost_case':retcol}
            row.update(metrics(z[retcol],z.turnover,z.cost_1x*cost_mult,z.gross_leverage,z.active_instruments))
            row['max_missing_exposures_in_month']=int(z.missing_exposures.max()) if len(z) else 0
            row['months_with_missing_exposure']=int((z.missing_exposures>0).sum()) if len(z) else 0
            rows.append(row)
summary=pd.DataFrame(rows)
summary.to_csv(OUT/'strategy_summary.csv',index=False)

# calendar year returns base-cost net and gross, primary strategy + controls
cal=[]
for strat,res in RESULTS.items():
    for col in ['gross','net_1x','net_2x','net_3x']:
        for y,g in res.loc['1985':,col].groupby(res.loc['1985':].index.year):
            if len(g): cal.append({'strategy':strat,'cost_case':col,'year':int(y),'return':(1+g).prod()-1,'months':len(g)})
pd.DataFrame(cal).to_csv(OUT/'calendar_year_returns.csv',index=False)

# Paired moving-block bootstrap of mean difference, using 12-month blocks.
def moving_block_bootstrap_mean_diff(a,b,n_boot=5000,block=12,seed=RNG_SEED):
    x=pd.concat([a,b],axis=1,join='inner').dropna()
    d=(x.iloc[:,0]-x.iloc[:,1]).to_numpy(float)
    n=len(d)
    if n<block*2: return (np.nan,np.nan,np.nan,np.nan,n)
    rng=np.random.default_rng(seed)
    starts=np.arange(0,n-block+1)
    vals=np.empty(n_boot)
    blocks_needed=int(np.ceil(n/block))
    for k in range(n_boot):
        chosen=rng.choice(starts,size=blocks_needed,replace=True)
        sample=np.concatenate([d[s:s+block] for s in chosen])[:n]
        vals[k]=12*sample.mean()
    obs=12*d.mean()
    return obs,np.quantile(vals,.025),np.quantile(vals,.975),np.mean(vals<=0),n
comparisons=[]
for period,(start,end) in {'MOP_1985_2009':PERIODS['MOP_1985_2009'],'POST_2009':PERIODS['POST_2009'],'POST_2020':PERIODS['POST_2020']}.items():
    for costcase in ['gross','net_1x','net_2x','net_3x']:
        a=RESULTS['TSMOM_scaled'].loc[start:end,costcase]
        for ctl in ['AlwaysLong_scaled','HistoricalMean_scaled']:
            b=RESULTS[ctl].loc[start:end,costcase]
            obs,lo,hi,p,n=moving_block_bootstrap_mean_diff(a,b,seed=RNG_SEED+len(comparisons))
            comparisons.append({'period':period,'cost_case':costcase,'comparison':f'TSMOM_scaled - {ctl}','months':n,'ann_mean_diff':obs,'ci95_low':lo,'ci95_high':hi,'p_diff_le_zero':p})
comparisons=pd.DataFrame(comparisons)
comparisons.to_csv(OUT/'paired_control_bootstrap.csv',index=False)

# Asset-class attribution: contribution to overall TSMOM_scaled portfolio, using base costs.
res=RESULTS['TSMOM_scaled']; w,inst_gross,inst_cost=DETAIL['TSMOM_scaled']
attr=[]
for period,(start,end) in {'MOP_1985_2009':PERIODS['MOP_1985_2009'],'POST_2009':PERIODS['POST_2009'],'POST_2020':PERIODS['POST_2020']}.items():
    for group in ['Equities','Bonds','STIR','FX','Energy','Metals','Agriculture']:
        cols=[x for x in r.columns if group_map.get(x)==group]
        g=inst_gross.loc[start:end,cols].sum(axis=1)
        cc=inst_cost.loc[start:end,cols].sum(axis=1)
        attr.append({'period':period,'asset_class':group,'ann_gross_contribution':12*g.mean(),'ann_cost_contribution':12*cc.mean(),'ann_net_contribution':12*(g-cc).mean(),'avg_abs_weight':w.loc[start:end,cols].abs().sum(axis=1).mean(),'n_contracts_total':len(cols)})
pd.DataFrame(attr).to_csv(OUT/'asset_class_attribution.csv',index=False)

# Signal leg diagnostics: long vs short contributions gross/net base.
legs=[]
eff_w=DETAIL['TSMOM_scaled'][0]
inst_g=DETAIL['TSMOM_scaled'][1]
inst_c=DETAIL['TSMOM_scaled'][2]
for period,(start,end) in {'MOP_1985_2009':PERIODS['MOP_1985_2009'],'POST_2009':PERIODS['POST_2009'],'POST_2020':PERIODS['POST_2020']}.items():
    q_w=eff_w.loc[start:end]; q_g=inst_g.loc[start:end]; q_c=inst_c.loc[start:end]
    for leg,mask in [('LONG',q_w>0),('SHORT',q_w<0)]:
        gross=q_g.where(mask,0).sum(axis=1)
        # cost cannot cleanly allocate flips; allocate current month's transaction cost to side of resulting position; exits to zero remain unallocated.
        cost=q_c.where(mask,0).sum(axis=1)
        legs.append({'period':period,'leg':leg,'ann_gross_contribution':12*gross.mean(),'ann_allocated_cost':12*cost.mean(),'ann_net_approx':12*(gross-cost).mean(),'avg_active':mask.sum(axis=1).mean()})
pd.DataFrame(legs).to_csv(OUT/'long_short_contributions.csv',index=False)

# Placebo: independent random +/- signs each instrument-month using same absolute scaled risk weights.
# Primary p-value is gross, since independent random signs mechanically increase turnover; net is shown as a stress reference.
abs_target=TARGETS['TSMOM_scaled'].abs().to_numpy(float)
M=mret.fillna(0.0).to_numpy(float)
COST=mcost.ffill().bfill().to_numpy(float)
idx=mret.index
# effective weight months are shifted one from target
rng=np.random.default_rng(RNG_SEED)
N_SIM=3000
batch=100
placebo_records=[]
period_masks={k:((idx>=pd.Timestamp(s)) & ((idx<=pd.Timestamp(e)) if e else True)) for k,(s,e) in {'MOP_1985_2009':PERIODS['MOP_1985_2009'],'POST_2009':PERIODS['POST_2009'],'POST_2020':PERIODS['POST_2020']}.items()}
placebo_by_period={k:{'gross_mean':[],'net_mean':[],'gross_sharpe':[],'net_sharpe':[]} for k in period_masks}
T,N=abs_target.shape
for st in range(0,N_SIM,batch):
    B=min(batch,N_SIM-st)
    signs=rng.choice(np.array([-1.0,1.0]),size=(B,T,N))
    targ=signs*abs_target[None,:,:]
    eff=np.zeros_like(targ)
    eff[:,1:,:]=targ[:,:-1,:]
    gross=np.sum(eff*M[None,:,:],axis=2)
    prev=np.zeros_like(eff)
    prev[:,1:,:]=eff[:,:-1,:]
    cost=np.sum(np.abs(eff-prev)*COST[None,:,:],axis=2)
    net=gross-cost
    for period,mask in period_masks.items():
        gg=gross[:,mask]; nn=net[:,mask]
        am_g=12*np.mean(gg,axis=1); av_g=np.sqrt(12)*np.std(gg,axis=1,ddof=1)
        am_n=12*np.mean(nn,axis=1); av_n=np.sqrt(12)*np.std(nn,axis=1,ddof=1)
        placebo_by_period[period]['gross_mean'].extend(am_g.tolist())
        placebo_by_period[period]['net_mean'].extend(am_n.tolist())
        placebo_by_period[period]['gross_sharpe'].extend((am_g/av_g).tolist())
        placebo_by_period[period]['net_sharpe'].extend((am_n/av_n).tolist())

placebo_summary=[]
for period,d in placebo_by_period.items():
    start,end={'MOP_1985_2009':PERIODS['MOP_1985_2009'],'POST_2009':PERIODS['POST_2009'],'POST_2020':PERIODS['POST_2020']}[period]
    actual_g=metrics(RESULTS['TSMOM_scaled'].loc[start:end,'gross'])
    actual_n=metrics(RESULTS['TSMOM_scaled'].loc[start:end,'net_1x'])
    ag=actual_g['ann_arith_mean']; an=actual_n['ann_arith_mean']
    g=np.array(d['gross_mean']); n=np.array(d['net_mean'])
    placebo_summary.append({'period':period,'n_sim':N_SIM,'actual_gross_ann_mean':ag,'random_gross_mean_median':np.median(g),'random_gross_mean_p95':np.quantile(g,.95),'p_random_gross_ge_actual':np.mean(g>=ag),'actual_net_ann_mean':an,'random_net_mean_median':np.median(n),'random_net_mean_p95':np.quantile(n,.95),'p_random_net_ge_actual':np.mean(n>=an)})
pd.DataFrame(placebo_summary).to_csv(OUT/'random_sign_placebo.csv',index=False)

# Data QA and universe availability
qa={
    'daily_start':str(r.index.min().date()),'daily_end':str(r.index.max().date()),'daily_rows':len(r),'contracts':len(r.columns),
    'wheel_sha256':'76beb7a35b22cb2784df98bb20a6d9ca5803c4df761398b877db765bd6562c9a',
    'cost_values_unique':sorted(np.unique(c.values[~np.isnan(c.values)]).tolist()),
    'max_monthly_missing_exposures_tsmom':int(RESULTS['TSMOM_scaled'].missing_exposures.max()),
    'months_with_missing_exposure_tsmom':int((RESULTS['TSMOM_scaled'].missing_exposures>0).sum()),
}
counts=desc.groupby('group_data').size().to_dict(); qa['contracts_by_class']=counts
with open(OUT/'data_quality.json','w') as f: json.dump(qa,f,indent=2)

# Save monthly primary returns/diagnostics and weights only from 1984 onward to limit size.
primary=RESULTS['TSMOM_scaled'].loc['1984':].copy()
primary.to_csv(OUT/'tsmom_monthly_returns.csv')
TARGETS['TSMOM_scaled'].loc['1984':].to_csv(OUT/'tsmom_target_weights.csv')

# Print compact result
sel=summary[(summary.period.isin(['MOP_1985_2009','POST_2009','POST_2020'])) & (summary.cost_case.isin(['gross','net_1x','net_2x','net_3x']))]
print('DATA',qa)
print('\nPRIMARY TSMOM SCALED')
print(sel[sel.strategy=='TSMOM_scaled'][['period','cost_case','ann_arith_mean','ann_vol','sharpe','cagr','max_drawdown','ann_cost_drag','ann_turnover','avg_gross_leverage','avg_active_instruments']].to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('\nCONTROLS BASE COST')
print(sel[sel.cost_case=='net_1x'][['strategy','period','ann_arith_mean','ann_vol','sharpe','cagr','max_drawdown']].to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('\nPAIRED CONTROL BOOTSTRAP BASE COST')
print(comparisons[comparisons.cost_case=='net_1x'].to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('\nPLACEBO')
print(pd.DataFrame(placebo_summary).to_string(index=False,float_format=lambda x:f'{x:.4f}'))
print('\nOUT',OUT)
