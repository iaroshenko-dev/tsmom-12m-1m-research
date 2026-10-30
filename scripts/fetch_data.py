"""Download exact verified PyPI wheel and extract 3 required CSV resources.
No third-party Python dependencies.
"""
from pathlib import Path
import hashlib, io, json, urllib.request, zipfile
ROOT = Path(__file__).resolve().parents[1]
SHA = '76beb7a35b22cb2784df98bb20a6d9ca5803c4df761398b877db765bd6562c9a'
NAME = 'trendfollowing-1.3.1-py3-none-any.whl'
NAMES = [
    'tf_system_data_usd_returns.csv',
    'tf_system_data_volume_costs.csv',
    'tf_system_data_descriptive_df.csv',
]
def main():
    info = json.load(urllib.request.urlopen('https://pypi.org/pypi/trendfollowing/1.3.1/json', timeout=30))
    files = [f for f in info['urls'] if f['filename'] == NAME]
    if len(files) != 1: raise RuntimeError('Expected exact wheel not found')
    data = urllib.request.urlopen(files[0]['url'], timeout=120).read()
    actual = hashlib.sha256(data).hexdigest()
    if actual != SHA: raise RuntimeError(f'Wheel checksum mismatch: {actual}')
    base = ROOT / 'data/vendor/trendfollowing/resources/futures'
    base.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for name in NAMES:
            member = f'trendfollowing/resources/futures/{name}'
            (base / name).write_bytes(z.read(member))
    print(f'Verified {NAME} SHA256={actual}')
    print(f'Extracted {len(NAMES)} source files to {base}')
if __name__ == '__main__': main()
