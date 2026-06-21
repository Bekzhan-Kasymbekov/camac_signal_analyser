> **Language / Язык**
>
> This README is bilingual.
>
> - English instructions are first.
> - Русская версия инструкции находится ниже, во второй половине файла.
>
> Основные пользователи приложения работают на Windows 11, поэтому рекомендуемый способ запуска: **Docker Desktop + WSL2 + Ubuntu + WSLg**. CAMAC Signal Analyser

# CAMAC Signal Analyser is a desktop GUI application for reading, analysing, visualising, and exporting CAMAC acoustic emission (AE / АЭ) and electromagnetic emission (EME / ЭМЭ) signal archives.

The application is intended mainly for **Windows 11 users**, but it can also run on Linux and macOS through Docker.

---

## Main features

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

## Project structure

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

then inside the application it appears as:

```text
/app/sample_data/archive.001
```

---

# Recommended setup for Windows 11

The recommended Windows 11 setup is:

```text
Windows 11
Docker Desktop
WSL2
Ubuntu inside WSL
WSLg GUI support
```

This avoids installing Python, CMake, PySide6, pybind11, and C++ build tools directly on Windows.

---

## Windows 11 Quick Start: run from prebuilt release archive

This is the easiest method for regular users.

### 1. Install WSL and Ubuntu

Open **PowerShell as Administrator** and run:

```powershell
wsl --install
```

Restart Windows if asked.

Then open **Ubuntu** from the Start Menu and finish the Ubuntu setup.

---

### 2. Install Docker Desktop

Install Docker Desktop for Windows.

During setup, use the **WSL2 backend**.

After installation, open Docker Desktop and check:

```text
Settings -> Resources -> WSL Integration
```

Enable integration for your Ubuntu distribution.

---

### 3. Test Linux GUI support

Inside Ubuntu/WSL, run:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

If a small eyes window appears, WSLg GUI support works.

If `xeyes` does not open, fix WSLg/Windows GUI support before running this application.

---

### 4. Download the Docker image archive

Go to the GitHub repository release page:

```text
GitHub repository -> Releases -> latest release
```

Download the release asset:

```text
camac-signal-analyser-dev.tar.gz
```

This file is a prebuilt Docker image archive.

It is not part of the normal Git repository source code. It is attached to the GitHub Release as a downloadable asset.

---

### 5. Prepare working folder inside Ubuntu/WSL

Inside Ubuntu/WSL:

```bash
mkdir -p ~/camac_signal_analyser_run
cd ~/camac_signal_analyser_run
mkdir -p sample_data exports
```

Move or copy the downloaded archive into this folder.

For example, if the file is in your Windows Downloads folder:

```bash
cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/camac-signal-analyser-dev.tar.gz .
```

Replace `YOUR_WINDOWS_USERNAME` with your actual Windows username.

---

### 6. Load the Docker image

Inside Ubuntu/WSL:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Check that the image exists:

```bash
docker images
```

You should see something like:

```text
REPOSITORY              TAG
camac-signal-analyser   dev
```

---

### 7. Add CAMAC archives

Put CAMAC binary archive files into:

```text
sample_data/
```

Example:

```text
sample_data/example.001
sample_data/190723.001
```

---

### 8. Run the application on Windows 11 through WSL

Run this command from Ubuntu/WSL:

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

After export, files appear on your computer in:

```text
exports/
```

Check from Ubuntu/WSL:

```bash
ls -lh exports
```

---

# Windows 11: build from source instead

Use this method if you want to build the Docker image yourself.

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

# Running on Linux

Linux is the simplest platform for this Docker GUI application.

## 1. Clone and build

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

---

## 2. Run on Linux

Allow Docker containers to use the local X11 display:

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

After closing the application:

```bash
xhost -local:docker
```

Inside the application:

```text
Open archives from:
    /app/sample_data

Export files to:
    /app/exports
```

---

## Linux: run from prebuilt release archive

If you downloaded:

```text
camac-signal-analyser-dev.tar.gz
```

load it with:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Then create working folders:

```bash
mkdir -p sample_data exports
```

Put archives into:

```text
sample_data/
```

