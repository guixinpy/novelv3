"""会话转录（append-only JSONL + compaction 检查点 + 前向兼容）。

吸收点：
- append-only 事件日志 + compaction 记录（openhuman #7）：历史压缩不丢原始行，
  压缩记录是此后消息状态的真相源（与旧版一致的检查点语义）
- api_content sidecar（hermes #5）：持久化存干净内容，API 发送存精确字节（含临时注入），
  注入内容永不污染存储
- 幂等键（openclaw #5）：user 消息重复投递安全
- parent_id 预留（openclaw #6）：章节分叉/回滚的持久化基础（本次只落字段）
- 前向兼容（openhuman）：未知字段/未知记录跳过，存档格式演进零成本
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TranscriptRecord:
    """一条转录记录（消息或压缩检查点）。"""

    type: str  # "message" | "compaction"
    data: dict
    _extra: dict | None = None


def strip_api_fields(message: dict) -> dict:
    """剥离发送专用字段（api_content 等），得到持久化形态。"""
    return {k: v for k, v in message.items() if k not in ("api_content",)}


def with_api_content(message: dict, api_content: str) -> dict:
    """附加精确发送字节（sidecar），发送前组装、持久化时剥离。"""
    out = dict(message)
    out["api_content"] = api_content
    return out


class Transcript:
    """会话转录：append-only 追加 + compaction 检查点替换累积器。

    线程不安全；单会话单消费者（写锁由上层持有）。
    """

    def __init__(self, log_path: Path) -> None:
        self.log_path = log_path
        self.messages: list[dict] = self._load()

    def _load(self) -> list[dict]:
        if not self.log_path.exists():
            return []
        messages: list[dict] = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") == "message":
                messages.append(entry["data"])
            elif entry.get("type") == "compaction":
                # 压缩快照是此后消息状态的真相源（append-only 日志中的检查点）
                messages = list(entry["data"]["messages"][1:])
            # 未知 type：跳过（前向兼容，openhuman 同款）
        return messages

    def append_message(self, message: dict) -> None:
        self._append_log("message", message)
        self.messages.append(message)

    def append_messages(self, messages: list[dict]) -> None:
        for message in messages:
            self._append_log("message", message)
        self.messages.extend(messages)

    def record_compaction(self, compressed: list[dict], summary: str) -> None:
        self._append_log("compaction", {"messages": compressed, "summary": summary})
        self.messages = list(compressed[1:])

    def _append_log(self, entry_type: str, data: dict) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"type": entry_type, "data": data}, ensure_ascii=False) + "\n")
