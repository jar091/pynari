"""Headless driver for pynari's samples/interactive/*.py (matplotlib
FuncAnimation apps): replaces plt.show() by calling the animation's update
function a few times (each call renders an ANARI frame) and saving the figure.

Usage: python interactive_headless.py <script.py> -o out.png [-n frames]
"""
import getopt, os, runpy, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.animation as animation
import matplotlib.pyplot as plt

script = sys.argv[1]
opts, _ = getopt.getopt(sys.argv[2:], "o:n:")
opts = dict(opts)
out = opts.get("-o", "interactive.png")
nframes = int(opts.get("-n", "3"))

_anims = []
_orig_init = animation.FuncAnimation.__init__


def _init(self, fig, func, *a, **kw):
    _anims.append((fig, func))
    _orig_init(self, fig, func, *a, **kw)


def _show(*a, **kw):
    if not _anims:
        raise RuntimeError("no FuncAnimation was created before plt.show()")
    fig, func = _anims[-1]
    for i in range(nframes):
        func(i)
    fig.savefig(out)
    print(f"@interactive_headless: rendered {nframes} frames, saved {out}")


animation.FuncAnimation.__init__ = _init
plt.show = _show
sys.argv = [script]
sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
runpy.run_path(script, run_name="__main__")
