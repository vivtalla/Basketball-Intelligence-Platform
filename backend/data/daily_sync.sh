#!/bin/bash
cd "$(dirname "$0")/.."
python data/warehouse_jobs.py --season 2024-25 --max-jobs 100 >> /var/log/bip_sync.log 2>&1
