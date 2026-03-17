#!/usr/bin/env bash
set -euo pipefail

python tax1040_simple.py \
  --resident-return \
  --tax-year 2025 \
  --w2 "/mnt/data/2025 W2.pdf" \
  --brokerage-1099 "/mnt/data/2025-Ananya-s-Individual-Fidelity-Go-2462-Consolidated-Form-1099.pdf" \
  --brokerage-1099 "/mnt/data/2025-Individual-1084-Consolidated-Form-1099.pdf" \
  --output-json example_tax_summary.json \
  --output-report example_tax_report.md
