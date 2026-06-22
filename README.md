# CAMAC Signal Analyser

> **Language / Язык**
>
> This README is bilingual.
>
> - English instructions are first.
> - Русская версия находится ниже, во второй половине файла.
>
> Main target platform: **Windows 10**.
>
> Recommended Windows 10 setup:
>
> ```text
> Windows 10 Build 19044+ if possible
> Docker Desktop
> WSL2
> Ubuntu inside WSL
> WSLg GUI support, or VcXsrv if WSLg does not work
> ```

CAMAC Signal Analyser is a desktop GUI application for reading, analysing, visualising, and exporting CAMAC acoustic emission (AE / АЭ) and electromagnetic emission (EME / ЭМЭ) signal archives.

---

# Main features

- CAMAC binary archive loading
- automatic old/new CAMAC encoding detection
- AE and EME waveform display
- FFT / amplitude-frequency analysis
- accumulated AE and EME energy plots
- CUT by event number or experiment time
- current-event energy, power, and max amplitude
- d-value, S-value, γ-value, and Tsallis q
- b-value analysis
- AE and EME wavelet scalograms
- CSV export of catalogs, events, RAW data, processed signal matrices, b-value, and wavelet results
- Docker-based distribution

---

# Project structure

```text
camac_signal_analyser/
├── cpp_core/                 # C++ CAMAC parser and pybind11 module
├── python_gui/               # PySide6 GUI
├── sample_data/              # Put CAMAC binary archives here
├── exports/                  # Exported CSV/graph files go here
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

Inside Docker, these folders are visible as:

```text
/app/sample_data
/app/exports
```

So if you put a file into:

```text
sample_data/archive.001
```

inside the application it appears as:

```text
/app/sample_data/archive.001
```

---

# Windows 10 recommended setup

Windows 10 can work, but the GUI part depends on Linux GUI support.

There are two possible Windows 10 paths:

```text
Option A:
    Windows 10 with WSLg GUI support.
    This is the preferred Windows 10 method.

Option B:
    Windows 10 without WSLg.
    Use VcXsrv as a Windows X server.
```

Before debugging the CAMAC application, first test whether Linux GUI apps work in WSL.

---

# Windows 10 Quick Start: test GUI support first

Open Ubuntu/WSL and run:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

If a small eyes window appears, GUI support works. Use **Option A**.

If `xeyes` does not open, WSL GUI forwarding is not working. Use **Option B** or use Windows 11 if possible.

---

# Option A: Windows 10 with WSLg

## 1. Install or update WSL

Open PowerShell as Administrator:

```powershell
wsl --install -d Ubuntu
wsl --update
wsl --shutdown
```

Then open Ubuntu from the Start Menu.

Check WSL distributions:

```powershell
wsl -l -v
```

Ubuntu should use WSL version 2.

---

## 2. Install Docker Desktop

Install Docker Desktop for Windows.

During setup, use the WSL2 backend.

After installation, open Docker Desktop and enable:

```text
Settings -> Resources -> WSL Integration -> Ubuntu
```

Docker Desktop should be running before launching the app.

---

## 3. Test GUI support

Inside Ubuntu/WSL:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

If `xeyes` opens, continue.

---

# Option A1: Run from prebuilt Docker image archive

This is the easiest method for regular users.

## 1. Download release archive

Go to the GitHub repository:

```text
GitHub repository -> Releases -> latest release
```

Download:

```text
camac-signal-analyser-dev.tar.gz
```

This file is a prebuilt Docker image archive.

It is attached to a GitHub Release as a downloadable asset. It is not committed into the normal Git source code.

---

## 2. Create working folder inside Ubuntu/WSL

Inside Ubuntu/WSL:

```bash
mkdir -p ~/camac_signal_analyser_run
cd ~/camac_signal_analyser_run
mkdir -p sample_data exports
```

If the downloaded archive is in Windows Downloads, copy it into WSL:

```bash
cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/camac-signal-analyser-dev.tar.gz .
```

Replace:

```text
YOUR_WINDOWS_USERNAME
```

with your actual Windows username.

---

## 3. Load Docker image

Inside Ubuntu/WSL:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Check that the image exists:

```bash
docker images
```

Expected:

```text
REPOSITORY              TAG
camac-signal-analyser   dev
```

---

## 4. Add CAMAC archive files

Put CAMAC binary archives into:

```text
sample_data/
```

Example:

```text
sample_data/example.001
sample_data/190723.001
```

---

## 5. Run application with WSLg

Run from Ubuntu/WSL:

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

Inside the application:

```text
Open archives from:
    /app/sample_data

