from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.models.schemas import SummaryResponse
from app.services.llm_service import chat_json


def _fallback_summary(doc_id: str, text: str, llm_error: str | None = None) -> SummaryResponse:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    title_candidate = lines[0][:120] if lines else "Untitled Document"
    short = text[:500]
    return SummaryResponse(
        doc_id=doc_id,
        source="fallback",
        title_candidate=title_candidate,
        topic="待模型识别（当前为本地降级总结）",
        research_question="请配置 OPENAI 兼容 API 后生成高质量总结。",
        core_method="当前仅返回模板化内容。",
        innovations=["待模型生成"],
        experiment_results=short or "无可用文本。",
        limitations="当前未调用远程模型。",
        plain_explanation="这是一个本地降级总结，用于保证流程可演示。",
        llm_error=llm_error,
    )


def generate_structured_summary(doc_id: str) -> SummaryResponse:
    settings = Settings.load()
    text_path = Path(settings.docs_dir) / f"{doc_id}.txt"
    if not text_path.exists():
        raise FileNotFoundError(f"Parsed text not found for doc_id={doc_id}")

    text = text_path.read_text(encoding="utf-8", errors="ignore").strip()
    if not text:
        raise ValueError("Document text is empty.")

    title_candidate = next((ln.strip() for ln in text.splitlines() if ln.strip()), "Untitled Document")[:120]
    prompt_text = text[:12000]

    system_prompt = (
        "你是学术阅读助手。必须使用简体中文回答。"
        "请严格基于用户提供论文文本，总结为 JSON。"
        "若文本证据不足，要明确写“文本中未明确给出”。"
        "总结要具体，不要过短，每个字段尽量给出可解释细节。"
    )
    user_prompt = f"""
请阅读下面论文文本，输出 JSON，字段必须完整：
{{
  "topic": "string",
  "research_question": "string",
  "core_method": "string",
  "innovations": ["string", "string"],
  "experiment_results": "string",
  "limitations": "string",
  "plain_explanation": "string"
}}

论文文本：
{prompt_text}
"""
    try:
        data = chat_json(system_prompt=system_prompt, user_prompt=user_prompt)
        return SummaryResponse(
            doc_id=doc_id,
            source="llm",
            title_candidate=title_candidate,
            topic=str(data.get("topic", "文本中未明确给出")),
            research_question=str(data.get("research_question", "文本中未明确给出")),
            core_method=str(data.get("core_method", "文本中未明确给出")),
            innovations=[str(x) for x in (data.get("innovations") or ["文本中未明确给出"])],
            experiment_results=str(data.get("experiment_results", "文本中未明确给出")),
            limitations=str(data.get("limitations", "文本中未明确给出")),
            plain_explanation=str(data.get("plain_explanation", "文本中未明确给出")),
        )
    except Exception as exc:
        return _fallback_summary(doc_id=doc_id, text=text, llm_error=str(exc))

