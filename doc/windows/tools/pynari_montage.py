"""One labelled image per pynari sample with a tile per renderer configuration.

  python pynari_montage.py <pynari-out dir> <output dir> [results.json ...]

The images come from run_all.py (<pynari-out>/<config>/<sample>.png). The status of each run
(from the given results files) is written under its tile.
"""
import glob
import json
import os
import sys

from PIL import Image, ImageDraw

src_root, out_root = sys.argv[1], sys.argv[2]
CONFIGS = ("helide", "visrtx", "barney", "cycles_optix", "cycles_cpu", "mitsuba_cuda",
           "mitsuba_llvm", "moonray", "visionaray", "visionaray_cuda", "ospray", "rpr", "photon",
           "photon_cpu")
TILE = (240, 160)
LABEL_H = 16

status = {}
for path in sys.argv[3:]:
    with open(path) as f:
        for r in json.load(f):
            status[(r["sample"], r["renderer"])] = r
# Configurations without results are left out.
if status:
    CONFIGS = tuple(c for c in CONFIGS if any(config == c for _, config in status))

samples = sorted({os.path.splitext(os.path.basename(p))[0]
                  for config in CONFIGS for p in glob.glob(os.path.join(src_root, config, "*.png"))})
os.makedirs(out_root, exist_ok=True)
for sample in samples:
    sheet = Image.new("RGB", (len(CONFIGS) * TILE[0], TILE[1] + 2 * LABEL_H), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)
    for i, config in enumerate(CONFIGS):
        x = i * TILE[0]
        draw.text((x + 4, 2), config, fill=(0, 0, 0))
        path = os.path.join(src_root, config, sample + ".png")
        r = status.get((sample, config), {})
        if os.path.exists(path) and r.get("status", "PASS") == "PASS":
            image = Image.open(path).convert("RGB")
            image.thumbnail(TILE, Image.LANCZOS)
            sheet.paste(image, (x + (TILE[0] - image.width) // 2,
                                LABEL_H + (TILE[1] - image.height) // 2))
        else:
            draw.rectangle([x, LABEL_H, x + TILE[0] - 1, LABEL_H + TILE[1] - 1], fill=(235, 235, 235))
            draw.text((x + 80, LABEL_H + TILE[1] // 2 - 6), "no image", fill=(120, 120, 120))
        if r:
            text = "{:s} {:.0f} s".format(r.get("status", "?"), r.get("time", 0.0))
            draw.text((x + 4, LABEL_H + TILE[1] + 2), text,
                      fill=(0, 120, 0) if r.get("status") == "PASS" else (200, 0, 0))
    sheet.save(os.path.join(out_root, sample + ".png"))
print("wrote {:d} sample images".format(len(samples)))
