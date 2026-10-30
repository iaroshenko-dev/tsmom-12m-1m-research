"""Compare archived CSVs to regenerated CSVs with numeric tolerances; no writes to archived files."""
from pathlib import Path
import pandas as pd,numpy as np,json,sys
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'results';B=ROOT/'generated/reproduction'
files=sorted(x for x in A.glob('*.csv'))
failed=[]
for f in files:
    q=B/f.name
    if not q.exists():failed.append((f.name,'missing'));continue
    a=pd.read_csv(f);b=pd.read_csv(q)
    if a.shape != b.shape or list(a.columns)!=list(b.columns):failed.append((f.name,'shape/columns'));continue
    for col in a.columns:
        aa=a[col];bb=b[col]
        if pd.api.types.is_numeric_dtype(aa) and pd.api.types.is_numeric_dtype(bb):
            same=np.allclose(aa,bb,atol=1e-9,rtol=1e-9,equal_nan=True)
        else: same=aa.fillna('<MISSING>').equals(bb.fillna('<MISSING>'))
        if not same:failed.append((f.name,'column '+col));break
    if not any(err[0]==f.name for err in failed):print('PASS',f.name,len(a),'rows')
if (A/'data_quality.json').exists():
    if not (B/'data_quality.json').exists() or json.loads((A/'data_quality.json').read_text())!=json.loads((B/'data_quality.json').read_text()):
        failed.append(('data_quality.json','different'))
    else:print('PASS data_quality.json')
if failed:
    for f,e in failed: print('FAIL',f,e,file=sys.stderr)
    raise SystemExit(1)
print('All',len(files),'archived CSV files and JSON are reproducible.')
