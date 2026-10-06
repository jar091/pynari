"""Run every pynari sample with every installed ANARI renderer.

Each (sample, renderer) pair runs in its own process (the moonray and the
Blender/Cycles DLL sets must never meet in one process), with a timeout.
Outputs go to F:/work/anari/build/pynari-out/<renderer>/<sample>.png together
with a per-run log; a summary is written to results.json and results.md.

Usage:
  python run_all.py                       # full matrix
  python run_all.py -r helide,visrtx      # only some renderer configs
  python run_all.py -s sample01,sample02  # only samples whose name contains one of these
  python run_all.py -t 900 -j 2           # timeout per run [s], parallel jobs
  python run_all.py --md-only             # rescan logs, rewrite results.md
Use the venv interpreter: F:/work/anari/build/pynari-venv/Scripts/python.exe
"""
import argparse, concurrent.futures, glob, json, os, subprocess, sys, time

ROOT = "F:/work/anari"
SRC = f"{ROOT}/pynari"
OUT = f"{ROOT}/build/pynari-out"
PYTHON = f"{ROOT}/build/pynari-venv/Scripts/python.exe"
MODULE_DIR = f"{ROOT}/build/pynari/Release"   # pynari.cp313-win_amd64.pyd
LAUNCH = f"{OUT}/_launch.py"

INSTALL_BIN = f"{ROOT}/install/bin"
BLENDER_SHARED = f"{ROOT}/build/blender/bin/Release/blender.shared"
MITSUBA_BIN = f"{ROOT}/install/mitsuba/bin"
MOONRAY_BIN = f"{ROOT}/install/moonray/bin"
OSPRAY_BIN = f"{ROOT}/install/ospray/bin"
RPR_BIN = f"{ROOT}/install/rpr/bin"
PHOTON_BIN = f"{ROOT}/install/photon/bin"
PHOTON_CPU_BIN = f"{ROOT}/install/photon_cpu/bin"

# renderer config name -> (ANARI library, dll dirs, extra env)
RENDERERS = {
    "helide":        ("helide",  [INSTALL_BIN], {}),
    "visrtx":        ("visrtx",  [INSTALL_BIN], {}),
    "barney":        ("barney",  [INSTALL_BIN], {}),
    "cycles_optix":  ("cycles",  [INSTALL_BIN, BLENDER_SHARED], {"CYCLES_ANARI_USE_GPU": "OPTIX"}),
    "cycles_cpu":    ("cycles",  [INSTALL_BIN, BLENDER_SHARED], {"ANARI_CYCLES_FORCE_CPU": "1"}),
    "mitsuba_cuda":  ("mitsuba", [MITSUBA_BIN, INSTALL_BIN], {"ANARI_MITSUBA_VARIANT": "cuda_ad_rgb"}),
    # llvm_ad_rgb needs LLVM-C.dll; Dr.Jit loads it with LoadLibrary from PATH,
    # it is staged into install/mitsuba/bin (taken from the official LLVM
    # 20.1.8 Windows release, F:/work/anari/external/llvm).
    "mitsuba_llvm":  ("mitsuba", [MITSUBA_BIN, INSTALL_BIN], {"ANARI_MITSUBA_VARIANT": "llvm_ad_rgb"}),
    # Scalar (non-vectorized) CPU variant: slow, optional (not in the default
    # matrix), select it explicitly with -r mitsuba_scalar.
    "mitsuba_scalar": ("mitsuba", [MITSUBA_BIN, INSTALL_BIN], {"ANARI_MITSUBA_VARIANT": "scalar_rgb"}),
    "moonray":       ("moonray", [MOONRAY_BIN, INSTALL_BIN], {}),
    # anari-visionaray builds one library per back-end.
    "visionaray":      ("visionaray",      [INSTALL_BIN], {}),
    "visionaray_cuda": ("visionaray_cuda", [INSTALL_BIN], {}),
    # anari-ospray with the OSPRay 3.2 runtime (Embree, Open VKL, OIDN, TBB) next to it.
    "ospray":          ("ospray", [OSPRAY_BIN, INSTALL_BIN], {}),
    # RadeonProRenderANARI with the RadeonProRender SDK runtime (Northstar) next to it.
    "rpr":             ("rpr", [RPR_BIN, INSTALL_BIN], {}),
    # Photon (Kokkos): the CUDA and the CPU build are the same library in two directories.
    "photon":          ("photon", [PHOTON_BIN, INSTALL_BIN], {}),
    "photon_cpu":      ("photon", [PHOTON_CPU_BIN, INSTALL_BIN], {}),
}
def installed(rname):
    lib, dlls, _ = RENDERERS[rname]
    return any(os.path.exists(f"{d}/anari_library_{lib}.dll") for d in dlls)