Export files to:
    /app/exports
```

Exported files appear on your computer in:

```text
exports/
```

Check:

```bash
ls -lh exports
```

---

# Option A2: Build Docker image from source on Windows 10 / WSLg

Use this method if you want to build the image yourself instead of downloading the release archive.

Inside Ubuntu/WSL:

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Put CAMAC archives into:

```text
sample_data/
```

Run:

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

---

# Option B: Windows 10 without WSLg, using VcXsrv

Use this only if:

```text
xeyes does not open inside Ubuntu/WSL
```

This method uses a separate Windows X server.

---

## 1. Install VcXsrv

Install VcXsrv on Windows.

Start:

```text
XLaunch
```

Choose:

```text
Multiple windows
Start no client
Disable access control
```

Keep VcXsrv running.

---

## 2. Set DISPLAY inside Ubuntu/WSL

Inside Ubuntu/WSL:

```bash
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
export QT_X11_NO_MITSHM=1
```

Test:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

If `xeyes` opens, continue.

---

## 3. Run from prebuilt Docker archive with VcXsrv

Create working folder:

```bash
mkdir -p ~/camac_signal_analyser_run
cd ~/camac_signal_analyser_run
mkdir -p sample_data exports
```

Copy the archive into this folder:

```bash
cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/camac-signal-analyser-dev.tar.gz .
```

Load image:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Run:

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY="$DISPLAY" \
  -e QT_X11_NO_MITSHM=1 \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

---

## 4. Build from source with VcXsrv

From Ubuntu/WSL:

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Run:

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY="$DISPLAY" \
  -e QT_X11_NO_MITSHM=1 \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

---

# Common Windows 10 mistakes

## Wrong: running Python directly

Do not do this for normal use:

```bash
cd ~/camac_signal_analyser-main/python_gui
python3 main.py
```

This can fail because dependencies and `camac_core` may not be available.

Use Docker instead.

---

## Wrong: running Docker from the wrong folder

Wrong:

```bash
cd ~/camac_signal_analyser-main/python_gui
docker build -t camac-signal-analyser:dev .
```

Correct:

```bash
cd ~/camac_signal_analyser-main
docker build -t camac-signal-analyser:dev .
```

The project root must contain:

```text
Dockerfile
requirements.txt
python_gui
cpp_core
README.md
```

---

## Wrong: opening normal Windows paths inside the app

Inside Docker, use:

```text
/app/sample_data
/app/exports
```

not:

```text
C:\Users\...
```

and not:

```text
/home/username/...
```

unless you mounted that folder manually.

---

# Windows 11 note

Windows 11 is usually easier than Windows 10 because WSLg support is more reliable.

The Windows 11 command is the same as **Option A / WSLg**:

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

---

# Running on Linux / Ubuntu

Linux is the simplest platform for this Docker GUI application.

## Build from source

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Put CAMAC archives into:

```text
sample_data/
```

Allow Docker containers to use local X11:

```bash
xhost +local:docker
```

Run:

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

After closing:

```bash
xhost -local:docker
```

---

## Linux: run from release archive

```bash
mkdir -p camac_signal_analyser_run
cd camac_signal_analyser_run
mkdir -p sample_data exports
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Run:

```bash
xhost +local:docker

docker run --rm -it \
  --name camac-gui \
  -e DISPLAY="$DISPLAY" \
  -e QT_X11_NO_MITSHM=1 \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev

xhost -local:docker
```

---

# Running on macOS

macOS support requires:

```text
Docker Desktop
XQuartz
```

GUI forwarding through XQuartz can be slower than Linux or Windows WSLg.

Start XQuartz:

```bash
open -a XQuartz
```

In XQuartz settings, enable:

```text
Allow connections from network clients
```

Restart XQuartz.

Allow local X11 connections:

```bash
xhost + 127.0.0.1
```

Build from source:

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Run:

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY=host.docker.internal:0 \
  -e QT_X11_NO_MITSHM=1 \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