Run the same Linux Docker command above.

---

# Running on macOS

macOS support requires Docker Desktop and XQuartz.

GUI forwarding through XQuartz can be slower than Linux or Windows WSLg.

---

## 1. Install requirements

Install:

```text
Docker Desktop
XQuartz
```

Start XQuartz:

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

---

## 2. Build on macOS

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Put CAMAC archive files into:

```text
sample_data/
```

---

## 3. Run on macOS

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY=host.docker.internal:0 \
  -e QT_X11_NO_MITSHM=1 \
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

---

## macOS: run from prebuilt release archive

If you downloaded:

```text
camac-signal-analyser-dev.tar.gz
```

load it with:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Then run the same macOS Docker command above.

---

# Using the application

## Basic workflow

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

Shows four coefficient plots:

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
    full time-frequency scalogram for the selected AE and EME signals.

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

# Supported CAMAC encodings

The application auto-detects supported CAMAC archive formats.

The exported processed signal length depends on the encoding format:

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

The processed signal matrix export uses the already processed signals, so CAMAC metadata/header samples are not included.

---

# GitHub Release archive information

The prebuilt Docker image archive is distributed as a GitHub Release asset.

Example file:

```text
camac-signal-analyser-dev.tar.gz
```

This file should not be committed into the Git repository.

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

Check the image:

```bash
docker images
```

Expected image:

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

## Test image on Linux

```bash
mkdir -p sample_data exports

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

## Save image as compressed release archive

```bash
docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
```

Do not commit this `.tar.gz` file into Git.

Upload it as a GitHub Release asset instead.

---

## Load image archive for testing

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

---

## Recommended release workflow

```text
1. Commit and push source code.
2. Build Docker image.
3. Test Docker image locally.
4. Save image:
       docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
5. Go to GitHub repository.
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

## GUI does not open on Linux

Check:

```bash
echo $DISPLAY
```

Then allow local Docker GUI access:

```bash
xhost +local:docker
```

Run the Docker command again.

---

## GUI does not open on Windows

Inside Ubuntu/WSL, test:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

If `xeyes` does not open, the issue is WSLg/Windows GUI support, not the CAMAC application.

---

## GUI does not open on macOS

Make sure XQuartz is running:

```bash
open -a XQuartz
```

Enable:

```text
Allow connections from network clients
```

Restart XQuartz.

Then run:

```bash
xhost + 127.0.0.1
```

Start the Docker container again.

---

## Archive is not visible in the file picker

Inside Docker, use:

```text
/app/sample_data
```

Do not use your normal host path.

Example:

```text
Host:
    ./sample_data/test.001

Inside application:
    /app/sample_data/test.001
```

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

Best supported:

```text
Linux / Ubuntu
```

Recommended for primary users:

```text
Windows 11 + WSL2 + WSLg + Docker Desktop
```

Possible on macOS:

```text
Docker Desktop + XQuartz
```

---

# Русская версия README

# CAMAC Signal Analyser

CAMAC Signal Analyser — это настольное GUI-приложение для чтения, анализа, визуализации и экспорта CAMAC-архивов с сигналами акустической эмиссии (АЭ / AE) и электромагнитной эмиссии (ЭМЭ / EME).

Основная целевая платформа: **Windows 11**.

Рекомендуемый способ запуска на Windows 11:

```text
Docker Desktop
WSL2
Ubuntu внутри WSL
WSLg для отображения GUI
```

Такой способ позволяет не устанавливать Python, CMake, PySide6, pybind11 и C++ build tools напрямую в Windows.

---

## Возможности приложения

Приложение поддерживает:

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

## Структура проекта

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

То есть файл:

```text
sample_data/archive.001
```

внутри приложения будет виден как:

```text
/app/sample_data/archive.001
```

---

# Быстрый запуск на Windows 11 через готовый Docker-архив

Это рекомендуемый способ для обычных пользователей.

---

## 1. Установить WSL и Ubuntu

Откройте **PowerShell от имени администратора** и выполните:

```powershell
wsl --install
```

Если Windows попросит перезагрузку, перезагрузите компьютер.

После этого откройте **Ubuntu** из меню Start и завершите первичную настройку.

