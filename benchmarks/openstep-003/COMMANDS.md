# Exact replay order

Run from the repository root with the pinned dependencies installed. Use one BLAS thread. These commands replay complete solves; failure exit code 2 is an expected recorded outcome for failed attempts. Intermediate homotopy files are numerical warm starts, not design candidates.

```sh
export OPENBLAS_NUM_THREADS=1
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-001/results/baseline-129-symmetric.npz --tag recovery-129-fd7 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-001/results/baseline-129-symmetric.npz --tag recovery-129-no-linesearch --rdiff 1e-07 --line-search none --maxits 60 --alpha 1 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift 0.075 --warm benchmarks/openstep-002/results/p9-inward-129-controlled.npz --tag recovery-geometry-075mm --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-001/results/baseline-129-symmetric.npz --tag recovery-homotopy-00 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.0
python benchmarks/openstep-003/solve.py --n 257 --shift 0 --warm benchmarks/openstep-002/results/baseline-257-controlled.npz --tag shift-+000mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 257 --shift 0.01 --warm benchmarks/openstep-003/results/shift-+000mm-257.npz --tag inward-010mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-00.npz --tag recovery-homotopy-01 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.1
python benchmarks/openstep-003/solve.py --n 257 --shift -0.01 --warm benchmarks/openstep-003/results/shift-+000mm-257.npz --tag shift--010mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 257 --shift 0.025 --warm benchmarks/openstep-003/results/inward-010mm-257.npz --tag inward-025mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 257 --shift 0.05 --warm benchmarks/openstep-003/results/inward-010mm-257.npz --tag inward-050mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-01.npz --tag recovery-homotopy-02 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.2
python benchmarks/openstep-003/solve.py --n 257 --shift -0.025 --warm benchmarks/openstep-003/results/shift--010mm-257.npz --tag shift--025mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 257 --shift -0.05 --warm benchmarks/openstep-003/results/shift--010mm-257.npz --tag shift--050mm-257 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-02.npz --tag recovery-homotopy-03 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.3
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-03.npz --tag recovery-homotopy-04 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.4
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-04.npz --tag recovery-homotopy-05 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.5
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-05.npz --tag recovery-homotopy-06 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.6
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-06.npz --tag recovery-homotopy-07 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.7
python benchmarks/openstep-003/solve.py --n 129 --shift -0.01 --warm benchmarks/openstep-003/results/recovery-homotopy-06.npz --tag shift--010mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-07.npz --tag recovery-homotopy-08 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.8
python benchmarks/openstep-003/solve.py --n 129 --shift -0.025 --warm benchmarks/openstep-003/results/shift--010mm-129.npz --tag shift--025mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift -0.05 --warm benchmarks/openstep-003/results/shift--010mm-129.npz --tag shift--050mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-08.npz --tag recovery-homotopy-09 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 0.9
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-09.npz --tag recovery-homotopy-10 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0.01 --warm benchmarks/openstep-003/results/recovery-homotopy-10.npz --tag inward-010mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0 --warm benchmarks/openstep-003/results/recovery-homotopy-10.npz --tag shift-+000mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0.025 --warm benchmarks/openstep-003/results/inward-010mm-129.npz --tag inward-025mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift 0.05 --warm benchmarks/openstep-003/results/inward-010mm-129.npz --tag inward-050mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
python benchmarks/openstep-003/solve.py --n 129 --shift 0.01 --warm benchmarks/openstep-003/results/shift-+000mm-129.npz --tag shift-+010mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0
python benchmarks/openstep-003/solve.py --n 129 --shift 0.025 --warm benchmarks/openstep-003/results/shift-+010mm-129.npz --tag shift-+025mm-129 --rdiff 1e-07 --line-search armijo --maxits 60 --alpha 1.0 || test "$?" -eq 2
```

Interrupted exploratory trials are described in DEVELOPMENT.md. Their logs document the interruption; they have no accepted final field.