Run from release archive:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Then use the same macOS `docker run` command.

---

# Using the application

Basic workflow:

```text
1. Put CAMAC binary archives into sample_data/.
2. Start the application.
3. Click Browse...
4. Open archive from /app/sample_data.
5. Use Window 1 to view accumulated energy and CUT the archive range.
6. Use Window 2 for waveform, FFT, energy, power, and current event analysis.
7. Use Window 3 for d-value, S-value, γ-value, and Tsallis q.
8. Use Window 4 for AE and EME wavelet scalograms.
9. Use Window 5 to export CSV files.
10. Export into /app/exports.
11. Check exported files on your computer in exports/.
```

---

# Application windows

## Window 1: Cropping and accumulation

Shows accumulated energy curves for:

```text
AE / АЭ
EME / ЭМЭ
```

Supports:

```text
CUT by event number
CUT by experiment time
RESET
```

---

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

---

## Window 3: Statistical coefficients

Shows:

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
    S-value, γ-value, and Tsallis q are shown as range-level values.

Sliding-window mode:
    d-value, S-value, γ-value, and Tsallis q are calculated over event windows.
```

Heavy calculations run in a background worker thread, so the GUI should remain responsive.

---

## Window 4: Wavelet analysis

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

---

## Window 5: Export

Exports:

```text
catalog CSV
current processed event CSV
current RAW event CSV
current range folder export
processed AE and EME signal matrix CSV files
b-value CSV
wavelet CSV
graph images through plot context menu
```

---

# Processed signal matrix CSV format

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

# Supported CAMAC encodings

The application auto-detects supported CAMAC archive formats.

Processed signal length depends on the encoding format:

```text
Old format:
    AE:
        3072 raw samples - 12 metadata samples = 3060 processed values

    EME:
        3072 raw samples - 0 metadata samples = 3072 processed values

New format:
    AE:
        3072 raw samples - 4 timestamp samples = 3068 processed values

    EME:
        3072 raw samples - 4 timestamp samples = 3068 processed values
```

The processed signal matrix export uses already processed signals, so CAMAC metadata/header samples are not included.

---

# GitHub Release archive information

The prebuilt Docker image archive is distributed as a GitHub Release asset.

Example file:

```text
camac-signal-analyser-dev.tar.gz
```

This file should not be committed into Git.

It should be uploaded here:

```text
GitHub repository -> Releases -> latest release -> Assets
```

Users can download the archive, load it into Docker, and run the application without building the image themselves.

---

## Loading the release archive

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Check:

```bash
docker images
```

Expected:

```text
camac-signal-analyser   dev
```

Then run the application using the command for your operating system.

---

# Maintainer instructions

## Build image

```bash
docker build -t camac-signal-analyser:dev .
```

---

## Save image as compressed release archive

```bash
docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
```

Do not commit this `.tar.gz` file into Git.

Upload it as a GitHub Release asset instead.

---

## Recommended release workflow

```text
1. Commit and push source code.
2. Build Docker image.
3. Test Docker image locally.
4. Save image:
       docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
5. Open GitHub repository.
6. Open Releases.
7. Draft a new release.
8. Create a tag, for example:
       v1.0.0
9. Upload:
       camac-signal-analyser-dev.tar.gz
