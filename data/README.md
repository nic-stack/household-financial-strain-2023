# Data

**Source:** U.S. Bureau of Labor Statistics, Consumer Expenditure Survey (CE), Interview Survey public-use microdata, 2023 release. Public domain.

The raw files are not committed (about 63 MB). To rebuild:

1. Go to https://www.bls.gov/cex/pumd_data.htm, find **2023 → Interview → CSV** and download `intrvw23.zip`.
2. Copy `fmli232.csv`, `fmli233.csv`, `fmli234.csv` and `fmli241.csv` into `data/raw/`.
3. Run `./run_all.sh`.

Variable definitions come from the BLS data dictionary, `ce-pumd-interview-diary-dictionary.xlsx` on the same page.

`data/processed/interviews.csv` is the tidy table built by `src/build.py` (one row per household interview, only the columns this project uses, with the 44 replicate weights). It is committed so the analysis can be rerun without the raw files: skip `src/build.py` in `run_all.sh`.
