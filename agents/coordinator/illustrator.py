from __future__ import annotations

from google.adk import Agent

from agents.coordinator.illustrator_prompts import IMAGE_PROMPT_FORMAT

STATE_ILLUSTRATOR_PROMPT = "illustrator_prompt"

ILLUSTRATOR_PROMPT_AGENT_MODEL = "gemini-3.1-pro-preview"
ILLUSTRATOR_AGENT_MODEL = "gemini-3-pro-image"
STATE_ILLUSTRATOR_PROMPT = "illustrator_prompt"

ILLUSTRATOR_PROMPT_AGENT_MODEL = "gemini-3.1-pro-preview"
ILLUSTRATOR_AGENT_MODEL = "gemini-3-pro-image"

illustrator_prompt_agent = Agent(
    name="illustrator_prompt_writer",
    model=ILLUSTRATOR_PROMPT_AGENT_MODEL,
    description="plannerの旅程markdownから表紙画像生成用promptを作る。",
    instruction=(
        "入力: 旅行旅程\n"
        "出力: 1枚の旅行しおり画像を生成するための英語のprompt\n"
        "- 画像生成プロンプト以外を出力するのは禁止です\n"
        "- 入力された旅程情報を全て配置してください。省略は禁止です\n"
        "- この画像を見るだけで旅程と全く同じ旅行ができることが目標です\n"
        "- 画像のスタイルはこれをそのまま貼ってください: "
        "'flat 2D cel-shaded anime illustration, hand-drawn line art, crisp black outlines, "
        "minimal gradients, no realistic skin texture, no 3D rendering, "
        "no photorealistic lighting, no glossy highlights, no cinematic color grading'"
        f"- プロンプトは以下のフォーマット例に従ってください\n{IMAGE_PROMPT_FORMAT}"
    ),
    mode="single_turn",
)

illustrator_agent = Agent(
    name="illustrator",
    model=ILLUSTRATOR_AGENT_MODEL,
    description="旅しおりの表紙画像を生成する。",
    instruction="旅しおり画像を生成してください",
    mode="single_turn",
)