10. Publish release.
```

---

# Development without Docker

On Ubuntu, you can run locally.

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

Find compiled CAMAC module inside image:

```bash
docker run --rm -it camac-signal-analyser:dev bash
find /app -name "camac_core*.so"
```

Save image:

```bash
docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
```

Load image:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

---

# Troubleshooting

## Docker command says permission denied on Linux

Either run Docker with `sudo`:

```bash
sudo docker build -t camac-signal-analyser:dev .
```

or add your user to the Docker group:

```bash
sudo usermod -aG docker "$USER"
```

Then log out and log back in.

---

## GUI does not open on Windows 10

First test:

```bash
xeyes
```

If it does not open:

```bash
wsl --update
wsl --shutdown
```

Then reopen Ubuntu and test again.

If it still does not open, use VcXsrv or Windows 11.

---

## Archive is not visible in the file picker

Inside Docker, use:

```text
/app/sample_data
```

Do not use your normal Windows/Linux host path.

---

## Exported files are not visible

Export inside the GUI to:

```text
/app/exports
```

Then check on the host:

```bash
ls -lh exports
```

---

## `camac_core` import fails

Run a shell inside the image:

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

## The application is slow during heavy calculations

Some operations are computationally expensive:

```text
Window 3 statistics
Tsallis fitting
wavelet analysis for all impulses
large CSV exports
```

Recommended:

```text
Use CUT first to reduce the current archive range.
Then run heavy calculations on the selected range.
```

---

# Notes

This is a Dockerized desktop GUI application.

Docker makes the Python/C++ environment reproducible, but GUI forwarding depends on the operating system.

Primary target:

```text
Windows 10
```

Best Windows 10 path:

```text
Windows 10 Build 19044+
WSL2
Ubuntu
Docker Desktop
WSLg
```

Fallback Windows 10 path:

```text
VcXsrv
```

Easier alternative:

```text
Windows 11 + WSLg
```

---

---

# Русская версия README

# CAMAC Signal Analyser

CAMAC Signal Analyser — это настольное GUI-приложение для чтения, анализа, визуализации и экспорта CAMAC-архивов с сигналами акустической эмиссии (АЭ / AE) и электромагнитной эмиссии (ЭМЭ / EME).

Основная целевая платформа: **Windows 10**.

Рекомендуемый способ запуска:

```text
Windows 10 Build 19044+ если возможно
Docker Desktop
WSL2
Ubuntu внутри WSL
WSLg GUI support или VcXsrv, если WSLg не работает
```

---

# Возможности приложения

```text
- чтение бинарных CAMAC архивов;
- автоматическое определение старого/нового формата кодирования;
- отображение сигналов АЭ и ЭМЭ;
- FFT / АЧХ анализ;
- графики накопленной энергии АЭ и ЭМЭ;
- CUT по номеру импульса или времени эксперимента;
- анализ текущего импульса;
- расчет энергии, мощности и максимальной амплитуды;
- d-value, S-value, γ-value и параметр Тсаллиса q;
- b-value анализ;
- вейвлет-скалограммы АЭ и ЭМЭ;
- экспорт CSV файлов;
- запуск через Docker.
```

---

# Структура проекта

```text
camac_signal_analyser/
├── cpp_core/                 # C++ CAMAC parser и pybind11 модуль
├── python_gui/               # GUI на PySide6
├── sample_data/              # сюда кладутся CAMAC архивы
├── exports/                  # сюда сохраняются экспортированные файлы
├── Dockerfile
├── .dockerignore
├── requirements.txt
└── README.md
```

Внутри Docker контейнера папки доступны как:

```text
/app/sample_data
/app/exports
```

---

# Windows 10: сначала проверить GUI

В Ubuntu/WSL выполните:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

Если появилось маленькое окно с глазами, Linux GUI работает. Используйте вариант с WSLg.

Если `xeyes` не открылся, значит GUI forwarding не работает. Используйте VcXsrv или Windows 11.

---

# Вариант A: Windows 10 с WSLg

## 1. Установить или обновить WSL

В PowerShell от имени администратора:

```powershell
wsl --install -d Ubuntu
wsl --update
wsl --shutdown
```

Откройте Ubuntu из Start Menu.

---

## 2. Установить Docker Desktop

Установите Docker Desktop для Windows.

Включите WSL2 backend.

Проверьте:

```text
Settings -> Resources -> WSL Integration -> Ubuntu
```

Docker Desktop должен быть запущен.

---

# Запуск из готового Docker archive

## 1. Скачать release archive

Откройте:

```text
GitHub repository -> Releases -> latest release
```

Скачайте:

```text
camac-signal-analyser-dev.tar.gz
```

---

## 2. Подготовить папку

В Ubuntu/WSL:

```bash
mkdir -p ~/camac_signal_analyser_run
cd ~/camac_signal_analyser_run
mkdir -p sample_data exports
```

Если файл в Windows Downloads:

```bash
cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/camac-signal-analyser-dev.tar.gz .
```

---

## 3. Загрузить Docker image

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Проверить:

```bash
docker images
```

Ожидаемо:

```text
camac-signal-analyser   dev
```

---

## 4. Добавить CAMAC архивы

Положите CAMAC архивы в:

```text
sample_data/
```

---

## 5. Запустить приложение через WSLg

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

Внутри приложения:

```text
Открывать архивы из:
    /app/sample_data

