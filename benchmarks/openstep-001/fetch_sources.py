"""Download unmodified OpenSTEP source files, verifying immutable content hashes."""
from pathlib import Path
import hashlib
import urllib.request

ROOT=Path(__file__).resolve().parent/'source'
PIN='6f66ae09c60b361d600b178416ef3f22b8d0aa6a'
FILES={
    'coilset.mat': ('eb-cc/freeboundary/_src/coilset.mat','7587fc76b5f7e14d7ac966d9cfd2504cbc212bea80aa5931cebad984c4e4066f'),
    'equilibrium.mat': ('eb-cc/freeboundary/_src/equilibrium.mat','c06780bd75cde1dce793d6b4ec778869c8a6ef0e79ccd976e87522cbcef756e9'),
    'STEP_SPP_001_EBCC_freeboundary.nc': ('eb-cc/freeboundary/STEP_SPP_001_EBCC_freeboundary.nc','b2391ae94b6a9c696d8bbb27b91999f6c93c8664afc06471cb889024146751a4'),
}

def main():
    ROOT.mkdir(exist_ok=True)
    for name,(remote,digest) in FILES.items():
        target=ROOT/name
        if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==digest:
            print(name,'verified cached copy');continue
        url=f'https://raw.githubusercontent.com/ukaea/OpenSTEP/{PIN}/{remote}'
        with urllib.request.urlopen(url,timeout=60) as response:
            data=response.read()
        actual=hashlib.sha256(data).hexdigest()
        if actual!=digest: raise ValueError(f'{name}: SHA256 mismatch: {actual}')
        target.write_bytes(data)
        print(name,'downloaded and verified')

if __name__=='__main__': main()
