"""Kaggle notebook entry point: run thymus-eval on a Kaggle GPU with Ollama.

Reads run_config.json from the attached private dataset, installs Ollama, pulls the
models, runs each configured evaluation, and leaves results (and the response cache, so
a later session can resume) in /kaggle/working.
"""

import json
import os
import pathlib
import subprocess
import sys
import tarfile
import time
import urllib.request

INPUT = next(pathlib.Path("/kaggle/input").glob("*/code.tar.gz")).parent
WORK = pathlib.Path("/kaggle/working")
CODE = WORK / "thymus-memory"
CONFIG = json.loads((INPUT / "run_config.json").read_text())


def sh(cmd, **kwargs):
    print("+", cmd if isinstance(cmd, str) else " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=True, **kwargs)


def wait_for_ollama(timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen("http://localhost:11434/api/version", timeout=2)
            return
        except OSError:
            time.sleep(2)
    raise RuntimeError("ollama did not start")


with tarfile.open(INPUT / "code.tar.gz") as archive:
    archive.extractall(WORK)

previous_cache = INPUT / "cache.tar.gz"
if previous_cache.exists():
    with tarfile.open(previous_cache) as archive:
        archive.extractall(CODE)

sh("curl -fsSL https://ollama.com/install.sh | sh", shell=True)
server_log = open(WORK / "ollama-server.log", "w")
subprocess.Popen(["ollama", "serve"], stdout=server_log, stderr=subprocess.STDOUT,
                 env={**os.environ, "OLLAMA_KEEP_ALIVE": "24h"})
wait_for_ollama()
for model in CONFIG["pull"]:
    sh(["ollama", "pull", model])
sh(["nvidia-smi"])
sh([sys.executable, "-m", "pip", "install", "-q", "-e", str(CODE)])

def save_outputs():
    """Write results and cache after every run, so a session stopped at Kaggle's time
    limit still leaves everything finished so far."""
    if (CODE / "results").exists():
        with tarfile.open(WORK / "results.tar.gz", "w:gz") as archive:
            archive.add(CODE / "results", arcname="results")
    if (CODE / ".cache").exists():
        with tarfile.open(WORK / "cache.tar.gz", "w:gz") as archive:
            archive.add(CODE / ".cache", arcname=".cache")


for run in CONFIG["runs"]:
    command = ["thymus-eval", "--llm", run["llm"], "--judge", run["judge"], "--out", f"results/{run['name']}"]
    for gate in run.get("gates", []):
        command += ["--gate", gate]
    for text in run.get("only", []):
        command += ["--only", text]
    for category in run.get("category", []):
        command += ["--category", category]
    try:
        sh(command, cwd=CODE)
    except subprocess.CalledProcessError as e:
        print(f"run {run['name']} stopped with exit code {e.returncode}; results so far are kept", flush=True)
    save_outputs()

print("done", flush=True)
