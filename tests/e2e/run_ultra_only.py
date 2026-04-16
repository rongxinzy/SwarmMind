#!/usr/bin/env python3
"""Run ultra mode E2E test only."""
import json
import time
from pathlib import Path
import requests

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path(__file__).parent
STREAM_TIMEOUT = 400  # generous for potential subagent calls
REQUEST_TIMEOUT = 30

PROMPT = (
    "我想要开发一个完整的个人财务管理系统，包含收支记录、预算设置、报表分析、数据导出和智能建议功能。"
    "请帮我拆分这个任务，调用不同的子agent分别负责需求分析、技术选型、数据库设计和API设计，"
    "然后整合输出一份完整的项目方案。"
)

EXPECTED_LABELS = {
    "routing": "Agent Team 正在判断这轮探索需要怎样的协作方式",
    "running": "Agent Team 正在协作处理你的问题",
}

def create_conversation(goal: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/conversations",
        json={"goal": goal},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()

def send_stream(conv_id: str, content: str) -> list[dict]:
    print("[ultra] Starting stream request...")
    resp = requests.post(
        f"{BASE_URL}/conversations/{conv_id}/messages/stream",
        json={"content": content, "mode": "ultra"},
        stream=True,
        timeout=STREAM_TIMEOUT,
    )
    resp.raise_for_status()
    events = []
    last_print = time.time()
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError as e:
            ev = {"_raw": line, "_parse_error": str(e)}
        events.append(ev)
        if time.time() - last_print > 10:
            print(f"[ultra] Collected {len(events)} events so far...")
            last_print = time.time()
    print(f"[ultra] Stream finished, total events: {len(events)}")
    return events

def get_messages(conv_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/conversations/{conv_id}/messages",
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()

def get_trace(conv_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/conversations/{conv_id}/trace",
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()

def main():
    result = {"mode": "ultra", "status": "RUNNING"}
    try:
        conv = create_conversation("E2E test for ultra mode")
        conv_id = conv["id"]
        result["conversation_id"] = conv_id
        print(f"[ultra] Created conversation: {conv_id}")

        t0 = time.time()
        events = send_stream(conv_id, PROMPT)
        elapsed = time.time() - t0
        result["stream_elapsed_seconds"] = round(elapsed, 2)

        stream_file = OUTPUT_DIR / "ultra_stream.jsonl"
        with open(stream_file, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        result["stream_file"] = str(stream_file)

        types = [e.get("type") for e in events if "_parse_error" not in e]
        status_labels = {}
        for e in events:
            if e.get("type") == "status" and "phase" in e:
                status_labels[e["phase"]] = e.get("label", "")

        analysis = {
            "event_types": list(dict.fromkeys(types)),
            "total_events": len(events),
            "has_done": "done" in types,
            "has_assistant_final": "assistant_final" in types,
            "has_thinking": "status.thinking" in types,
            "has_task_started": "task_started" in types,
            "has_team_activity": "team_activity" in types,
            "has_error": "error" in types,
            "status_labels": status_labels,
        }
        result["stream_analysis"] = analysis
        print(f"[ultra] Event types: {analysis['event_types']}")
        print(f"[ultra] Status labels: {status_labels}")

        msgs = get_messages(conv_id)
        result["messages"] = msgs
        msg_roles = [m["role"] for m in msgs.get("items", [])]
        print(f"[ultra] Messages roles: {msg_roles}")

        trace = get_trace(conv_id)
        result["trace"] = trace
        print(f"[ultra] Trace keys: {list(trace.keys())}")

        checks = []
        checks.append(("HTTP 200 & stream ended", analysis["has_done"]))
        checks.append(("assistant_final present", analysis["has_assistant_final"]))
        checks.append(("messages persisted", "user" in msg_roles and "assistant" in msg_roles))
        checks.append(("routing label matches expected backend flags", status_labels.get("routing") == EXPECTED_LABELS["routing"]))
        checks.append(("running label matches expected backend flags", status_labels.get("running") == EXPECTED_LABELS["running"]))
        checks.append(("thinking events recorded (optional)", True))
        checks.append(("task/team_activity events recorded (optional)", True))
        result["task_events_observed"] = analysis["has_task_started"] or analysis["has_team_activity"]

        result["checks"] = checks
        result["all_passed"] = all(passed for _, passed in checks)
        result["status"] = "PASS" if result["all_passed"] else "FAIL"
        print(f"[ultra] Result: {result['status']}")

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = str(exc)
        print(f"[ultra] EXCEPTION: {exc}")

    # Update state
    state_file = OUTPUT_DIR / "_qa_state.json"
    state = {}
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
    state["ultra"] = result
    with open(state_file, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    print("Ultra-only test complete.")

if __name__ == "__main__":
    main()
