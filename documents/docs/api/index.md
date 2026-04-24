# CLI HTTP API 文档

## 概述

小智 AI 客户端的 CLI 模式内嵌了一个 HTTP API 服务，使外部 UI（Web 前端、桌面应用、移动端等）能够通过 HTTP 接口与小智 AI 进行交互。

该服务以插件形式（`HttpApiPlugin`）集成到现有的 PluginManager 体系中，随 CLI 模式自动启动和关闭，基于 `aiohttp` 实现。

### 功能一览

- **状态查询** — 获取设备当前状态、聊天消息、表情等信息
- **实时事件推送** — 通过 SSE（Server-Sent Events）接收状态变化、文本更新、表情变化
- **控制指令** — 开始/中止对话、发送文本、手动录音控制

### 默认配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `HTTP_API_OPTIONS.HOST` | `0.0.0.0` | 监听地址 |
| `HTTP_API_OPTIONS.PORT` | `8000` | 监听端口 |

在 `config.json` 中可自定义：

```json
{
  "HTTP_API_OPTIONS": {
    "HOST": "0.0.0.0",
    "PORT": 8000
  }
}
```

::: tip
HTTP API 仅在 CLI 模式下启动，GUI 模式不会加载该插件。
:::

---

## 统一响应格式

所有 API 响应均使用统一的 JSON 结构。

**成功响应：**

```json
{
  "success": true,
  "data": { ... }
}
```

**错误响应：**

```json
{
  "success": false,
  "error": "错误描述"
}
```

---

## API 端点

### GET /api/status

获取小智 AI 的当前状态快照。

**请求示例：**

```bash
curl http://localhost:8000/api/status
```

**响应示例：**

```json
{
  "success": true,
  "data": {
    "device_state": "idle",
    "listening_mode": "realtime",
    "keep_listening": false,
    "audio_opened": false,
    "chat_message": "你好，有什么可以帮你的？",
    "emotion": "neutral"
  }
}
```

**字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_state` | string | 设备状态：`idle`、`listening`、`speaking` |
| `listening_mode` | string | 监听模式 |
| `keep_listening` | boolean | 是否保持监听 |
| `audio_opened` | boolean | 音频是否已打开 |
| `chat_message` | string | 最新的聊天消息文本 |
| `emotion` | string | 当前表情状态，如 `neutral`、`happy`、`sad` 等 |

---

### GET /api/events

建立 SSE（Server-Sent Events）连接，接收实时事件推送。

**请求示例：**

```bash
curl -N http://localhost:8000/api/events
```

**事件类型：**

#### state_changed

设备状态发生变化时推送。

```
event: state_changed
data: {"device_state": "listening"}
```

#### text_updated

收到 TTS 或 STT 文本消息时推送。

```
event: text_updated
data: {"role": "assistant", "text": "你好"}
```

| 字段 | 说明 |
|------|------|
| `role` | 消息角色：`user` 或 `assistant` |
| `text` | 消息文本内容 |

#### emotion_changed

表情发生变化时推送。

```
event: emotion_changed
data: {"emotion": "happy"}
```

::: info
SSE 支持多个客户端同时连接，每个客户端独立接收事件。所有事件的 `data` 字段均为 JSON 字符串。
:::

---

### POST /api/action/start-conversation

开始自动对话。

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/action/start-conversation \
  -H "Content-Type: application/json"
```

**响应示例：**

```json
{
  "success": true,
  "data": null
}
```

---

### POST /api/action/abort-speaking

中止当前语音输出。

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/action/abort-speaking \
  -H "Content-Type: application/json"
```

**响应示例：**

```json
{
  "success": true,
  "data": null
}
```

---

### POST /api/action/send-text

向小智 AI 发送文本消息。

**请求体：**

```json
{
  "text": "你好小智"
}
```

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/action/send-text \
  -H "Content-Type: application/json" \
  -d '{"text": "你好小智"}'
```

**响应示例：**

```json
{
  "success": true,
  "data": null
}
```

**错误情况：**

缺少 `text` 字段或 `text` 为空/纯空白时返回 400：

```json
{
  "success": false,
  "error": "text 字段不能为空"
}
```

---

### POST /api/action/start-listening

开始手动录音（按住说话模式）。

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/action/start-listening \
  -H "Content-Type: application/json"
```

**响应示例：**

```json
{
  "success": true,
  "data": null
}
```

---

### POST /api/action/stop-listening

停止手动录音。

**请求示例：**

```bash
curl -X POST http://localhost:8000/api/action/stop-listening \
  -H "Content-Type: application/json"
```

**响应示例：**

```json
{
  "success": true,
  "data": null
}
```

---

## 错误处理

| HTTP 状态码 | 场景 | 说明 |
|-------------|------|------|
| 400 | 请求体缺少必要字段 / Content-Type 不是 `application/json` | 客户端请求错误 |
| 404 | 请求路径未匹配任何 API 端点 | 路径不存在 |
| 500 | 服务端内部异常 | 服务会记录错误日志并继续运行 |

所有错误响应均使用统一格式：

```json
{
  "success": false,
  "error": "错误描述"
}
```

---

## CORS 支持

所有 API 响应均包含以下 CORS 头，允许跨域访问：

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

---

## 快速集成示例

### JavaScript（浏览器）

```javascript
// 获取状态
const res = await fetch('http://localhost:8000/api/status')
const { data } = await res.json()
console.log(data.device_state)

// 监听 SSE 事件
const events = new EventSource('http://localhost:8000/api/events')

events.addEventListener('state_changed', (e) => {
  const data = JSON.parse(e.data)
  console.log('状态变化:', data.device_state)
})

events.addEventListener('text_updated', (e) => {
  const data = JSON.parse(e.data)
  console.log(`${data.role}: ${data.text}`)
})

events.addEventListener('emotion_changed', (e) => {
  const data = JSON.parse(e.data)
  console.log('表情:', data.emotion)
})

// 发送文本
await fetch('http://localhost:8000/api/action/send-text', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ text: '今天天气怎么样？' })
})
```

### Python

```python
import requests
import sseclient

# 获取状态
resp = requests.get('http://localhost:8000/api/status')
print(resp.json()['data']['device_state'])

# 监听 SSE 事件
resp = requests.get('http://localhost:8000/api/events', stream=True)
client = sseclient.SSEClient(resp)
for event in client.events():
    print(f'{event.event}: {event.data}')

# 发送文本
requests.post(
    'http://localhost:8000/api/action/send-text',
    json={'text': '你好小智'}
)
```
