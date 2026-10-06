"""Launcher used by run_all.py: registers DLL directories (Windows, Python 3.8+
ignores PATH for extension-module dependencies) and then runs a pynari sample
as __main__ with the remaining command-line arguments.

Usage: python _launch.py <sample.py> [sample args...]
Env:   PYNARI_DLL_DIRS   os.pathsep-separated list of directories to register
       PYNARI_MODULE_DIR directory containing pynari*.pyd (prepended to sys.path)
"""
import os, sys, runpy

for d in os.environ.get("PYNARI_DLL_DIRS", "").split(os.pathsep):
    if d and os.path.isdir(d):
        os.add_dll_directory(d)
mod_dir = os.environ.get("PYNARI_MODULE_DIR")
if mod_dir:
    sys.path.insert(0, mod_dir)

# Never open interactive windows.
import matplotlib
matplotlib.use("Agg")

sample = sys.argv[1]
sys.argv = sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(sample)))
runpy.run_path(sample, run_name="__main__")