---

## 2. Установить Docker Desktop

Установите Docker Desktop для Windows.

Во время установки используйте backend:

```text
WSL2 backend
```

После установки откройте Docker Desktop и проверьте:

```text
Settings -> Resources -> WSL Integration
```

Включите интеграцию для Ubuntu.

---

## 3. Проверить поддержку Linux GUI

В Ubuntu/WSL выполните:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

Если открылось маленькое окно с глазами, значит WSLg GUI работает.

Если `xeyes` не открывается, сначала нужно исправить WSLg/GUI поддержку Windows.

---

## 4. Скачать Docker-архив приложения

Откройте страницу репозитория GitHub:

```text
GitHub repository -> Releases -> latest release
```

Скачайте файл:

```text
camac-signal-analyser-dev.tar.gz
```

Это готовый Docker image archive.

Этот файл **не хранится внутри Git commit history**. Он прикреплен к GitHub Release как downloadable asset.

---

## 5. Подготовить рабочую папку в Ubuntu/WSL

В Ubuntu/WSL выполните:

```bash
mkdir -p ~/camac_signal_analyser_run
cd ~/camac_signal_analyser_run
mkdir -p sample_data exports
```

Скопируйте скачанный архив в эту папку.

Например, если файл лежит в Windows Downloads:

```bash
cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/camac-signal-analyser-dev.tar.gz .
```

Замените:

```text
YOUR_WINDOWS_USERNAME
```

на имя пользователя Windows.

---

## 6. Загрузить Docker image

В Ubuntu/WSL:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Проверьте, что image появился:

```bash
docker images
```

Должно быть примерно так:

```text
REPOSITORY              TAG
camac-signal-analyser   dev
```

---

## 7. Добавить CAMAC архивы

Положите бинарные CAMAC архивы в папку:

```text
sample_data/
```

Пример:

```text
sample_data/example.001
sample_data/190723.001
```

---

## 8. Запустить приложение на Windows 11 через WSL

Выполните команду из Ubuntu/WSL:

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

Внутри приложения открывайте архивы из:

```text
/app/sample_data
```

Экспорт сохраняйте в:

```text
/app/exports
```

После экспорта файлы появятся на вашем компьютере в папке:

```text
exports/
```

Проверить можно так:

```bash
ls -lh exports
```

---

# Запуск на Windows 11 через сборку из исходников

Используйте этот способ, если хотите собрать Docker image самостоятельно.

В Ubuntu/WSL:

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Положите CAMAC архивы в:

```text
sample_data/
```

Запустите:

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

# Запуск на Linux / Ubuntu

Linux — самая простая платформа для Docker GUI приложения.

---

## 1. Сборка

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

Положите CAMAC архивы в:

```text
sample_data/
```

---

## 2. Запуск

Разрешите Docker контейнеру использовать X11 display:

```bash
xhost +local:docker
```

Запустите:

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

После закрытия приложения:

```bash
xhost -local:docker
```

---

## Linux: запуск из готового release archive

Если вы скачали:

```text
camac-signal-analyser-dev.tar.gz
```

загрузите image:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Создайте папки:

```bash
mkdir -p sample_data exports
```

Положите архивы в:

```text
sample_data/
```

И запустите приложение обычной Linux-командой выше.

---

# Запуск на macOS

На macOS нужен Docker Desktop и XQuartz.

GUI через XQuartz может работать медленнее, чем на Linux или Windows WSLg.

---

## 1. Установить зависимости

Нужно установить:

```text
Docker Desktop
XQuartz
```

Запустите XQuartz:

```bash
open -a XQuartz
```

В настройках XQuartz включите:

```text
Allow connections from network clients
```

После этого перезапустите XQuartz.

Разрешите локальные X11 соединения:

```bash
xhost + 127.0.0.1
```

---

## 2. Сборка на macOS

```bash
git clone <YOUR_REPOSITORY_URL>
cd camac_signal_analyser
mkdir -p sample_data exports
docker build -t camac-signal-analyser:dev .
```

---

## 3. Запуск на macOS

