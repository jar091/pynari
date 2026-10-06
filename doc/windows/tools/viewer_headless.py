"""Headless driver for pynari's viewer/examples scenes (the interactive viewer
needs glfw/OpenGL). Renders one frame with the viewer's default camera and
reads it back through frame.map()/unmap() exactly like viewer/anari_viewer.py.

Usage: python viewer_headless.py <example module, e.g. sample02> -o out.png
"""
import ctypes, getopt, importlib, os, sys
import numpy as np
import PIL.Image

VIEWER_DIR = "F:/work/anari/pynari/viewer"
sys.path.insert(0, VIEWER_DIR)

mod_name = sys.argv[1]
opts, _ = getopt.getopt(sys.argv[2:], "o:")
out = dict(opts).get("-o", f"viewer-{mod_name}.png")

mod = importlib.import_module(f"examples.{mod_name}")
scene = mod.AnariScene()
w, h = 800, 600
scene.anari_init(w, h)

# viewer defaults: yaw=-90, pitch=0, distance=5, up=+y -> dir = (0,0,-1)
yaw, pitch, distance = -90.0, 0.0, 5.0
d = np.array([np.cos(np.radians(yaw)) * np.cos(np.radians(pitch)),
              np.sin(np.radians(pitch)),
              np.sin(np.radians(yaw)) * np.cos(np.radians(pitch))])
up = scene.get_camera_up()
eye = -d * distance
scene.anari_render(w, h, eye, d, up, 60.0)

ptr = scene.anari_fb_map()
if not ptr:
    raise RuntimeError("frame.map('channel.color') returned a null pointer")
pixels = np.ctypeslib.as_array(ctypes.cast(ptr, ctypes.POINTER(ctypes.c_ubyte)),
                               shape=(h, w, 4)).copy()
scene.anari_fb_unmap()
im = PIL.Image.fromarray(pixels).transpose(PIL.Image.FLIP_TOP_BOTTOM).convert("RGB")
print(f"@viewer_headless: saving {out}")
im.save(out)