# The default matrix: every configuration whose device library is installed.
DEFAULT_RENDERERS = [r for r in RENDERERS if r != "mitsuba_scalar" and installed(r)]

# Samples that do not produce an image / do not take '-o'.
NO_IMAGE = {"sample-getInfo"}


# viewer/examples scenes run through viewer_headless.py (the viewer itself
# needs glfw/OpenGL); sample_volume_vdb/_sitk need pyopenvdb/SimpleITK + data
# downloads and are not part of the matrix.
VIEWER_EXAMPLES = ["sample01", "sample02", "sample05", "sample07"]


def find_samples():
    s = sorted(glob.glob(f"{SRC}/samples/*.py")) + sorted(glob.glob(f"{SRC}/testing/*.py"))
    s += sorted(glob.glob(f"{SRC}/samples/interactive/*.py"))
    s = [p.replace("\\", "/") for p in s]
    return s + [f"viewer:{m}" for m in VIEWER_EXAMPLES]


def sample_name(path):
    if path.startswith("viewer:"):
        return "viewer-" + path[len("viewer:"):]
    base = os.path.splitext(os.path.basename(path))[0]
    if "/testing/" in path:
        return "testing-" + base
    if "/interactive/" in path:
        return "interactive-" + base
    return base


def image_stats(png):
    try:
        from PIL import Image
        import numpy as np
        a = np.asarray(Image.open(png).convert("RGB"), dtype=np.float32)
        st = {"w": a.shape[1], "h": a.shape[0], "mean": round(float(a.mean()), 2),
              "std": round(float(a.std()), 2), "max": int(a.max())}
        if a.max() < 4:
            st["verdict"] = "BLACK"
        elif a.std() < 1.0:
            st["verdict"] = "FLAT"
        else:
            st["verdict"] = "ok"
        return st
    except Exception as e:  # noqa: BLE001
        return {"verdict": f"unreadable: {e}"}


