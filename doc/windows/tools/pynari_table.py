"""Markdown matrix of the pynari run_all.py results.

  python pynari_table.py results-a.json [results-b.json ...]
"""
import json
import os
import sys

CONFIGS = ("helide", "visrtx", "barney", "cycles_optix", "cycles_cpu", "mitsuba_cuda",
           "mitsuba_llvm", "moonray", "visionaray", "visionaray_cuda", "ospray", "rpr", "photon",
           "photon_cpu")
results = {}
for path in sys.argv[1:]:
    with open(path) as f:
        for r in json.load(f):
            if r["renderer"] in CONFIGS:
                results[(r["sample"], r["renderer"])] = r
# Configurations without results are left out.
CONFIGS = tuple(c for c in CONFIGS if any(config == c for _, config in results))

samples = sorted({s for s, _ in results})
lines = ["| sample | " + " | ".join(CONFIGS) + " |",
         "|---|" + "---|" * len(CONFIGS)]
passed = total = 0
for sample in samples:
    cells = []
    for config in CONFIGS:
        r = results.get((sample, config))
        if r is None:
            cells.append("–")
            continue
        total += 1
        ok = r["status"] == "PASS"
        passed += ok
        cell = "{:s} {:.0f}s".format("ok" if ok else "**" + r["status"] + "**", r["time"])
        cells.append(cell)
    name = sample
    if os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "images",
                                   sample + ".png")):
        name = "[{0:s}](images/{0:s}.png)".format(sample)
    lines.append("| {:s} | {:s} |".format(name, " | ".join(cells)))
print("\n".join(lines))
print("\n{:d} of {:d} runs passed.".format(passed, total))
