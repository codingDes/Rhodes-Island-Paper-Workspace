"""
历史说明：早期版本把完整问答写入 agent_memory.json，与前端 history 重复且体积膨胀。

当前策略：
- 对话上下文仅使用请求体中的 history，并在 chat_service 内做条数/字数截断，减少 token。
- 干员长期设定请使用 data/lore/ 与 /api/lore 接口维护，由 lore_service 注入 system prompt。
"""

from __future__ import annotations