def run_one(sample, rname, timeout):
    lib, dlls, extra = RENDERERS[rname]
    name = sample_name(sample)
    odir = f"{OUT}/{rname}"
    os.makedirs(odir, exist_ok=True)
    png = f"{odir}/{name}.png"
    log = f"{odir}/{name}.log"
    if os.path.exists(png):
        os.remove(png)
    env = dict(os.environ)
    env["ANARI_LIBRARY"] = lib
    env["PATH"] = os.pathsep.join([d.replace("/", "\\") for d in dlls] + [env.get("PATH", "")])
    env["PYNARI_DLL_DIRS"] = os.pathsep.join(dlls)
    env["PYNARI_MODULE_DIR"] = MODULE_DIR
    env["MPLBACKEND"] = "Agg"
    env["PYTHONUNBUFFERED"] = "1"
    env.setdefault("PYNARI_LOG_LEVEL", "1")  # pynari prints device warnings
    env.update(extra)
    if sample.startswith("viewer:"):
        cmd = [PYTHON, LAUNCH, f"{OUT}/viewer_headless.py", sample[len("viewer:"):]]
    elif "/interactive/" in sample:
        cmd = [PYTHON, LAUNCH, f"{OUT}/interactive_headless.py", sample]
    else:
        cmd = [PYTHON, LAUNCH, sample]
    has_image = name not in NO_IMAGE and not name.startswith("testing-")
    if has_image:
        cmd += ["-o", png]
    t0 = time.time()
    status, rc = "PASS", None
    with open(log, "w", encoding="utf-8", errors="replace") as f:
        f.write(f"# {' '.join(cmd)}\n# ANARI_LIBRARY={lib} extra={extra}\n")
        f.flush()
        try:
            p = subprocess.run(cmd, cwd=odir, env=env, stdout=f, stderr=subprocess.STDOUT,
                               timeout=timeout)
            rc = p.returncode
            if rc != 0:
                status = "FAIL"
        except subprocess.TimeoutExpired:
            status = "TIMEOUT"
            # kill leftovers (subprocess.run already killed the child)
    dt = time.time() - t0
    res = {"sample": name, "renderer": rname, "status": status, "rc": rc,
           "time": round(dt, 1), "log": log}
    if has_image:
        if os.path.exists(png):
            res["image"] = png
            res.update(image_stats(png))
        elif status == "PASS":
            res["status"] = "FAIL"
            res["verdict"] = "no image written"
    # last error-ish lines of the log
    try:
        with open(log, encoding="utf-8", errors="replace") as f:
            lines = [l.rstrip() for l in f if l.strip()]
        errs = [l for l in lines if any(k in l for k in ("Error", "ERROR", "FATAL", "Traceback", "error"))]
        res["tail"] = (errs[-3:] if errs else lines[-2:]) if res["status"] != "PASS" else errs[-2:]
        # ANARI status messages printed by pynari (PYNARI_LOG_LEVEL=1); the
        # process still exits 0 when a device rejects a render.
        res["anari_errors"] = sum(1 for l in lines if l.startswith("[ERROR]") or l.startswith("[FATAL]"))
        res["anari_warnings"] = sum(1 for l in lines if l.startswith("[WARN ]"))
    except OSError:
        pass
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-r", "--renderers", default=",".join(DEFAULT_RENDERERS))
    ap.add_argument("-s", "--samples", default="")
    ap.add_argument("-t", "--timeout", type=float, default=600)
    ap.add_argument("-j", "--jobs", type=int, default=1)
    ap.add_argument("--results", default=f"{OUT}/results.json")
    a = ap.parse_args()
    rnames = [r for r in a.renderers.split(",") if r]
    samples = find_samples()
    if a.samples:
        keys = a.samples.split(",")
        samples = [s for s in samples if any(k == sample_name(s) or k in sample_name(s) for k in keys)]
    # merge with previous results so partial reruns update the matrix
    results = {}
    if os.path.exists(a.results):
        with open(a.results) as f:
            for r in json.load(f):
                results[(r["sample"], r["renderer"])] = r
    jobs = [(s, r) for r in rnames for s in samples]
    with concurrent.futures.ThreadPoolExecutor(max_workers=a.jobs) as ex:
        futs = {ex.submit(run_one, s, r, a.timeout): (s, r) for s, r in jobs}
        for fu in concurrent.futures.as_completed(futs):
            r = fu.result()
            results[(r["sample"], r["renderer"])] = r
            print(f"{r['renderer']:14s} {r['sample']:36s} {r['status']:8s} {r['time']:7.1f}s "
                  f"{r.get('verdict', '')} {r.get('tail', '') if r['status'] != 'PASS' else ''}",
                  flush=True)
            with open(a.results, "w") as f:
                json.dump(sorted(results.values(), key=lambda x: (x["renderer"], x["sample"])), f, indent=1)
    write_md(results, a.results.replace(".json", ".md"))


def write_md(results, path):
    rs = [r for r in RENDERERS if any(k[1] == r for k in results)]
    ss = sorted({k[0] for k in results})
    with open(path, "w") as f:
        f.write("Cell: status [image verdict] [E<n>: ANARI error messages] [W<n>: warnings] time.\n"
                "PASS = process exited 0 (and wrote its image). BLACK/FLAT = image looks empty.\n\n")
        f.write("| sample | " + " | ".join(rs) + " |\n|---|" + "---|" * len(rs) + "\n")
        for s in ss:
            cells = []
            for r in rs:
                x = results.get((s, r))
                if not x:
                    cells.append("-")
                    continue
                c = x["status"]
                v = x.get("verdict")
                if c == "PASS" and v and v != "ok":
                    c += f" ({v})"
                if x.get("anari_errors"):
                    c += f" E{x['anari_errors']}"
                if x.get("anari_warnings"):
                    c += f" W{x['anari_warnings']}"
                cells.append(f"{c} {x['time']}s")
            f.write(f"| {s} | " + " | ".join(cells) + " |\n")


if __name__ == "__main__":
    if sys.argv[1:] == ["--md-only"]:
        # re-derive the log-based counts and rewrite results.md
        with open(f"{OUT}/results.json") as f:
            res = {(r["sample"], r["renderer"]): r for r in json.load(f)}
        for r in res.values():
            try:
                with open(r["log"], encoding="utf-8", errors="replace") as f:
                    lines = [l.rstrip() for l in f if l.strip()]
                r["anari_errors"] = sum(1 for l in lines if l.startswith(("[ERROR]", "[FATAL]")))
                r["anari_warnings"] = sum(1 for l in lines if l.startswith("[WARN ]"))
            except OSError:
                pass
        with open(f"{OUT}/results.json", "w") as f:
            json.dump(sorted(res.values(), key=lambda x: (x["renderer"], x["sample"])), f, indent=1)
        write_md(res, f"{OUT}/results.md")
    else:
        main()
