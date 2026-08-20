"""MCP server exposing Xiaomi MiMo-V2.5 image understanding to text-only LLMs.

Run with stdio transport:

    python -m mimo_vision_mcp.server
    # or after `pip install -e .`:
    mimo-vision-mcp
"""

import json

from mcp.server.fastmcp import FastMCP

from . import config
from .providers import call_vision

mcp = FastMCP("mimo-vision")

DESCRIBE_PROMPT = "请详细描述这张图片的内容，包括主体、场景、细节与氛围。"
OCR_PROMPT = "请提取图片中的所有文字内容，尽量逐字输出，并保留原有排版顺序。"


def _run(images: list[str], prompt: str, detail: str | None = None) -> str:
    payload = call_vision(
        images,
        prompt,
        detail,
        provider=config.get_provider(),
        model=config.get_model(),
    )
    return json.dumps(payload, ensure_ascii=False)


@mcp.tool()
def analyze_image(images: list[str], prompt: str, detail: str | None = None) -> str:
    """分析图片内容并回答你的问题（基于视觉模型）。

    当用户要求"看图片/描述图片/识别图中内容/截图分析"，或对话中出现本地图片路径、
    图片 URL 或 base64 图片数据时，主动调用本工具。

    Args:
        images: 图片列表，每项可以是：
            - 本地绝对路径，如 "C:/Users/xx/Pictures/a.png"
            - 公网 URL，如 "https://example.com/a.jpg"
            - base64 data URI，如 "data:image/png;base64,...."
            - 纯 base64 字符串
        prompt: 对图片提出的问题或指令，如 "这张图里有什么动物？"
        detail: 可选，图片采样精细度，取 "low" / "high" / "auto"
    """
    return _run(images, prompt, detail)


@mcp.tool()
def describe_image(images: list[str], detail: str | None = None) -> str:
    """详细描述图片内容（基于视觉模型）。

    当用户要求"描述/介绍一下这张图、看到什么"时调用。输入约定同 analyze_image。
    """
    return _run(images, DESCRIBE_PROMPT, detail)


@mcp.tool()
def extract_text_from_image(images: list[str], detail: str | None = None) -> str:
    """提取图片中的文字（OCR，基于视觉模型）。

    当用户要求"识别/提取图中文字、截图里的文本"时调用。输入约定同 analyze_image。
    """
    return _run(images, OCR_PROMPT, detail)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
