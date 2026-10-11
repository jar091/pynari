# pynari on macOS with all local ANARI devices

This page describes how pynari (branch `mjar/devel`) is built on macOS against a local ANARI
SDK 0.17 and how its samples are run against every ANARI device built in the same workspace.
It is the macOS counterpart of [`doc/windows/README.md`](../windows/README.md), which
describes the samples, the checks and the changes made to pynari; only what differs on macOS
is repeated here.

How the devices themselves are built on macOS is described in the Blender ANARI
documentation (`blenderphi/doc/anari/MACOS.md`): the workspace, its `scripts/` directory
with `env.sh`, and the build of every device. The machine is an Apple M4 (arm64) with
macOS 26 and Xcode. There is no CUDA or OptiX on macOS: the GPU configurations are
cyclesphi-anari and Mitsuba on Metal, everything else renders on the CPU, and VisRTX is not
available.

Contents:

1. [Building pynari](#1-building-pynari)
2. [Running the samples](#2-running-the-samples)
3. [Results](#3-results)
4. [Differences from Windows](#4-differences-from-windows)

## 1. Building pynari

```sh
bash scripts/build_pynari.sh
```

[`tools/build_pynari.sh`](tools/build_pynari.sh) is the script; it belongs into the
`scripts/` directory of the workspace, next to the `env.sh` of the Blender ANARI
documentation, which sets the paths and the compiler options it uses. It

* creates the Python environment `build/pynari-venv` from Homebrew's Python 3.13 (the
  version used on Windows) with numpy, pybind11, Pillow and matplotlib from PyPI; the pip
  cache is inside of the workspace;
* installs mpi4py, which only `sample06` uses and which is built against Homebrew's
  Open MPI;
* configures pynari against the ANARI SDK of the workspace with the options of Windows
  (`-Danari_DIR=...`, `-DPYNARI_USE_INSTALLED_PYBIND=ON`, `-Dpybind11_DIR=...`,
  `-DPython_EXECUTABLE=...`, `-DPYBIND11_FINDPYTHON=ON`);
* builds the module `build/pynari/pynari.cpython-313-darwin.so`. It is used from the build
  directory, no wheel is installed.

No source change of pynari was needed for macOS.

## 2. Running the samples

```sh
bash scripts/run_pynari.sh                           # every installed configuration
bash scripts/run_pynari.sh -r helide,barney -s sample0
bash scripts/run_pynari.sh -r ospray --results build/pynari-out/results-ospray.json
bash scripts/run_pynari.sh -r moonray -j 1 -t 1500 --results build/pynari-out/results-moonray.json
```

[`tools/run_pynari.py`](tools/run_pynari.py) is
[`doc/windows/tools/run_all.py`](../windows/tools/run_all.py) with the paths, the library
names and the configurations of the macOS workspace: it imports that module and replaces its
settings, so the samples, the checks and the result files are the same as on Windows, and so
are the options (`-r`, `-s`, `-t`, `-j`, `--results`).
[`tools/run_pynari.sh`](tools/run_pynari.sh) starts it with the interpreter of the virtual
environment.

* **Results** are in `build/pynari-out`: `<configuration>/<sample>.png` and `.log`,
  `results*.json` and `.md`. Runs which execute at the same time need different `--results`
  files.
* **Finding the libraries.** Windows registers DLL directories. On macOS the front-end
  library finds the device libraries next to itself (`install/lib`); devices in other
  directories, and the libraries a device depends on, are found through
  `DYLD_LIBRARY_PATH`, which the runner sets per configuration. For cyclesphi-anari that is
  `Blender.app/Contents/Resources/lib`. `DYLD_LIBRARY_PATH` does not survive a start through
  a system binary such as `/usr/bin/env` or `/bin/sh`, so the samples are started with the
  interpreter directly.
* **Home directory.** The samples run with `HOME` and `CFFIXED_USER_HOME` set to a
  directory inside of the workspace, and `MPLCONFIGDIR` likewise.
* **Kernel caches.** cyclesphi-anari on Metal and Mitsuba compile their kernels at the
  first render (cyclesphi about two and a half minutes on this machine) and cache them
  inside of the workspace.

## 3. Results

| Configuration | ANARI library | Selected with | Samples passed | Time of all 36 |
|---|---|---|---|---|
| `helide` | helide | | 36 of 36 | 11 s |
| `barney` | barney (CPU back end) | | 36 of 36 | 198 s |
| `cycles_cpu` | cycles | `ANARI_CYCLES_FORCE_CPU=1` | 36 of 36 | 70 s |
| `cycles_metal` | cycles | `CYCLES_ANARI_USE_GPU=METAL` | 36 of 36 | 73 s |
| `visionaray` | visionaray | | 36 of 36 | 89 s |
| `ospray` | ospray | | 36 of 36 | 83 s |
| `rpr_cpu` | rpr | `ANARI_RPR_COMPUTE_DEVICE=cpu` | 35 of 36: `interactive-bobblespheres3` ends with a bus error in the RPR library; in other runs `sample02` and `viewer-sample02` did as well | 595 s |
| `rpr` | rpr | `ANARI_RPR_COMPUTE_DEVICE=gpu` | does not finish a frame (timeout); not in the default matrix | |
| `photon_cpu` | photon | | 36 of 36 | 143 s |
| `mitsuba_llvm` | mitsuba | `ANARI_MITSUBA_VARIANT=llvm_ad_rgb` | 36 of 36 | 50 s |
| `mitsuba_metal` | mitsuba | `ANARI_MITSUBA_VARIANT=metal_ad_rgb` | 36 of 36 | 32 s |
| `moonray` | moonray | | 36 of 36 | 93 s |

Run of 2026-10-11 with two jobs in parallel, with the kernels of cyclesphi and Mitsuba
already cached; the `moonray` row is from a run of its own with one job. A sample passes
when its process exits normally and wrote its image; none of the images of the passing
samples is black or flat. The 36 samples are the 25 scripts in `samples/`, the six scripts
in `testing/`, the interactive sample and the four viewer examples, the latter two driven
headless by the tools of the Windows documentation. The images of `mitsuba_llvm` and
`mitsuba_metal` have the same mean brightness in every sample.

## 4. Differences from Windows

* **No CUDA, OptiX or HIP.** The configurations `visrtx`, `cycles_optix`, `mitsuba_cuda`,
  `visionaray_cuda` and the GPU build of Photon do not exist. `cycles_metal` and
  `mitsuba_metal` take their place; barney runs its CPU back end.
* **Radeon ProRender.** On the GPU (through Metal) no frame finishes, so `rpr` is not in the
  default matrix. On the CPU `interactive-bobblespheres3` ends with a bus error inside of
  the RPR library, and in other runs `sample02` and `viewer-sample02` did as well. The
  macOS libraries of the RadeonProRender SDK are those of version 3.1.6.
* **MoonRay** passes all 36 samples in 93 s; the Windows run took 1153 s, of which
  `sample03` 398 s (4 s here). Its images have the mean brightness of the Windows run within
  2 of 255 in every sample, except the two `sampler-image3d` samples (224 here, 241 on
  Windows; `image3D` samplers are not supported by the device on either platform).
* **Mitsuba on LLVM** needs a `libLLVM.dylib` which exports only the C API when it runs
  inside of Blender; for pynari the one of Homebrew works. See the Blender ANARI
  documentation.
