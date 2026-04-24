# Docker 部署指南

## 前置要求

- Docker 20.10+
- 宿主机具备音频设备（麦克风 + 扬声器）

## 快速开始

### 1. 构建镜像

```bash
docker build -t py-xiaozhi .
```

国内网络环境推荐使用清华镜像源加速（apt + pip 同时加速）：

```bash
docker build --build-arg USE_MIRROR=true -t py-xiaozhi .
```

### 2. 准备配置与模型

首次运行前，在项目根目录创建 `config` 和 `models` 目录：

```bash
mkdir -p config models
```

> 如果没有配置文件，应用首次启动时会引导你完成设备激活流程。

#### 下载模型文件

模型文件不再打包进镜像，需要在宿主机上提前准备好，运行时通过挂载目录提供给容器。

以 Sherpa-ONNX 唤醒词模型为例：

```bash
KWS_MODEL=sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01

wget https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/${KWS_MODEL}.tar.bz2
tar xjf ${KWS_MODEL}.tar.bz2

cp ${KWS_MODEL}/encoder-epoch-99-avg-1-chunk-16-left-64.int8.onnx models/encoder.onnx
cp ${KWS_MODEL}/decoder-epoch-99-avg-1-chunk-16-left-64.onnx      models/decoder.onnx
cp ${KWS_MODEL}/joiner-epoch-99-avg-1-chunk-16-left-64.int8.onnx  models/joiner.onnx
cp ${KWS_MODEL}/tokens.txt   models/tokens.txt
cp ${KWS_MODEL}/keywords.txt models/keywords.txt

# 清理下载文件
rm -rf ${KWS_MODEL}.tar.bz2 ${KWS_MODEL}
```

最终 `models` 目录结构如下：

```
models/
├── encoder.onnx
├── decoder.onnx
├── joiner.onnx
├── tokens.txt
└── keywords.txt
```

### 3. 启动容器

```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./models:/app/models \
  --device /dev/snd \
  py-xiaozhi
```

## 运行参数

镜像默认以 `--mode cli --protocol websocket` 启动。

| 参数 | 可选值 | 说明 |
|------|--------|------|
| `--protocol` | `websocket`（默认）/ `mqtt` | 通信协议 |
| `--skip-activation` | — | 跳过设备激活（调试用） |

示例：使用 MQTT 协议

```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./models:/app/models \
  --device /dev/snd \
  py-xiaozhi --protocol mqtt
```

## 音频配置

容器需要访问宿主机音频设备，根据你的音频系统选择对应方案。

### 方案一：ALSA 直通（最简单）

```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./models:/app/models \
  --device /dev/snd \
  py-xiaozhi
```

### 方案二：PulseAudio

适用于大多数桌面 Linux 发行版：

```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./models:/app/models \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  py-xiaozhi
```

### 方案三：PipeWire

Ubuntu 22.04+ 等默认使用 PipeWire 的系统，PulseAudio 兼容层同样适用：

```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./models:/app/models \
  -v /run/user/$(id -u)/pulse:/run/user/1000/pulse \
  -e PULSE_SERVER=unix:/run/user/1000/pulse/native \
  py-xiaozhi
```

> PipeWire 通过 `pipewire-pulse` 提供 PulseAudio 兼容接口，命令与方案二相同。

## 数据持久化

| 容器路径 | 说明 | 建议 |
|----------|------|------|
| `/app/config` | 配置文件 | 必须挂载 |
| `/app/models` | 唤醒词模型文件 | 必须挂载 |
| `/app/logs` | 运行日志 | 按需挂载 |
| `/app/cache` | 音乐缓存等 | 按需挂载 |

完整挂载示例：

```bash
docker run -it --rm \
  -v ./config:/app/config \
  -v ./logs:/app/logs \
  -v ./cache:/app/cache \
  -v ./models:/app/models \
  --device /dev/snd \
  py-xiaozhi
```

## Docker Compose

创建 `docker-compose.yml`：

```yaml
services:
  xiaozhi:
    build: .
    image: py-xiaozhi
    container_name: py-xiaozhi
    stdin_open: true
    tty: true
    restart: unless-stopped
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - ./config:/app/config
      - ./models:/app/models
      - ./logs:/app/logs
      - ./cache:/app/cache
```

启动：

```bash
docker compose up -d
```

查看日志：

```bash
docker compose logs -f xiaozhi
```

交互操作：

```bash
docker attach py-xiaozhi
```

> 按 `Ctrl+P` `Ctrl+Q` 可退出 attach 而不停止容器。

## 常见问题

### 音频设备无法访问

确认宿主机音频设备存在：

```bash
ls -la /dev/snd/
```

如果使用 PulseAudio，确认 socket 存在：

```bash
ls /run/user/$(id -u)/pulse/native
```

### 权限不足

将当前用户加入 `audio` 和 `docker` 组：

```bash
sudo usermod -aG audio,docker $USER
# 重新登录后生效
```

### 容器内无声音

进入容器检查音频设备：

```bash
docker exec -it py-xiaozhi bash
aplay -l        # 列出播放设备
arecord -l      # 列出录音设备
```

### 构建失败：PyQt5 相关错误

Docker 镜像仅支持 CLI 模式，PyQt5 构建失败不影响使用。如果构建过程中出现 PyQt5 相关警告可以忽略。

### 网络问题导致构建慢

使用清华镜像源加速（apt + pip 一键加速）：

```bash
docker build --build-arg USE_MIRROR=true -t py-xiaozhi .
```
