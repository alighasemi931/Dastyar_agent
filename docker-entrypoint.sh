#!/bin/bash
set -e

# 1. دیتابیس را آماده کن
python scripts/data_collector.py

# 2. ساخت وکتور DB
python scripts/build_vector_db.py

# 3. اجرای سرور
python api_server.py