```bash
docker run --rm -it \
  --name camac-gui \
  -e DISPLAY=host.docker.internal:0 \
  -e QT_X11_NO_MITSHM=1 \
  -v "$PWD/sample_data:/app/sample_data:rw" \
  -v "$PWD/exports:/app/exports:rw" \
  camac-signal-analyser:dev
```

---

# Использование приложения

Основной workflow:

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
11. Файлы появятся на компьютере в папке exports/.
```

---

# Описание окон приложения

## Окно 1: Обрезка и накопленная энергия

Показывает накопленную энергию:

```text
АЭ / AE
ЭМЭ / EME
```

Поддерживает:

```text
CUT по номеру импульса
CUT по времени эксперимента
RESET
```

---

## Окно 2: Поимпульсный анализ

Показывает:

```text
форма сигнала АЭ
форма сигнала ЭМЭ
FFT АЭ
FFT ЭМЭ
сводная FFT по всем импульсам
энергия текущего импульса
мощность текущего импульса
максимальная амплитуда
RAW header preview
удаление текущего импульса
```

---

## Окно 3: Статистические коэффициенты

Показывает четыре графика:

```text
d-value
S-value
γ-value
Tsallis q
```

Режимы:

```text
1 сигнал за раз:
    d-value показывается как кривая по импульсам.
    S-value, γ-value и Tsallis q показываются как значения для текущего диапазона.

Скользящее окно:
    d-value, S-value, γ-value и Tsallis q считаются по окнам импульсов.
```

Тяжелые расчеты выполняются в background worker thread, поэтому GUI должен оставаться отзывчивым.

---

## Окно 4: Вейвлет-анализ

Показывает две скалограммы одновременно:

```text
вейвлет-скалограмма АЭ
вейвлет-скалограмма ЭМЭ
```

Режимы:

```text
Текущий импульс:
    полная time-frequency скалограмма выбранного импульса.

Все импульсы:
    сводные вейвлет-карты по текущему диапазону архива.
```

---

## Окно 5: Экспорт

Экспортирует:

```text
catalog CSV
текущий обработанный импульс CSV
текущий RAW импульс CSV
текущий диапазон в папку
матрицы обработанных сигналов AE и EME
b-value CSV
wavelet CSV
изображения графиков через контекстное меню
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

Значение:

```text
columns:
    импульсы / сигналы

first row:
    подписи импульсов

first column:
    подписи строк

experiment_time_seconds:
    время от начала эксперимента / архива

sample_0, sample_1, ...
    значения обработанного сигнала
```

После CUT/delete:

```text
event_1_original_50
```

означает:

```text
event_1:
    первый импульс в текущем обработанном диапазоне

original_50:
    исходный номер импульса в полном архиве
```

---

# Поддерживаемые форматы CAMAC

Приложение автоматически определяет поддерживаемый формат CAMAC архива.

Длина обработанного сигнала зависит от формата:

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

В экспорт обработанных матриц CAMAC metadata/header samples не попадают.

---

# Информация о GitHub Release archive

Готовый Docker image распространяется как GitHub Release asset.

Пример файла:

```text
camac-signal-analyser-dev.tar.gz
```

Этот файл **не нужно коммитить в Git**.

Его нужно загрузить сюда:

```text
GitHub repository -> Releases -> latest release -> Assets
```

Пользователи скачивают архив, загружают его в Docker и запускают приложение без самостоятельной сборки.

---

## Загрузка release archive в Docker

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

Проверить:

```bash
docker images
```

Ожидаемый image:

```text
camac-signal-analyser   dev
```

После этого приложение запускается обычной командой для вашей ОС.

---

# Инструкция для разработчика / maintainer

## Собрать Docker image

```bash
docker build -t camac-signal-analyser:dev .
```

---

## Проверить image на Linux

```bash
mkdir -p sample_data exports

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

## Сохранить image как compressed release archive

```bash
docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
```

Не коммитьте `.tar.gz` файл в Git.

Загрузите его как GitHub Release asset.

---

## Рекомендуемый release workflow

```text
1. Сделать commit и push исходного кода.
2. Собрать Docker image.
3. Проверить Docker image локально.
4. Сохранить image:
       docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
