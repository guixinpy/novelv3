"""Provider 工厂（v1 绞杀：统一 LLM 调用路径的公共入口）。

所有内部 LLM 调用（v2 会话、athena 聊天、一致性 L2、章节修订/v2 动作）
都从这里构建 provider，确保只有一条 DeepSeek HTTP 客户端路径。

注：DeepSeekProvider 实现已迁入新内核 core/providers/deepseek.py
（arch-refactor 阶段 1），此处 re-export 保持旧调用方兼容。
"""
from __future__ import annotations

from core.providers.deepseek import DeepSeekProvider
from app.config import load_api_key


def build_provider() -> DeepSeekProvider:
    key = load_api_key()
    if not key:
        raise ValueError("DeepSeek API key 未配置")
    return DeepSeekProvider(api_key=key)
