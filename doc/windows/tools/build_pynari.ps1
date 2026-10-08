# Configure and build pynari (F:\work\anari\pynari) against the local ANARI-SDK 0.17 install.
# Output: F:\work\anari\build\pynari\Release\pynari.cp313-win_amd64.pyd
$ErrorActionPreference = "Stop"
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsPath = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
$env:PATH = "$(Split-Path -Parent $vswhere);$env:PATH"
Import-Module (Join-Path $vsPath "Common7\Tools\Microsoft.VisualStudio.DevShell.dll")
Enter-VsDevShell -VsInstallPath $vsPath -SkipAutomaticLocation -DevCmdArguments "-arch=x64 -host_arch=x64" | Out-Null
$py = "F:/work/anari/build/pynari-venv/Scripts/python.exe"
if (-not (Test-Path $py)) {
  & D:/apps/Python313/python.exe -m venv F:/work/anari/build/pynari-venv
  & $py -m pip install --upgrade pip
  & $py -m pip install numpy pybind11 pillow matplotlib
}
$pybindDir = & $py -c "import pybind11; print(pybind11.get_cmake_dir())"
cmake -S F:/work/anari/pynari -B F:/work/anari/build/pynari -G "Visual Studio 17 2022" -A x64 `
  "-Danari_DIR=F:/work/anari/install/lib/cmake/anari-0.17.0" `
  "-DPYNARI_USE_INSTALLED_PYBIND=ON" "-Dpybind11_DIR=$pybindDir" `
  "-DPython_EXECUTABLE=$py" "-DPYBIND11_FINDPYTHON=ON" "-DCMAKE_CUDA_ARCHITECTURES=native"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
cmake --build F:/work/anari/build/pynari --config Release --parallel
exit $LASTEXITCODE
