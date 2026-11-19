# Corpus fixtures — provenance

This directory mixes retained field evidence with explicitly labeled synthetic parser fixtures. Do not describe the synthetic FULLLOGs as hardware output.

## Retained field evidence

The summary CSVs and cdw-validation bundle text were copied read-only from the review corpus (`~/FenrisWorkspace/dgx-vitals-review/corpus-sleipnir/dgx-vitals-test/`). The site hostname prefix `nesd-oma01c-` was replaced by `fx-` in contents and paths. Summary CSVs keep only the rows named, with the header unchanged. Bundle files came from `moonlite-validation-bundle.tar.gz`; dump archives and `var-log-nvsm` were not retained.

`sha256` below is of the source before hostname substitution; `subs` is the substitution count.

| fixture | source | sha256 (source) | subs |
|---|---|---|---|
| `full-w08-hollow-stress/summary.csv` | `validation-output-full/summary.csv` (w08 row) | `b3b73d94374e463935108a92c8325c9c5446242946559265c2df9438d0eb23a4` | 1 |
| `wave1-w08-already-running/summary.csv` | `validation-output-wave1/summary.csv` (w08 row) | `785230d59f12b1d02f09f244394cf10ddef1d184c8c4f4a96acf1c5de76d7318` | 1 |
| `wave1-w09-full-pass/summary.csv` | `validation-output-wave1/summary.csv` (w09 row) | `785230d59f12b1d02f09f244394cf10ddef1d184c8c4f4a96acf1c5de76d7318` | 1 |
| `wave1-x10-ki2/summary.csv` | `validation-output-wave1/summary.csv` (x10 row) | `785230d59f12b1d02f09f244394cf10ddef1d184c8c4f4a96acf1c5de76d7318` | 1 |
| `xwave2-summary-rows/summary.csv` | `validation-output-x-wave2/summary.csv` (hv-02 and hv-04 rows) | `a9409641f0e949d7b307ac299886e42f5e5e986089d4b51c52c86ba2baf34e6d` | 2 |
| `bundle-w09/.../summary.txt` | `moonlite-validation-bundle.tar.gz` → w09 bundle → `summary.txt` | `12959706835715526f73c353cc962a9bb938a9305046f6de610038366da3682f` | 1 |
| `bundle-w09/.../03-nvsm-versions.log` | same bundle | `b9764b03ce16b2d81b8020618b77c222cc4a5db555feb4c5def6c8dcef080ede` | 0 |
| `bundle-w09/.../04-nvsm-health.log` | same bundle | `a62a8620adc336228f1a90a6875800835479f0bc7470ca4b31d38adb876e5fec` | 0 |
| `bundle-w09/.../system-info.txt` | same bundle | `65cc921d50d5ade6c5962273a5fe95b040eaf3ff241ebb2a6b8b6010781910b2` | 2 |

The original FULLLOG sources were not present in the repository or its canonical upstream. Their previously recorded hashes remain historical provenance, not hashes of the synthetic replacements: w08-full `23ae50a1…`, w08-wave1 `acc4f067…`, w09 `f4a0dc14…`, x10 `ac33be9a…`, x01-hv-02 `b3fe37bd…`, x01-hv-04 `6c34e00c…`, and y10 `8f39c1fe…`.

## Synthetic FULLLOG replacements

Run `python3 -m tests.synthetic_corpus` from `dgx-vitals/` to regenerate every missing FULLLOG deterministically. Each generated file carries a `Fixture: deterministic synthetic parser evidence; not hardware output` header. The generator reuses the retained anonymized w09 health log and creates the other step outputs needed to exercise the documented parser cases.

| fixture case | synthetic behavior covered |
|---|---|
| `full-w08-hollow-stress` | v1.4 log; stress confirmation-prompt echo; NCCL non-launch; dump timeout |
| `wave1-w08-already-running` | v1.5 log; DIMM and PSU unhealthy checks; already-running stress refusal |
| `wave1-w09-full-pass` | v1.5 seven-step log; DIMM-only KI-1; legacy NCCL non-launch; genuine stress/harvest evidence |
| `wave1-x10-ki2` | v1.5 legacy NCCL non-launch signature and failed dump |
| `xwave2-no-summary` | v1.9 rebuild without summary; stress failure on hv-02; DIMM-only warning on hv-04 |
| `y10-truncated` | v1.9 unfinished six-step log with five results and failed GPU stress component |

Tests copy fixtures into a temporary directory and stamp `summary.csv` newest, matching runner output ordering. The `.gitignore` runtime FULLLOG rule explicitly unignores these fixture paths so they cannot silently disappear again.
