#!/usr/bin/env python3
"""Generate a mock DeerFlow ultra-mode snapshot for the restaurant agent team scenario.

This script produces:
  - tests/snapshots/ultra_restaurant_agent_team.ndjson
  - tests/snapshots/ultra_restaurant_agent_team.meta.json

The snapshot mimics real DeerFlow raw event structure so QA agents can write
regression tests against it. When a valid API key becomes available, replace
this mock with a real recording script that calls DeerFlowRuntimeAdapter.
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path


def _make_event(type_: str, **kwargs) -> dict:
    return {"type": type_, **kwargs}


def generate_snapshot() -> tuple[list[dict], str]:
    """Return raw DeerFlow events and the expected final response text."""

    msg_id_1 = str(uuid.uuid4())
    msg_id_2 = str(uuid.uuid4())
    msg_id_3 = str(uuid.uuid4())
    msg_id_4 = str(uuid.uuid4())
    msg_id_5 = str(uuid.uuid4())

    call_id_customer = f"call-{uuid.uuid4().hex[:8]}"
    call_id_chef = f"call-{uuid.uuid4().hex[:8]}"
    call_id_boss = f"call-{uuid.uuid4().hex[:8]}"
    call_id_clarify = f"call-{uuid.uuid4().hex[:8]}"
    call_id_boss2 = f"call-{uuid.uuid4().hex[:8]}"

    events: list[dict] = []

    # Phase 1: reasoning (planning)
    events.append(
        _make_event(
            "assistant_reasoning",
            message_id=msg_id_1,
            content="用户希望模拟一个完整的餐厅流程。我需要组织三个 agent：顾客、厨师和餐厅老板，分别负责点单、做饭和买单。接下来我将创建对应的子任务。",
        )
    )

    # Phase 2: tool calls to create subagents/tasks
    events.append(
        _make_event(
            "assistant_tool_calls",
            message_id=msg_id_2,
            tool_calls=[
                {
                    "name": "task",
                    "args": {
                        "description": "顾客 agent：进入餐厅并点单",
                        "prompt": "你是一位顾客，走进一家中式餐厅。请查看菜单并点一份宫保鸡丁、一碗米饭和一杯豆浆。",
                    },
                    "id": call_id_customer,
                },
                {
                    "name": "task",
                    "args": {
                        "description": "厨师 agent：接收订单并完成烹饪",
                        "prompt": "你是一位厨师，收到顾客的订单：宫保鸡丁、米饭、豆浆。请在厨房里完成烹饪，并通知服务员出餐。",
                    },
                    "id": call_id_chef,
                },
                {
                    "name": "task",
                    "args": {
                        "description": "餐厅老板 agent：结账与收款",
                        "prompt": "你是一位餐厅老板，顾客用餐完毕。请计算账单总价并向顾客收款。宫保鸡丁 38 元，米饭 3 元，豆浆 5 元，总计 46 元。",
                    },
                    "id": call_id_boss,
                },
            ],
        )
    )

    # Phase 3: custom task lifecycle events (subagent running updates)
    events.append(
        _make_event(
            "custom_event",
            event_type="task_started",
            task_id="task-customer-001",
            description="顾客 agent 已开始执行：进入餐厅并点单",
        )
    )
    events.append(
        _make_event(
            "custom_event",
            event_type="task_running",
            task_id="task-customer-001",
            message="顾客正在浏览菜单...",
        )
    )
    events.append(
        _make_event(
            "custom_event",
            event_type="task_completed",
            task_id="task-customer-001",
            result="Task Succeeded. Result: 顾客入座，浏览菜单后点了一份宫保鸡丁、一碗米饭和一杯豆浆，等待上菜。",
        )
    )

    events.append(
        _make_event(
            "custom_event",
            event_type="task_started",
            task_id="task-chef-001",
            description="厨师 agent 已开始执行：接收订单并完成烹饪",
        )
    )
    events.append(
        _make_event(
            "custom_event",
            event_type="task_running",
            task_id="task-chef-001",
            message="厨师正在切配食材并热锅...",
        )
    )

    # Phase 4: intermediate assistant_message (progress update)
    events.append(
        _make_event(
            "assistant_message",
            message_id=msg_id_3,
            content="顾客已经顺利点单，厨师正在后厨忙碌地准备宫保鸡丁。",
        )
    )

    events.append(
        _make_event(
            "custom_event",
            event_type="task_completed",
            task_id="task-chef-001",
            result="Task Succeeded. Result: 厨师完成了宫保鸡丁、米饭和豆浆的烹饪，菜品已出餐，顾客开始用餐。",
        )
    )

    # Phase 5: tool results for customer and chef tasks
    events.append(
        _make_event(
            "tool_result",
            message_id=str(uuid.uuid4()),
            tool_name="task",
            tool_call_id=call_id_customer,
            content="Task Succeeded. Result: 顾客入座，浏览菜单后点了一份宫保鸡丁、一碗米饭和一杯豆浆，等待上菜。",
        )
    )
    events.append(
        _make_event(
            "tool_result",
            message_id=str(uuid.uuid4()),
            tool_name="task",
            tool_call_id=call_id_chef,
            content="Task Succeeded. Result: 厨师完成了宫保鸡丁、米饭和豆浆的烹饪，菜品已出餐，顾客开始用餐。",
        )
    )

    # Phase 6: boss task starts but needs clarification
    events.append(
        _make_event(
            "custom_event",
            event_type="task_started",
            task_id="task-boss-001",
            description="餐厅老板 agent 已开始执行：结账与收款",
        )
    )
    events.append(
        _make_event(
            "custom_event",
            event_type="task_running",
            task_id="task-boss-001",
            message="老板正在核对账单...",
        )
    )

    # Clarification request from boss agent
    events.append(
        _make_event(
            "tool_result",
            message_id=str(uuid.uuid4()),
            tool_name="ask_clarification",
            tool_call_id=call_id_clarify,
            content="请问本次模拟是否需要考虑给小费？如果需要，顾客打算给多少比例的小费？",
        )
    )

    # Simulated user reply turns into a new assistant reasoning + tool call
    events.append(
        _make_event(
            "assistant_reasoning",
            message_id=msg_id_4,
            content="用户回复不需要小费，直接按原价 46 元结账即可。我需要让老板 agent 继续完成收款动作。",
        )
    )

    events.append(
        _make_event(
            "assistant_tool_calls",
            message_id=msg_id_5,
            tool_calls=[
                {
                    "name": "task",
                    "args": {
                        "description": "餐厅老板 agent：按原价 46 元完成收款",
                        "prompt": "顾客回复不需要小费，请直接按原价 46 元（宫保鸡丁 38 元 + 米饭 3 元 + 豆浆 5 元）完成收款。",
                    },
                    "id": call_id_boss2,
                },
            ],
        )
    )

    events.append(
        _make_event(
            "custom_event",
            event_type="task_started",
            task_id="task-boss-002",
            description="餐厅老板 agent 继续执行：按原价收款",
        )
    )
    events.append(
        _make_event(
            "custom_event",
            event_type="task_running",
            task_id="task-boss-002",
            message="老板正在收款并打印小票...",
        )
    )
    events.append(
        _make_event(
            "custom_event",
            event_type="task_completed",
            task_id="task-boss-002",
            result="Task Succeeded. Result: 餐厅老板成功收款 46 元，顾客满意离店，本次用餐体验愉快。",
        )
    )

    # Final tool result for boss task
    events.append(
        _make_event(
            "tool_result",
            message_id=str(uuid.uuid4()),
            tool_name="task",
            tool_call_id=call_id_boss2,
            content="Task Succeeded. Result: 餐厅老板成功收款 46 元，顾客满意离店，本次用餐体验愉快。",
        )
    )

    # Another intermediate update before final summary
    events.append(
        _make_event(
            "assistant_message",
            message_id=str(uuid.uuid4()),
            content="所有子任务均已顺利完成，顾客点单、厨师做饭、老板结账的流程全部结束。",
        )
    )

    # Phase 7: final assistant_message (full summary)
    final_text = (
        "本次餐厅 agent team 模拟已完成，流程如下：\n\n"
        "1. **顾客 agent**：走进餐厅，浏览菜单后点了一份宫保鸡丁、一碗米饭和一杯豆浆。\n"
        "2. **厨师 agent**：接收到订单后，精心准备并完成了三道菜品的烹饪，顺利出餐。\n"
        "3. **餐厅老板 agent**：核对账单（宫保鸡丁 38 元 + 米饭 3 元 + 豆浆 5 元 = 46 元），"
        "在确认不需要小费后，成功收款 46 元。\n\n"
        "整个模拟过程中，三位 agent 各司其职，顾客满意用餐并离店。"
    )
    events.append(
        _make_event(
            "assistant_message",
            message_id=str(uuid.uuid4()),
            content=final_text,
        )
    )

    return events, final_text


def main() -> None:
    events, final_text = generate_snapshot()

    snapshot_dir = Path(__file__).parent.parent / "tests" / "snapshots"
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    ndjson_path = snapshot_dir / "ultra_restaurant_agent_team.ndjson"
    meta_path = snapshot_dir / "ultra_restaurant_agent_team.meta.json"

    # Write NDJSON
    with ndjson_path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")

    # Compute stats
    stats: dict[str, int] = {}
    for ev in events:
        t = ev["type"]
        stats[t] = stats.get(t, 0) + 1

    meta = {
        "scenario": "餐厅 agent team 模拟",
        "mode": "ultra",
        "runtime_options": {
            "plan_mode": True,
            "subagent_enabled": True,
            "thinking_enabled": True,
        },
        "event_count": len(events),
        "event_stats": stats,
        "final_response_preview": final_text[:80] + "...",
        "is_mock": True,
        "note": "基于真实 DeerFlow 事件结构手工构造的模拟快照，待真实 API key 可用后替换为真实录制",
    }

    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"Generated: {ndjson_path} ({ndjson_path.stat().st_size} bytes)")
    print(f"Generated: {meta_path} ({meta_path.stat().st_size} bytes)")
    print(f"Total events: {len(events)}")
    print(f"Event stats: {json.dumps(stats, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
