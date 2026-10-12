"""Kaggle CPU notebook: compile the paper (the dataset holds the paper/ folder as paper.tgz.bin)."""
import pathlib
import shutil
import subprocess
import tarfile

src = next(pathlib.Path("/kaggle/input").rglob("paper.tgz.bin"))
work = pathlib.Path("/kaggle/working/build")
work.mkdir(parents=True, exist_ok=True)
with tarfile.open(src, "r:gz") as archive:
    archive.extractall(work, filter="data")
subprocess.run("apt-get -qq update && DEBIAN_FRONTEND=noninteractive apt-get -qq install -y "
               "texlive-latex-recommended texlive-latex-extra texlive-pictures texlive-fonts-recommended "
               "texlive-science latexmk poppler-utils > /dev/null", shell=True, check=True)
paper = work / "paper"
result = subprocess.run(["latexmk", "-pdf", "-interaction=nonstopmode", "-f", "main.tex"],
                        cwd=paper, capture_output=True, text=True)
print(result.stdout[-6000:], result.stderr[-3000:])
for name in ("main.pdf", "main.log"):
    if (paper / name).exists():
        shutil.copy(paper / name, f"/kaggle/working/{name}")
if (paper / "main.pdf").exists():  # page previews for checking the layout
    subprocess.run(["pdftoppm", "-r", "80", "-png", "main.pdf", "/kaggle/working/page"], cwd=paper, check=False)
