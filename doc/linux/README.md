# pynari on Linux with all local ANARI devices

This page describes how pynari (branch `mjar/devel`) is built on Linux against a local ANARI
SDK 0.17 and how its samples are run against every ANARI device built in the same workspace.
It is the Linux counterpart of [`doc/windows/README.md`](../windows/README.md), which
describes the samples, the checks and the changes made to pynari; only what differs on Linux
is repeated here.

How the devices themselves are built on Linux is described in the Blender ANARI
documentation (`blenderphi/doc/anari/LINUX.md`): the workspace, its `scripts/` directory
with `env.sh`, and the build of every device. The machine is a GPU node with Rocky Linux 10,
GCC 14, CUDA 13.3 and two NVIDIA RTX PRO 6000 Blackwell, without a display.

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

* creates the Python environment `build/pynari-venv` from the system Python 3.12 (Windows
  uses 3.13) with numpy, pybind11, Pillow and matplotlib from PyPI; the pip cache is inside
  of the workspace;
* installs mpi4py, which only `sample06` uses, from its PyPI wheel together with the `mpich`
  package, which puts an MPI library into the virtual environment, so that no environment
  module is needed;
* configures pynari against the ANARI SDK of the workspace with the options of Windows
  (`-Danari_DIR=...`, `-DPYNARI_USE_INSTALLED_PYBIND=ON`, `-Dpybind11_DIR=...`,
  `-DPython_EXECUTABLE=...`, `-DPYBIND11_FINDPYTHON=ON`) and
  `-DCMAKE_CUDA_ARCHITECTURES=120` for the Blackwell GPUs;
* builds the module `build/pynari/pynari.cpython-312-x86_64-linux-gnu.so`. It is used from
  the build directory, no wheel is installed.

No source change of pynari was needed for Linux.

## 2. Running the samples

```sh
bash scripts/run_pynari.sh                          # every installed configuration
bash scripts/run_pynari.sh -r helide,barney -s sample0
bash scripts/run_pynari.sh -r cycles_optix,cycles_cuda -j 1 --results build/pynari-out/results-gpu.json
python3 scripts/pynari_table.py                     # the table of section 3
```

[`tools/run_pynari.py`](tools/run_pynari.py) is
[`doc/windows/tools/run_all.py`](../windows/tools/run_all.py) with the paths, the library
names and the configurations of the Linux workspace: it imports that module and replaces its
settings, so the samples, the checks and the result files are the same as on Windows, and so
are the options (`-r`, `-s`, `-t`, `-j`, `--results`).
[`tools/run_pynari.sh`](tools/run_pynari.sh) starts it with the interpreter of the virtual
environment, [`tools/pynari_table.py`](tools/pynari_table.py) prints the result table.

* **Results** are in `build/pynari-out`: `<configuration>/<sample>.png` and `.log`,
  `results*.json` and `.md`. Runs which execute at the same time need different `--results`
  files.
* **Finding the libraries.** Windows registers DLL directories. On Linux the front-end
  library finds the device libraries, and the shared libraries they depend on, through
  `LD_LIBRARY_PATH`, which the runner sets for each configuration. cyclesphi-anari, the
  CPU build of Photon and MoonRay use the libraries of Blender
  (`build/blender/bin/lib`).
* **One GPU.** Every run sees one GPU only (`ANARI_GPU`, default 0), so a test loop never
  occupies both.
* **Home directory.** The samples run with `HOME` set to a directory inside of the
  workspace, so that nothing a device or matplotlib writes lands in the real one.
* **MPI.** `sample06` initializes MPI. The MPICH of the virtual environment would open the
  InfiniBand ports of the node through UCX and fails there
  (`uct_iface_open(ud_verbs/mlx5_1:1) failed`), so the runner sets `UCX_TLS=self,sm,tcp`.

Configurations which are not in the Windows matrix, selected with `-r`: `cycles_cuda`
(cyclesphi-anari on CUDA without OptiX), `rpr_cpu` and `mitsuba_scalar`.

