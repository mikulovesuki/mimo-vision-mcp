# Mimo Vision MCP 使用说明

本项目的 `mimo-vision` MCP server 通过视觉模型（如 MiMo-V2.5）提供图像理解能力。

## 是否调用（重要）

- 如果你（当前模型）**本身支持图像输入（多模态）**：用户给的图片可直接作为图像输入理解，
  **不要**调用 mimo-vision 工具。
- 如果你**不支持图像输入（纯文本模型）**：遇到以下情况时**主动调用** mimo-vision 工具：
  - 用户说"看/描述/分析/识别这张图、这个截图、这个图片"
  - 对话中出现图片的**本地路径**（如 `C:\Users\xx\Pictures\a.png`）、**URL** 或 base64 数据
  - 用户要求识别图片中的文字（OCR）
  - 用户给出多张图片要求对比、分析

## 可用工具

- `analyze_image(images, prompt)` — 通用图片问答，可多图
- `describe_image(images)` — 详细描述图片内容
- `extract_text_from_image(images)` — 提取图中文字（OCR）

`images` 列表元素支持：本地绝对路径 / http(s) URL / base64 data URI。

## 注意

- 本地路径必须可被本 MCP 进程访问（同一台机器）
- 调用后把返回的 `result` 字段内容转述给用户即可
- 若返回 `error` 字段，说明图片输入非法或 API 未配置，请据此提示用户
