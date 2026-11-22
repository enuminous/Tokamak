"""Replay primary and diagnostic computations in an expendable checkout.

Archived historical failed attempts are preserved and are not rerun as successes.
Replay overwrites named current results; use the published commit for original bytes.
"""
from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parent
def call(name,extra):
    (ROOT/'logs').mkdir(exist_ok=True)
    cmd=[sys.executable,'-u',str(ROOT/'native.py'),'--name',name]+extra
    print('RUN',name,flush=True)
    with (ROOT/'logs'/f'{name}.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
def main():
    jobs=[('coarse',['--modes-only']),('fine',['--scale','.5','--modes-only']),('eta2-isolated',['--eta','2','--modes-only']),
        ('open-corrected-dt10',[]),('open-corrected-dt05',['--dt','.05']),
        ('feedback-neg100k',['--dt','.05','--gain','-100000']),('feedback-neg20k',['--dt','.05','--gain','-20000']),
        ('feedback-pos20k',['--dt','.05','--gain','20000']),('feedback-pos100k',['--dt','.05','--gain','100000']),
        ('feedback-delay05ms',['--dt','.05','--gain','100000','--delay','.0005']),
        ('feedback-delay10ms',['--dt','.05','--gain','100000','--delay','.001']),
        ('zero-seed',['--dt','.05','--seed','0']),('negative-seed',['--dt','.05','--seed','-.0005']),
        ('bounds-included',['--include-bounds','--modes-only']),('bounds-time05',['--include-bounds','--dt','.05']),
        ('bounds-time025',['--include-bounds','--dt','.025'])]
    for name,args in jobs:call(name,args)
    for name in ['reactor.py','verify.py','plots.py']:subprocess.run([sys.executable,str(ROOT/name)],check=True)
    print('Replay complete. Read verification.json: expected validation failures remain; exit success is not a physics PASS.')
if __name__=='__main__':main()
