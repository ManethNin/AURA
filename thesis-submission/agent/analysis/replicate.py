import os
import subprocess
from glob import glob
from tqdm import tqdm
from pathlib import Path

# Set the base directory
base_dir = Path(__file__).resolve().parent.parent / "dataset"

# Find all replicate.sh files using glob
replicate_files = glob(str(base_dir / '**' / 'out' / 'reproduction' / '**' / 'replicate.sh'), recursive=True)

# Total number of replicate.sh files
total_files = len(replicate_files)

# Execute each replicate.sh file with progress tracking
for file in tqdm(replicate_files, desc="Executing replicate.sh scripts", unit="file", total=total_files):
    cwd = Path(file).parent
    log_file = cwd / 'replicate.log'
    try:
        with open(log_file, 'a') as f:
            _ = subprocess.run(["bash", file], cwd=cwd, stdout=f, stderr=subprocess.STDOUT, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing {file}: {e}")
    except Exception as e:
        print(f"Unexpected error with {file}: {e}")