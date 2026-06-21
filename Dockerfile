FROM python:3.11-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV QT_X11_NO_MITSHM=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    git \
    pkg-config \
    libgl1 \
    libegl1 \
    libopengl0 \
    libdbus-1-3 \
    libfontconfig1 \
    libfreetype6 \
    libglib2.0-0 \
    libsm6 \
    libice6 \
    libx11-xcb1 \
    libxext6 \
    libxrender1 \
    libxcb1 \
    libxcb-cursor0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-shm0 \
    libxcb-xfixes0 \
    libxcb-xinerama0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN cmake -S cpp_core -B cpp_core/build \
    -DCMAKE_BUILD_TYPE=Release \
    -Dpybind11_DIR=$(python -m pybind11 --cmakedir) \
    && cmake --build cpp_core/build -j$(nproc)

ENV PYTHONPATH=/app/python_gui:/app/cpp_core/build

CMD ["python", "python_gui/main.py"]
