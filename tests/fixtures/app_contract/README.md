# Vendored app-contract schemas (for tests only)

Copies of `app/contract/artifacts/{rules,thresholds,model}.schema.json` from the `app-track`
branch at commit `f7b828b`, so `tests/test_export.py` can check that
`research/export_artifacts.py` writes files the app will accept. The app's copies are the
source of truth: when they change, copy them here again. Once `app-track` is merged, the
exporter validates against `app/contract/artifacts/` directly.
