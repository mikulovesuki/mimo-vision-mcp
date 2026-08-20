# mimo-vision-mcp

> Give text-only LLMs vision capability through MCP, powered by vision models like Xiaomi MiMo-V2.5.

通过 **MCP（Model Context Protocol）**，把视觉模型（如小米 **MiMo-V2.5**）的图像理解能力暴露给**不具备多模态能力的文本 LLM**。文本模型遇到图片/截图/图片路径时，可主动调用 `analyze_image`、`describe_image`、`extract_text_from_image` 等工具获得视觉能力。

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
[![CI](https://github.com/mikulovesuki/mimo-vision-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/mikulovesuki/mimo-vision-mcp/actions/workflows/ci.yml)

## 原理

文本模型负责"调度"，视觉模型负责"看"，MCP 是把两者接起来的接口——**图片数据本身不经过文本模型**。

```
用户给图片路径/URL
  → ① 文本 LLM 根据工具列表 + 调用指引，决定调用 analyze_image
  → ② opencode / 任意 MCP 客户端（stdio）
  → ③ mimo-vision MCP server（图片归一化 + 转发请求）
  → ④ 视觉模型（MiMo-V2.5 等，经 OpenCode Go / 自定义供应商）真正"看"图
  → ⑤ 文本结果原路返回，文本模型转述给用户
```

## 特性

- 基于 OpenAI 兼容协议，默认接入 **OpenCode Go**，也可切换小米官方 / 任意自定义供应商
- stdio 本地传输，可接入 opencode / Claude Desktop / Cursor 等任意 MCP 客户端
- 图片输入灵活：**本地路径 / http(s) URL / base64 data URI / 纯 base64** 均可
- 支持多图输入、图片格式自动识别（JPEG/PNG/GIF/WebP/BMP）、50MB 限制校验
- 自动按模型选择 API 协议：`gpt-*`/`grok-*` 走 Responses API，其余走 chat/completions（可强制指定）
- 可选 **WebUI**：可视化配置面板 + 预览测试，选择即同步到 CLI，无需重启
- 无 API key 时返回友好错误提示，不会崩溃

## 目录结构

```
mimo-vision-mcp/
├── mimo_vision_mcp/
│   ├── config.py           # 配置读取（.env 实时重读）+ 应用到 MCP
│   ├── image_loader.py     # 图片输入归一化 + MIME 探测
│   ├── providers.py        # 供应商注册表 + call_vision（chat/responses 适配）
│   └── server.py           # FastMCP server + 3 个工具
├── webui/                  # 可选 WebUI（FastAPI + 单页 HTML）
├── tests/                  # 单元测试
├── .github/workflows/ci.yml
├── opencode.example.json   # opencode 接入配置示例
├── AGENTS.md               # 文本模型的调用指引
├── LICENSE
└── pyproject.toml
```

## 安装

```bash
python -m venv .venv
# Windows: .\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.venv/bin/python -m pip install -e ".[dev]"
```

## 配置 API Key

本项目默认走 **OpenCode Go** 套餐调用 MiMo-V2.5（模型 `mimo-v2.5`，OpenAI 兼容端点 `https://opencode.ai/zen/go/v1`）。

1. 在 [opencode.ai/auth](https://opencode.ai/auth) 订阅 Go，复制 API Key
2. 将 `.env.example` 复制为 `.env` 并填写：
   ```
   MIMO_API_KEY=你的-opencode-go-key
   ```

也可通过环境变量覆盖（`config.py` 每次调用实时重读 `.env`）：

| 变量 | 说明 | 默认值 |
| --- | --- | --- |
| `MIMO_API_KEY` | API Key（也可用 `OPENAI_API_KEY`） | 空 |
| `MIMO_PROVIDER` | 供应商 ID | `opencode-go` |
| `MIMO_MODEL` | 视觉模型 ID | `mimo-v2.5` |
| `MIMO_BASE_URL` | OpenAI 兼容端点 | `https://opencode.ai/zen/go/v1` |
| `MIMO_API_STYLE` | `chat` / `responses`（空则自动） | 自动 |
| `MIMO_MAX_TOKENS` | 单次输出上限 | `4096` |
| `MIMO_TIMEOUT` | 请求超时（秒） | `120` |

> 切换视觉模型：OpenCode Go 里更快的多模态模型可把 `MIMO_MODEL` 改成 `gpt-5.6-luna`（走 `/responses`）或 `minimax-m3`。注意 `mimo-v2.5-pro` 是**纯文本**模型，不能看图。

## 运行 MCP server

```bash
# 方式一：控制台脚本
mimo-vision-mcp
# 方式二：模块运行
python -m mimo_vision_mcp.server
```

## 接入 opencode

参考 `opencode.example.json` 把 `mimo-vision` 注册为本地 stdio MCP server：

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "mimo-vision": {
      "type": "local",
      "command": ["<你的python路径>", "-m", "mimo_vision_mcp.server"],
      "enabled": true,
      "environment": { "MIMO_API_KEY": "{env:MIMO_API_KEY}" }
    }
  },
  "experimental": { "mcp_timeout": 120000 }
}
```

> **注意**：`experimental.mcp_timeout`（默认 30s）控制 MCP 工具调用超时。视觉请求可能耗时几十秒，需调到 120s 以上；**不要**在 `mcp.mimo-vision` 里单独设置 `timeout`，它会覆盖 `mcp_timeout` 并导致超时。配置改动后需**重启 opencode** 生效。

本项目还附带 `AGENTS.md`（文本模型的调用指引），可通过全局配置 `"instructions": ["<路径>/AGENTS.md"]` 注入每个会话，让纯文本模型遇到图片时主动调用工具。

## 工具说明

| 工具 | 说明 |
| --- | --- |
| `analyze_image(images, prompt, detail?)` | 通用图片问答，可多图 |
| `describe_image(images, detail?)` | 详细描述图片内容 |
| `extract_text_from_image(images, detail?)` | 提取图中文字（OCR） |

`images` 每项支持：

- 本地绝对路径：`C:/Users/xx/Pictures/a.png`
- 公网 URL：`https://example.com/a.jpg`
- base64 data URI：`data:image/png;base64,....`
- 纯 base64 字符串

返回 JSON：`{ "result": "...", "error": "", "model": "...", "usage": {...} }`

## WebUI（交互式前端）

可选的**可视化配置面板**，供人上传图片、自由切换供应商/模型，并**把选择同步到 CLI 的 MCP**。

```bash
# Windows 一键启动：双击 启动WebUI.bat 或 start-webui.bat
# 手动启动：
python -m pip install -e ".[web]"
python -m webui.app
# 打开 http://127.0.0.1:8000 （端口可用 MIMO_WEBUI_PORT 修改）
```

- 顶部「CLI / MCP 当前生效模型」显示命令行 LLM 实际使用的供应商/模型/风格
- 选好模型后点**「应用到 CLI（同步到 MCP）」**，配置写入 `.env`，**无需重启**，CLI 下次调用即用新模型
- 下方「预览测试（不影响 CLI）」用于先试效果
- API Key 存于浏览器 localStorage；「应用到 CLI」时可一并写入 `.env`

## 测试

```bash
python -m pytest -q
```

## 常见问题

- **返回"未配置 API Key"**：在 `.env` 配置 `MIMO_API_KEY` 后重启客户端
- **图片格式不支持**：仅支持 JPEG/PNG/GIF/WebP/BMP
- **base64 输入报"无法解析"**：确认输入为合法 base64，且格式在支持范围内
- **MCP 工具调用超时**：将 `experimental.mcp_timeout` 调到 120000ms 以上

## 许可证

[MIT](LICENSE)

## 参考

- [OpenCode Go 文档](https://opencode.ai/docs/go/)
- [Xiaomi MiMo API 文档](https://mimo.mi.com/docs/zh-CN/quick-start/summary/first-api-call)
- [图片理解指南](https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/multimodal-understanding/image-understanding)
