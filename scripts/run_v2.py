import sys, time
sys.path.insert(0, "src")
from multipath_eval.config import load_config
from multipath_eval.runner2 import run_v2
import pandas as pd
cfg = load_config("configs/default.toml")
n = int(sys.argv[1]) if len(sys.argv) > 1 else len(cfg.topologies)
import dataclasses
cfg = dataclasses.replace(cfg, topologies=cfg.topologies[:n])
t = time.time()
df, nets = run_v2(cfg)
out = "results/v2"
import os; os.makedirs(out, exist_ok=True)
df.to_parquet(f"{out}/demand_metrics_v2.parquet"); nets.to_csv(f"{out}/networks.csv", index=False)
print(len(df), "rows", round(time.time() - t), "s")