5. Открыть GitHub repository.
6. Открыть Releases.
7. Draft a new release.
8. Создать tag, например:
       v1.0.0
9. Загрузить:
       camac-signal-analyser-dev.tar.gz
10. Publish release.
```

---

# Локальный запуск без Docker

На Ubuntu можно запускать приложение локально.

Создать virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Собрать C++ parser:

```bash
cmake -S cpp_core -B cpp_core/build \
  -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR=$(python -m pybind11 --cmakedir)

cmake --build cpp_core/build -j$(nproc)
```

Запустить GUI:

```bash
PYTHONPATH=python_gui:cpp_core/build python3 python_gui/main.py
```

---

# Полезные Docker команды

Собрать image:

```bash
docker build -t camac-signal-analyser:dev .
```

Показать images:

```bash
docker images
```

Удалить image:

```bash
docker rmi camac-signal-analyser:dev
```

Запустить shell внутри image:

```bash
docker run --rm -it camac-signal-analyser:dev bash
```

Найти compiled CAMAC module внутри image:

```bash
docker run --rm -it camac-signal-analyser:dev bash
find /app -name "camac_core*.so"
```

Сохранить image:

```bash
docker save camac-signal-analyser:dev | gzip -9 > camac-signal-analyser-dev.tar.gz
```

Загрузить image:

```bash
gunzip -c camac-signal-analyser-dev.tar.gz | docker load
```

---

# Troubleshooting / Решение проблем

## Docker command says permission denied на Linux

Можно запустить через `sudo`:

```bash
sudo docker build -t camac-signal-analyser:dev .
```

Или добавить пользователя в Docker group:

```bash
sudo usermod -aG docker "$USER"
```

После этого нужно выйти из системы и зайти снова.

---

## GUI не открывается на Linux

Проверьте:

```bash
echo $DISPLAY
```

Разрешите Docker доступ к X11:

```bash
xhost +local:docker
```

Запустите контейнер снова.

---

## GUI не открывается на Windows

В Ubuntu/WSL проверьте:

```bash
sudo apt update
sudo apt install -y x11-apps
xeyes
```

Если `xeyes` не открывается, проблема в WSLg/Windows GUI support, а не в CAMAC приложении.

---

## GUI не открывается на macOS

Убедитесь, что XQuartz запущен:

```bash
open -a XQuartz
```

Включите:

```text
Allow connections from network clients
```

Перезапустите XQuartz.

Затем:

```bash
xhost + 127.0.0.1
```

Запустите Docker container снова.

---

## Архив не виден в file picker

Внутри Docker используйте:

```text
/app/sample_data
```

Не используйте обычный host path.

Пример:

```text
Host:
    ./sample_data/test.001

Inside application:
    /app/sample_data/test.001
```

---

## Экспортированные файлы не видны

Экспортируйте внутри GUI в:

```text
/app/exports
```

Потом проверьте на host:

```bash
ls -lh exports
```

---

## Ошибка import camac_core

Запустите shell внутри Docker image:

```bash
docker run --rm -it camac-signal-analyser:dev bash
```

Внутри контейнера:

```bash
find /app -name "camac_core*.so"
python -c "import camac_core; print(camac_core)"
```

Если `camac_core*.so` существует, но import не работает, проверьте `PYTHONPATH` в Dockerfile.

---

## Приложение работает медленно при тяжелых расчетах

Некоторые операции тяжелые:

```text
Window 3 statistics
Tsallis fitting
wavelet analysis for all impulses
large CSV exports
```

Рекомендация:

```text
Сначала используйте CUT, чтобы уменьшить текущий диапазон.
Потом запускайте тяжелые расчеты на выбранном диапазоне.
```

---

# Примечания

Это desktop GUI приложение, запущенное через Docker.

Docker делает Python/C++ окружение воспроизводимым, но GUI forwarding зависит от операционной системы.

Лучше всего поддерживается:

```text
Linux / Ubuntu
```

Основной рекомендуемый вариант для пользователей:

```text
Windows 11 + WSL2 + WSLg + Docker Desktop
```

Возможно на macOS:

```text
Docker Desktop + XQuartz
```
