import os
import subprocess

cad_dir = os.path.join("hardware", "cad")
for f in os.listdir(cad_dir):
    if f.endswith(".py"):
        print(f"Executing {f}...")
        subprocess.run(["python", os.path.join(cad_dir, f)], check=True)
