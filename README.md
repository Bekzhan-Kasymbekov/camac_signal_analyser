# CAMAC Signal Analyser

A desktop GUI application for reading, analysing, visualising, and exporting CAMAC acoustic emission (AE/АЭ) and electromagnetic emission (EME/ЭМЭ) signal archives.

The application supports:

- CAMAC binary archive loading
- automatic old/new CAMAC encoding detection
- AE and EME waveform display
- FFT / amplitude-frequency analysis
- energy accumulation and CUT by event number or time
- current-event analysis
- d-value, S-value, γ-value, Tsallis q
- b-value analysis
- AE and EME wavelet scalograms
- CSV export of catalogs, events, RAW data, processed signal matrices, b-value, and wavelet results
- Docker-based running on Linux, Windows, and macOS

---

## 1. Project structure

```text
camac_signal_analyser/
├── cpp_core/                 # C++ CAMAC parser + pybind11 module
├── python_gui/               # PySide6 GUI
├── sample_data/              # Put CAMAC binary archives here
├── exports/                  # Exported CSV/graph files go here
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

`sample_data/` and `exports/` are mounted into Docker, so files placed there on your computer are visible inside the application.

Inside the Docker container:

```text
/app/sample_data
/app/exports
```

---

## 2. Requirements

You need:

- Docker
- Git
- a graphical display method for Docker GUI apps

Platform notes:

```text
Linux:
    works through X11.

Windows:
    recommended through WSL2 + WSLg + Docker Desktop.

macOS:
    works through Docker Desktop + XQuartz, but GUI forwarding can be slower.
```

---

## 3. Clone the project

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
```

Create data/export folders:

```bash
mkdir -p sample_data exports
```

Put CAMAC binary archive files into:

```text
sample_data/
```

Example:

```text
sample_data/190723.001
sample_data/example.001
```

---

## 4. Build Docker image

Run this from the project root:

```bash
docker build -t camac-signal-analyser:dev .
```

This builds:

- Python environment
- PySide6 GUI dependencies
- C++ CAMAC parser
- `camac_core` pybind11 module

---

# Running on Linux

## 5. Run on Linux / Ubuntu

Allow local Docker containers to use your X11 display:

```bash
xhost +local:docker
```

Run the application:

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY="$DISPLAY" \
  -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

After closing the application, revoke access:

```bash
xhost -local:docker
```

Inside the GUI:

```text
Open archives from:
    /app/sample_data

Export files to:
    /app/exports
```

Exported files will appear on your host machine in:

```text
exports/
```

---

# Running on Windows

## 6. Recommended Windows setup

Use:

```text
Windows 11
Docker Desktop
WSL2
Ubuntu inside WSL
WSLg GUI support
```

Recommended workflow:

```text
1. Install Docker Desktop.
2. Enable WSL2 backend in Docker Desktop.
3. Install Ubuntu from Microsoft Store.
4. Open Ubuntu terminal.
5. Clone this repository inside Ubuntu/WSL.
6. Build and run from the Ubuntu/WSL terminal.
```

Do not run the Linux GUI command from normal PowerShell. Use the Ubuntu/WSL terminal.

## 7. Test WSLg first

Inside Ubuntu/WSL:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

If a small eyes window appears, WSLg GUI forwarding works.

## 8. Build on Windows through WSL

Inside Ubuntu/WSL:

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Put archive files into:

```text
sample_data/
```

## 9. Run on Windows through WSL

Inside Ubuntu/WSL:

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY="$DISPLAY" \
  -e WAYLAND_DISPLAY="$WAYLAND_DISPLAY" \
  -e XDG_RUNTIME_DIR="$XDG_RUNTIME_DIR" \
  -e PULSE_SERVER="$PULSE_SERVER" \
  -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v /mnt/wslg:/mnt/wslg:rw \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

Inside the GUI:

```text
Open archives from:
    /app/sample_data

Export files to:
    /app/exports
```

After export, check files in WSL:

```bash
ls -lh exports
```

---

# Running on macOS

## 10. macOS setup

You need:

```text
Docker Desktop
XQuartz
```

Install XQuartz, then start it:

```bash
open -a XQuartz
```

In XQuartz settings, enable:

```text
Allow connections from network clients
```

Then restart XQuartz.

Allow local X11 connections:

```bash
xhost + 127.0.0.1
```

## 11. Build on macOS

From the project root:

```bash
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Put archive files into:

```text
sample_data/
```

## 12. Run on macOS

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY=host.docker.internal:0 \
  -e QT_X11_NO_MITSHM=1 \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

Inside the GUI:

```text
Open archives from:
    /app/sample_data

Export files to:
    /app/exports
