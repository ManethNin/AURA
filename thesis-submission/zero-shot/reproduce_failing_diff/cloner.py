import json
import os
from pathlib import Path
import subprocess
import pandas as pd


df = pd.read_parquet("../upgrades/research_data.parquet")
for index, row in df.iterrows():
    commit_hash = row["breakingCommit"]
    repo_slug = row["projectOrganisation"] + "/" + row["project"]

    os.makedirs("repos", exist_ok=True)

    repo_dir = os.path.join("repos", commit_hash)
    # os.makedirs(repo_dir, exist_ok=True)

    revapi_path = Path("../bump/RQData/japicmp-revapi-analysis-results.json")
    with revapi_path.open("r", encoding="utf-8") as f:
        revapi_dict = json.load(f)

    sampled_keys = [
        revapi_item
        for revapi_item in revapi_dict.keys()
        if revapi_dict[revapi_item]["japicmpResult"] != {}
        or revapi_dict[revapi_item]["revapiResult"] != {}
        or revapi_dict[revapi_item]["elementLines"] != {}
    ]

    if commit_hash not in sampled_keys:
        continue

    if os.path.exists(repo_dir):
        continue

    _ = subprocess.run(
        ["git", "clone", f"https://github.com/{repo_slug}.git", repo_dir],
        capture_output=True,
        check=True,
    )
    _ = subprocess.run(
        ["git", "fetch", "--depth", "2", "origin", commit_hash],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )
    _ = subprocess.run(
        ["git", "checkout", commit_hash],
        cwd=repo_dir,
        capture_output=True,
        check=True,
    )

    reproduction_log_path = Path(
        "../bump/reproductionLogs/successfulReproductionLogs"
    ) / (commit_hash + ".log")
    if not reproduction_log_path.exists():
        continue
    with open(reproduction_log_path, "r") as f:
        reproduction_log = f.read()
        with open(Path(repo_dir) / "reproduction.log", "w") as f:
            f.write(reproduction_log)
