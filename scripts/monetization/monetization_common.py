#!/usr/bin/env python3
from __future__ import annotations
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/"scripts"/"ops"))
from same_day_common import RUNTIME,SUPABASE_READY,now,read_json,write_json,write_report  # noqa:E402,F401
def offers():return read_json(ROOT/"configs/offer_registry.json",{}).get("offers",[])