```

macOS GUI forwarding through XQuartz can be slower than Linux/Windows WSLg.

---

# Using the application

## 13. Basic workflow

```text
1. Put CAMAC archive files into sample_data/.
2. Start the application through Docker.
3. Click Browse...
4. Open archive from /app/sample_data.
5. Use Window 1 to view accumulation and CUT the archive range.
6. Use Window 2 for waveform, FFT, energy, power, and current event analysis.
7. Use Window 3 for d-value, S-value, γ-value, and Tsallis q.
8. Use Window 4 for AE and EME wavelet scalograms.
9. Use Window 5 to export CSV files.
10. Export into /app/exports.
11. Check exported files on your host machine in exports/.
```

---

# Window overview

## Window 1: Cropping / accumulation

Shows accumulated AE and EME energy.

Supports:

```text
CUT by event number
CUT by experiment time
RESET
AE and EME accumulated energy curves
```

## Window 2: Event-by-event analysis

Shows:

```text
AE waveform
EME waveform
AE FFT
EME FFT
all-events FFT summary
current event energy
current event power
max absolute amplitude
RAW header preview
delete current event
```

## Window 3: Statistical coefficients

Shows four plots:

```text
d-value
S-value
γ-value
Tsallis q
```

Modes:

```text
1 signal at a time:
    d-value is shown as a curve per impulse.
    S-value, γ-value, and Tsallis q are shown as range-level horizontal values.

Sliding-window mode:
    all four coefficients are calculated over event windows.
```

Heavy calculations run in a background worker thread, so the GUI should not freeze.

## Window 4: Wavelets

Shows two simultaneous scalograms:

```text
AE wavelet scalogram
EME wavelet scalogram
```

Modes:

```text
Current impulse:
    full time-frequency scalogram for selected AE and EME signals.

All impulses:
    summary wavelet maps over the current archive range.
```

## Window 5: Export

Exports:

```text
catalog CSV
current processed event CSV
current RAW event CSV
current range folder export
processed AE/EME signal matrix CSV
b-value CSV
wavelet CSV
graph images through plot context menu
```

---

# CSV export notes

## Processed signal matrix export

Window 5 can export two matrix files:

```text
<archive>_processed_AE_signals.csv
<archive>_processed_EME_signals.csv
```

Format:

```csv
row_label,event_1_original_1,event_2_original_2,event_3_original_3
experiment_time_seconds,0,1.779,2.621
sample_0,-357.12,-340.91,-329.44
sample_1,-125.38,-118.22,-110.05
sample_2,84.51,79.33,76.18
```

Meaning:

```text
columns:
    events/signals

first row:
    event labels

first column:
    row labels

experiment_time_seconds:
    time after the beginning of the experiment/archive

sample_0, sample_1, ...
    processed signal values
```

After CUT/delete:

```text
event_1_original_50
```

means:

```text
event_1:
    first event in the current edited range

original_50:
    original archive event number 50
```

---

# Troubleshooting

## Docker command says permission denied

On Linux, either run Docker with `sudo`:

```bash
sudo docker build -t camac-signal-analyser:dev .
```

or add your user to the Docker group:

```bash
sudo usermod -aG docker "$USER"
```

Then log out and log back in.

## GUI does not open on Linux

Try:

```bash
echo $DISPLAY
xhost +local:docker
```

Then run the Docker command again.

## GUI does not open on Windows

Inside WSL, test:

```bash
sudo apt install -y x11-apps
xeyes
```

If `xeyes` does not open, the issue is WSLg/Windows GUI forwarding, not the CAMAC application.

## GUI does not open on macOS

Make sure XQuartz is running:

```bash
open -a XQuartz
```

Allow network clients in XQuartz settings, restart XQuartz, then run:

```bash
xhost + 127.0.0.1
```

Then start the Docker container again.

## Archive is not visible in the file picker

Inside Docker, use:

```text
/app/sample_data
```

not your normal host path.

For example, if the host file is:

```text
./sample_data/test.001
```

then inside the application it appears as:

```text
/app/sample_data/test.001
```

## Exported files are not visible

Export inside the GUI to:

```text
/app/exports
```

Then check on the host:

```bash
ls -lh exports
```

## `camac_core` import fails

Run:

```bash
docker run --rm -it camac-signal-analyser:dev bash
```

Inside the container:

```bash
find /app -name "camac_core*.so"
python -c "import camac_core; print(camac_core)"
```

If `camac_core*.so` exists but import fails, check `PYTHONPATH` in the Dockerfile.

---

# Development without Docker

On Ubuntu, you can also run locally.

Create virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Build C++ parser:

```bash
cmake -S cpp_core -B cpp_core/build \
  -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR=$(python -m pybind11 --cmakedir)

cmake --build cpp_core/build -j$(nproc)
```

Run GUI:

```bash
PYTHONPATH=python_gui:cpp_core/build python3 python_gui/main.py
```

---

# Useful Docker commands

Build image:

```bash
docker build -t camac-signal-analyser:dev .
```

List images:

```bash
docker images
```

Remove image:

```bash
docker rmi camac-signal-analyser:dev
```

Run shell inside image:

```bash
docker run --rm -it camac-signal-analyser:dev bash
```

Save image to file:

```bash
docker save camac-signal-analyser:dev | gzip > camac-signal-analyser-dev.tar.gz
```

Load image from file:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

---

# Notes

This is a Dockerized desktop GUI application. Docker makes the Python/C++ environment reproducible, but GUI forwarding is platform-dependent.

Best supported:

```text
Linux / Ubuntu
```

Recommended for Windows:

```text
Windows 11 + WSL2 + WSLg + Docker Desktop
```

Possible on macOS:

```text
Docker Desktop + XQuartz
```