## 3. Results

Runs of 2026-10-10 and 2026-10-11: the matrix of the
[Windows results](../windows/README.md#5-results) plus `cycles_cuda`. Each cell shows whether
the run passed (the process exited normally and wrote an image which is neither black nor
flat) and its time. The times include process start-up and are only a rough guide: the CPU
configurations ran two to four jobs in parallel, next to other tests and builds.

| sample | helide | visrtx | barney | cycles_optix | cycles_cuda | cycles_cpu | mitsuba_cuda | mitsuba_llvm | moonray | visionaray | visionaray_cuda | ospray | rpr | photon | photon_cpu |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| camera-depth-of-field | ok 92s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 2s | ok 2s | ok 3s | ok 2s | ok 3s | ok 1s | ok 49s | ok 2s | ok 4s |
| geometry-cones | ok 0s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 1s | ok 2s | ok 1s | ok 11s | ok 1s | ok 2s |
| geometry-cones-colorPerPrim | ok 0s | ok 1s | ok 14s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 1s | ok 13s | ok 1s | ok 1s |
| geometry-cones-colorPerVertex | ok 0s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 1s | ok 13s | ok 1s | ok 2s |
| geometry-cylinders | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 1s | ok 11s | ok 2s | ok 2s |
| geometry-cylinders-colorPerPrim | ok 1s | ok 1s | ok 7s | ok 3s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 1s | ok 2s | ok 1s | ok 13s | ok 1s | ok 1s |
| geometry-cylinders-colorPerVertex | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 13s | ok 1s | ok 1s |
| geometry-spheres-with-sampler1D | ok 1s | ok 2s | ok 1s | ok 2s | ok 2s | ok 10s | ok 3s | ok 7s | ok 23s | ok 14s | ok 10s | ok 6s | ok 195s | ok 4s | ok 20s |
| geometry-triangles-testorb-np | ok 1s | ok 1s | ok 2s | ok 2s | ok 1s | ok 7s | ok 2s | ok 2s | ok 30s | ok 10s | ok 4s | ok 3s | ok 90s | ok 2s | ok 13s |
| interactive-bobblespheres3 | ok 2s | ok 2s | ok 1s | ok 1s | ok 1s | ok 1s | ok 2s | ok 3s | ok 2s | ok 2s | ok 2s | ok 1s | **FAIL** 24s | ok 2s | ok 3s |
| reference-hdri | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 2s | ok 2s | ok 8s | ok 3s | ok 2s | ok 1s | ok 37s | ok 2s | ok 4s |
| sample-getInfo | ok 1s | ok 0s | ok 1s | ok 1s | ok 0s | ok 0s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s |
| sample01 | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 2s | ok 2s | ok 2s | ok 2s | ok 1s | ok 1s | ok 46s | ok 2s | ok 4s |
| sample01_with_texture | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 2s | ok 1s | ok 4s | ok 2s | ok 1s | ok 1s | ok 42s | ok 2s | ok 3s |
| sample02 | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 3s | ok 1s | ok 4s | ok 3s | ok 2s | ok 2s | **FAIL** 23s | ok 2s | ok 4s |
| sample03 | ok 1s | ok 1s | ok 2s | ok 3s | ok 2s | ok 6s | ok 7s | ok 31s | ok 51s | ok 10s | ok 2s | ok 15s | ok 396s | ok 7s | ok 98s |
| sample03-isosurface | ok 1s | ok 2s | ok 2s | ok 2s | ok 1s | ok 2s | ok 2s | ok 2s | ok 14s | ok 12s | ok 2s | ok 4s | ok 415s | ok 2s | ok 20s |
| sample04 | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 4s | ok 2s | ok 3s | ok 13s | ok 4s | ok 3s | ok 2s | ok 34s | ok 4s | ok 6s |
| sample04_pointLight | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 2s | ok 3s | ok 8s | ok 4s | ok 3s | ok 2s | ok 44s | ok 4s | ok 6s |
| sample05 | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 3s | ok 2s | ok 10s | ok 2s | ok 2s | ok 2s | ok 129s | ok 3s | ok 5s |
| sample06 | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 2s | ok 8s | ok 1s | ok 1s | ok 1s | ok 18s | ok 2s | ok 2s |
| sample07 | ok 1s | ok 1s | ok 1s | ok 2s | ok 1s | ok 3s | ok 2s | ok 3s | ok 5s | ok 6s | ok 2s | ok 4s | ok 85s | ok 2s | ok 13s |
| sampler-image3d | ok 4s | ok 1s | ok 2s | ok 1s | ok 1s | ok 2s | ok 1s | ok 2s | ok 24s | ok 6s | ok 1s | ok 4s | ok 410s | ok 2s | ok 28s |
| sampler-image3d-borderColor | ok 1s | ok 1s | ok 2s | ok 1s | ok 1s | ok 3s | ok 1s | ok 2s | ok 28s | ok 5s | ok 2s | ok 3s | ok 428s | ok 2s | ok 18s |
| testing-release_00 | ok 1s | ok 0s | ok 7s | ok 0s | ok 0s | ok 0s | ok 0s | ok 0s | ok 1s | ok 1s | ok 1s | ok 0s | ok 1s | ok 0s | ok 0s |
| testing-release_01 | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s |
| testing-release_02 | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 1s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s |
| testing-release_03 | ok 0s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s |
| testing-release_04 | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 1s | ok 0s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s |
| testing-release_05 | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 0s | ok 0s |
| unstructured-cellCentric | ok 1s | ok 1s | ok 9s | ok 2s | ok 2s | ok 5s | ok 2s | ok 3s | ok 2s | ok 4s | ok 3s | ok 1s | ok 42s | ok 1s | ok 2s |
| unstructured-vertexCentric | ok 3s | ok 1s | ok 2s | ok 2s | ok 2s | ok 6s | ok 1s | ok 3s | ok 2s | ok 4s | ok 2s | ok 1s | ok 41s | ok 1s | ok 2s |
| viewer-sample01 | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | ok 1s | ok 1s | ok 0s |
| viewer-sample02 | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | **FAIL** 31s | ok 1s | ok 1s |
| viewer-sample05 | ok 0s | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | ok 4s | ok 1s | ok 0s |
| viewer-sample07 | ok 1s | ok 1s | ok 1s | ok 1s | ok 1s | ok 0s | ok 1s | ok 1s | ok 1s | ok 0s | ok 0s | ok 0s | ok 2s | ok 1s | ok 1s |

537 of 540 runs passed. On Windows all 504 runs of its matrix pass.

## 4. Differences from Windows

* **Radeon ProRender renders on the CPU.** The precompiled GPU kernels of the RadeonProRender
  SDK 3.1.7.1 do not cover the Blackwell generation, so the device falls back to the CPU
  there. On the CPU, three samples crash inside of the RPR library (a segmentation fault in
  `rprContextRender`): `sample02`, `viewer-sample02` and `interactive-bobblespheres3`, the
  scenes of several hundred sphere instances. These are the three failures of the table. It
  is also slow: `sample03` takes 6.5 minutes.
* **`cycles_cuda`** is an additional configuration; it passes all 36 samples.
* **MoonRay** passes all 36 samples. `sample03`, which takes 6.5 minutes on the Windows
  machine, takes 30 to 100 s on the 64 cores here, depending on what else runs.
* **OSPRay** passes all 36 samples with its own Embree. With the Embree of Blender
  preloaded, the sample with a volume (`sample03`) crashes; that is how the device runs
  inside of Blender, see the Blender ANARI documentation.
* **Mitsuba** needed a fix in mitsuba-anari for `cuda_ad_rgb` (the shutdown of Dr.Jit
  between two devices); both variants pass all 36 samples with it.

## Development

AI agent harnesses were used for selected development, testing, and optimization tasks
