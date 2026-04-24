# ============================================================
# py-xiaozhi Docker 镜像 (CLI 模式, 轻量版)
# 构建: docker build -t py-xiaozhi .
# 使用清华镜像加速: docker build --build-arg USE_MIRROR=true -t py-xiaozhi .
# 运行 (ALSA): docker run -it --rm \
#         -v ./config:/app/config \
#         -v ./models:/app/models \
#         --device /dev/snd \
#         py-xiaozhi
# 运行 (PulseAudio): docker run -it --rm \
#         -v ./config:/app/config \
#         -v ./models:/app/models \
#         -e PULSE_SERVER=tcp:host.docker.internal \
#         py-xiaozhi
# ============================================================

FROM python:3.12-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

ARG USE_MIRROR=false

# 配置 apt 清华镜像源 (可选)
RUN if [ "$USE_MIRROR" = "true" ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
        && sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    fi

# 安装构建依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        portaudio19-dev \
        libopus-dev \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY requirements.txt .

# 过滤掉 GUI 相关包 + Windows 专用包，生成 CLI 专用依赖
# 放宽 sherpa-onnx 版本以匹配 Python 3.12 可用 wheel
RUN grep -viE '^(PyQt5|qasync|pyinstaller|comtypes|pycaw|pywin32)' requirements.txt \
    | sed 's/sherpa-onnx==.*/sherpa-onnx>=1.12.26/' \
    > requirements_cli.txt

# 配置 pip 镜像源 (可选) + 安装依赖到独立目录
RUN if [ "$USE_MIRROR" = "true" ]; then \
        pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple; \
    fi \
    && pip install --no-cache-dir \
        --target=/build/deps \
        -r requirements_cli.txt

# ============================================================
# 运行阶段
# ============================================================
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

ARG USE_MIRROR=false

RUN if [ "$USE_MIRROR" = "true" ]; then \
        sed -i 's|deb.debian.org|mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources \
        && sed -i 's|security.debian.org/debian-security|mirrors.tuna.tsinghua.edu.cn/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    fi

# 安装运行时系统依赖
# libasound2-plugins: 提供 ALSA PulseAudio 插件，使 PortAudio 通过 ALSA 访问 PulseAudio 设备
RUN apt-get update && apt-get install -y --no-install-recommends \
        libportaudio2 \
        libopus0 \
        ffmpeg \
        alsa-utils \
        libasound2-plugins \
        pulseaudio-utils \
        libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从 builder 复制 Python 依赖
COPY --from=builder /build/deps /usr/local/lib/python3.12/site-packages/

# 复制项目文件
COPY main.py .
COPY src/ src/
COPY libs/ libs/
COPY assets/ assets/
COPY scripts/ scripts/

# 创建运行时目录
RUN mkdir -p /app/config /app/logs /app/cache /app/models

# 模型文件通过挂载本地目录提供，不再打包进镜像，以减小构建体积
# 请在宿主机准备好模型目录后，运行时通过 -v 挂载到 /app/models

VOLUME ["/app/config", "/app/models"]

ENTRYPOINT ["python", "main.py", "--mode", "cli"]
CMD ["--protocol", "websocket"]