Экспортировать в:
    /app/exports
```

Файлы появятся в:

```text
exports/
```

---

# Сборка из исходников на Windows 10 / WSLg

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Запуск:

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

---

# Вариант B: Windows 10 без WSLg, через VcXsrv

Используйте только если:

```text
xeyes не открывается
```

## 1. Установить VcXsrv

Запустите XLaunch.

Выберите:

```text
Multiple windows
Start no client
Disable access control
```

---

## 2. Настроить DISPLAY в Ubuntu/WSL

```bash
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
export QT_X11_NO_MITSHM=1
```

Проверить:

```bash
xeyes
```

Если окно появилось, можно запускать приложение.

---

## 3. Запустить Docker через VcXsrv

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY="$DISPLAY" \
  -e QT_X11_NO_MITSHM=1 \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

---

# Частые ошибки на Windows 10

Неправильно:

```bash
cd ~/camac_signal_analyser-main/python_gui
python3 main.py
```

Правильно для обычного пользователя:

```bash
cd ~/camac_signal_analyser-main
docker build -t camac-signal-analyser:dev .
docker run ...
```

Неправильно:

```bash
cd ~/camac_signal_analyser-main/python_gui
docker build -t camac-signal-analyser:dev .
```

Правильно:

```bash
cd ~/camac_signal_analyser-main
docker build -t camac-signal-analyser:dev .
```

В правильной папке должны быть:

```text
Dockerfile
requirements.txt
python_gui
cpp_core
README.md
```

---

# Использование приложения

```text
1. Положите CAMAC архивы в sample_data/.
2. Запустите приложение.
3. Нажмите Browse...
4. Откройте архив из /app/sample_data.
5. В Окне 1 можно посмотреть накопленную энергию и сделать CUT.
6. В Окне 2 можно смотреть сигналы, FFT, энергию, мощность.
7. В Окне 3 можно считать d-value, S-value, γ-value и Tsallis q.
8. В Окне 4 можно строить вейвлет-скалограммы АЭ и ЭМЭ.
9. В Окне 5 можно экспортировать CSV файлы.
10. Экспорт сохраняйте в /app/exports.
```

---

# Формат экспорта обработанных сигналов

Окно 5 может экспортировать два файла:

```text
<archive>_processed_AE_signals.csv
<archive>_processed_EME_signals.csv
```

Формат:

```csv
row_label,event_1_original_1,event_2_original_2,event_3_original_3
experiment_time_seconds,0,1.779,2.621
sample_0,-357.12,-340.91,-329.44
sample_1,-125.38,-118.22,-110.05
sample_2,84.51,79.33,76.18
```

---

# Поддерживаемые CAMAC форматы

```text
Старый формат:
    AE:
        3072 raw samples - 12 metadata samples = 3060 processed values

    EME:
        3072 raw samples - 0 metadata samples = 3072 processed values

Новый формат:
    AE:
        3072 raw samples - 4 timestamp samples = 3068 processed values

    EME:
        3072 raw samples - 4 timestamp samples = 3068 processed values
```

---

# Информация о GitHub Release archive

Готовый Docker image распространяется как GitHub Release asset.

Пример:

```text
camac-signal-analyser-dev.tar.gz
```

Этот файл не нужно коммитить в Git.

Его нужно загрузить сюда:

```text
GitHub repository -> Releases -> latest release -> Assets
```

Загрузка в Docker:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Проверка:

```bash
docker images
```

---

# Инструкция для разработчика

Собрать image:

```bash
docker build -t camac-signal-analyser:dev .
```

Сохранить image:

```bash
docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
```

Не коммитьте `.tar.gz` файл в Git.

Загрузите его как GitHub Release asset.

---

# Примечания

Это desktop GUI приложение, запущенное через Docker.

Docker делает Python/C++ окружение воспроизводимым, но GUI forwarding зависит от операционной системы.

Основная целевая платформа:

```text
Windows 10
```

Лучший вариант для Windows 10:

```text
Windows 10 Build 19044+
WSL2
Ubuntu
Docker Desktop
WSLg
```

Fallback:

```text
VcXsrv
```

Более простой вариант при возможности:

```text
Windows 11 + WSLg
```
