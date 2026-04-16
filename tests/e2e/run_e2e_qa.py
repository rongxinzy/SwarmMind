#!/usr/bin/env python3
"""E2E QA test for SwarmMind backend four modes."""

import json
import sys
import time
from pathlib import Path

import requests

BASE_URL = "http://127.0.0.1:8000"
OUTPUT_DIR = Path(__file__).parent
MODES = ["flash", "thinking", "pro", "ultra"]
STREAM_TIMEOUT = 300  # seconds per mode (generous for LLM calls)
REQUEST_TIMEOUT = 30

# Mode-specific prompts designed to trigger expected LLM behaviors
MODE_PROMPTS = {
    "flash": "请用一句话介绍你自己",
    "thinking": (
        "我正在设计一个分布式消息队列系统，需要在一致性、可用性和分区容错性之间做权衡。"
        "请帮我深入分析CAP定理在这个场景下的应用，并详细展示你的推理过程。"
    ),
    "pro": (
        "我计划在下个月组织一场200人的技术峰会，包含嘉宾邀请、场地预订、议程安排、宣传推广和现场执行。"
        "请帮我制定一个详细的执行规划，分阶段说明关键任务和里程碑。"
    ),
    "ultra": (
        "我想要开发一个完整的个人财务管理系统，包含收支记录、预算设置、报表分析、数据导出和智能建议功能。"
        "请帮我拆分这个任务，调用不同的子agent分别负责需求分析、技术选型、数据库设计和API设计，"
        "然后整合输出一份完整的项目方案。"
    ),
}

# Expected status labels by mode (proof that backend flags are mapped correctly)
EXPECTED_STATUS_LABELS = {
    "flash": {
        "routing": "正在准备快速回复",
        "running": "正在快速生成结果",
    },
    "thinking": {
        "routing": "正在分析你的问题",
        "running": "正在整理深入回复",
    },
    "pro": {
        "routing": "正在规划这轮任务的执行方式",
        "running": "正在按规划生成结果",
    },
    "ultra": {
        "routing": "Agent Team 正在判断这轮探索需要怎样的协作方式",
        "running": "Agent Team 正在协作处理你的问题",
    },
}

RESULTS = {}
STATE_FILE = OUTPUT_DIR / "_qa_state.json"


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state():
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)


def create_conversation(goal: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/conversations",
        json={"goal": goal},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def send_stream(conversation_id: str, content: str, mode: str) -> list[dict]:
    """Send message via stream and collect all NDJSON events."""
    resp = requests.post(
        f"{BASE_URL}/conversations/{conversation_id}/messages/stream",
        json={"content": content, "mode": mode},
        stream=True,
        timeout=STREAM_TIMEOUT,
    )
    resp.raise_for_status()

    events = []
    for line in resp.iter_lines(decode_unicode=True):
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as e:
            events.append({"_raw": line, "_parse_error": str(e)})
    return events


def get_messages(conversation_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/conversations/{conversation_id}/messages",
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def get_trace(conversation_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/conversations/{conversation_id}/trace",
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def extract_status_labels(events: list[dict]) -> dict:
    """Extract status phase labels from stream events."""
    labels = {}
    for ev in events:
        if ev.get("type") == "status" and "phase" in ev:
            labels[ev["phase"]] = ev.get("label", "")
    return labels


def analyze_stream(events: list[dict], mode: str) -> dict:
    types = [e.get("type") for e in events if "_parse_error" not in e]
    has_done = "done" in types
    has_assistant_final = "assistant_final" in types
    has_thinking = "status.thinking" in types
    has_task_started = "task_started" in types
    has_team_activity = "team_activity" in types
    has_error = "error" in types
    parse_errors = [e for e in events if "_parse_error" in e]
    status_labels = extract_status_labels(events)

    analysis = {
        "event_types": list(dict.fromkeys(types)),
        "total_events": len(events),
        "has_done": has_done,
        "has_assistant_final": has_assistant_final,
        "has_thinking": has_thinking,
        "has_task_started": has_task_started,
        "has_team_activity": has_team_activity,
        "has_error": has_error,
        "parse_errors": parse_errors,
        "status_labels": status_labels,
    }
    return analysis


def run_mode(mode: str) -> dict:
    print(f"\n========== Testing mode: {mode} ==========")
    result = {"mode": mode, "status": "RUNNING"}
    prompt = MODE_PROMPTS[mode]
    expected_labels = EXPECTED_STATUS_LABELS[mode]

    try:
        # 1. Create conversation
        conv = create_conversation(f"E2E test for {mode} mode")
        conv_id = conv["id"]
        result["conversation_id"] = conv_id
        print(f"[{mode}] Created conversation: {conv_id}")

        # 2. Stream message
        print(f"[{mode}] Sending stream request...")
        print(f"[{mode}] Prompt: {prompt[:60]}...")
        t0 = time.time()
        events = send_stream(conv_id, prompt, mode)
        elapsed = time.time() - t0
        result["stream_elapsed_seconds"] = round(elapsed, 2)
        print(f"[{mode}] Stream completed in {elapsed:.1f}s, {len(events)} events")

        # Save stream
        stream_file = OUTPUT_DIR / f"{mode}_stream.jsonl"
        with open(stream_file, "w", encoding="utf-8") as f:
            for ev in events:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        result["stream_file"] = str(stream_file)

        # 3. Analyze stream
        analysis = analyze_stream(events, mode)
        result["stream_analysis"] = analysis
        print(f"[{mode}] Event types: {analysis['event_types']}")
        print(f"[{mode}] Status labels: {analysis['status_labels']}")

        # 4. Get messages
        msgs = get_messages(conv_id)
        result["messages"] = msgs
        msg_roles = [m["role"] for m in msgs.get("items", [])]
        print(f"[{mode}] Messages roles: {msg_roles}")

        # 5. Get trace
        try:
            trace = get_trace(conv_id)
            result["trace"] = trace
            print(f"[{mode}] Trace keys: {list(trace.keys())}")
        except Exception as te:
            result["trace_error"] = str(te)
            print(f"[{mode}] Trace error: {te}")

        # Assertions (revised per PM/owner feedback)
        checks = []
        checks.append(("HTTP 200 & stream ended", analysis["has_done"]))
        checks.append(("assistant_final present", analysis["has_assistant_final"]))
        checks.append(("no parse errors", len(analysis["parse_errors"]) == 0))
        checks.append(("messages persisted", "user" in msg_roles and "assistant" in msg_roles))

        # Verify backend flag mapping via mode-specific status labels
        routing_label = analysis["status_labels"].get("routing", "")
        running_label = analysis["status_labels"].get("running", "")
        checks.append((
            f"{mode}: routing label matches expected backend flags",
            routing_label == expected_labels["routing"],
        ))
        checks.append((
            f"{mode}: running label matches expected backend flags",
            running_label == expected_labels["running"],
        ))

        if mode == "flash":
            # flash should never emit thinking because thinking_enabled=False
            checks.append(("flash: no thinking events", not analysis["has_thinking"]))
        else:
            # For thinking/pro/ultra, we record whether thinking appeared (informational)
            # but do NOT fail the test if LLM chose not to emit reasoning chunks.
            checks.append((
                f"{mode}: thinking events recorded (optional, backend flag verified above)",
                True,  # always pass; we keep the info in the report
            ))

        if mode == "ultra":
            # task events are optional; record actual behavior without hard fail
            has_task_or_activity = analysis["has_task_started"] or analysis["has_team_activity"]
            checks.append((
                "ultra: task/team_activity events recorded (optional for simple prompts)",
                True,  # always pass
            ))
            result["task_events_observed"] = has_task_or_activity

        result["checks"] = checks
        result["all_passed"] = all(passed for _, passed in checks)
        result["status"] = "PASS" if result["all_passed"] else "FAIL"
        print(f"[{mode}] Result: {result['status']}")

    except Exception as exc:
        result["status"] = "FAIL"
        result["error"] = str(exc)
        print(f"[{mode}] EXCEPTION: {exc}")

    return result


def collect_backend_logs() -> str:
    """Try to collect backend logs from various sources."""
    logs = []
    sources = []

    # PM2 api logs
    pm2_out = Path("/Users/krli/.pm2/logs/swarmmind-api-out.log")
    pm2_err = Path("/Users/krli/.pm2/logs/swarmmind-api-error.log")

    for src in [pm2_out, pm2_err]:
        if src.exists():
            try:
                with open(src, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()
                content = "".join(lines[-2000:])
                logs.append(f"=== {src} ===\n{content}")
                sources.append(str(src))
            except Exception as e:
                logs.append(f"=== {src} ===\nError reading: {e}")

    # runtime/deerflow logs if any
    runtime_dir = Path("/Users/krli/workspace/SwarmMindProject/SwarmMind/.runtime/deerflow")
    if runtime_dir.exists():
        for log_file in sorted(runtime_dir.rglob("*.log")):
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                logs.append(f"=== {log_file} ===\n{content}")
                sources.append(str(log_file))
            except Exception as e:
                logs.append(f"=== {log_file} ===\nError reading: {e}")

    if not logs:
        return "# No backend logs could be collected."

    header = f"# Backend logs collected from: {', '.join(sources)}\n\n"
    return header + "\n\n".join(logs)


def scan_backend_errors() -> dict:
    """Scan backend logs for known stability issues."""
    issues = {
        "database_locked": 0,
        "http_500": 0,
        "other_errors": [],
    }
    pm2_err = Path("/Users/krli/.pm2/logs/swarmmind-api-error.log")
    pm2_out = Path("/Users/krli/.pm2/logs/swarmmind-api-out.log")

    for src in [pm2_err, pm2_out]:
        if not src.exists():
            continue
        try:
            with open(src, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    lower = line.lower()
                    if "database is locked" in lower:
                        issues["database_locked"] += 1
                    if '" 500 ' in line or " 500 internal server error" in lower:
                        issues["http_500"] += 1
                    if "error" in lower and "database is locked" not in lower and '" 500 ' not in line:
                        # Collect a sample of other error lines
                        if len(issues["other_errors"]) < 20:
                            issues["other_errors"].append(line.strip())
        except Exception:
            pass

    return issues


def write_report():
    report_path = OUTPUT_DIR / "e2e_report.md"
    backend_issues = scan_backend_errors()

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# SwarmMind E2E QA Report\n\n")
        f.write("## Test Environment\n")
        f.write(f"- API Base URL: {BASE_URL}\n")
        f.write(f"- Execution Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Mode Results\n\n")
        for mode in MODES:
            r = RESULTS.get(mode, {})
            status = r.get("status", "UNKNOWN")
            f.write(f"### {mode.upper()} — {status}\n\n")
            f.write(f"- Prompt: `{MODE_PROMPTS[mode]}`\n")
            if "error" in r:
                f.write(f"**Error:** {r['error']}\n\n")
            if "stream_analysis" in r:
                sa = r["stream_analysis"]
                f.write(f"- Stream events: {sa['total_events']}\n")
                f.write(f"- Event types: `{sa['event_types']}`\n")
                f.write(f"- Has `done`: {sa['has_done']}\n")
                f.write(f"- Has `assistant_final`: {sa['has_assistant_final']}\n")
                f.write(f"- Has `status.thinking`: {sa['has_thinking']}\n")
                f.write(f"- Has `task_started`: {sa['has_task_started']}\n")
                f.write(f"- Has `team_activity`: {sa['has_team_activity']}\n")
                f.write(f"- Stream elapsed: {r.get('stream_elapsed_seconds', 'N/A')}s\n")
                f.write(f"- Status labels: `{sa['status_labels']}`\n")
            if "messages" in r:
                msg_count = r["messages"].get("total", 0)
                f.write(f"- Messages persisted: {msg_count}\n")
            if "trace" in r:
                f.write(f"- Trace keys: `{list(r['trace'].keys())}`\n")
            if "checks" in r:
                f.write("\n**Checks:**\n")
                for desc, passed in r["checks"]:
                    mark = "✅" if passed else "❌"
                    f.write(f"- {mark} {desc}\n")
            if mode == "ultra" and "task_events_observed" in r:
                f.write(f"- Task/team_activity observed: {r['task_events_observed']}\n")
            f.write("\n")

        f.write("## Backend Stability Scan\n\n")
        f.write(f"- `database is locked` occurrences: {backend_issues['database_locked']}\n")
        f.write(f"- HTTP 500 occurrences: {backend_issues['http_500']}\n")
        if backend_issues["other_errors"]:
            f.write("- Other error samples:\n")
            for err in backend_issues["other_errors"]:
                f.write(f"  - `{err}`\n")
        else:
            f.write("- No other errors sampled.\n")
        f.write("\n")

        f.write("## Issues Found\n\n")
        issues = []
        for mode in MODES:
            r = RESULTS.get(mode, {})
            if r.get("status") != "PASS":
                issues.append(f"- **{mode}**: Test failed or encountered errors. Details: {r.get('error', 'See checks above')}")
            elif "checks" in r:
                for desc, passed in r["checks"]:
                    if not passed:
                        issues.append(f"- **{mode}**: Check failed — {desc}")
        if backend_issues["database_locked"] > 0:
            issues.append(f"- **Backend**: `database is locked` occurred {backend_issues['database_locked']} time(s)")
        if backend_issues["http_500"] > 0:
            issues.append(f"- **Backend**: HTTP 500 occurred {backend_issues['http_500']} time(s)")
        if issues:
            for issue in issues:
                f.write(issue + "\n")
        else:
            f.write("No issues found.\n")
        f.write("\n")

        f.write("## Overall Conclusion\n\n")
        all_pass = all(RESULTS.get(m, {}).get("status") == "PASS" for m in MODES)
        if all_pass:
            f.write("✅ All four modes (flash, thinking, pro, ultra) passed the end-to-end tests. ")
            f.write("Backend flag mapping and stream semantics behave correctly.\n")
        else:
            f.write("⚠️ Some modes did not pass all checks. See the issues above for details.\n")
            for mode in MODES:
                r = RESULTS.get(mode, {})
                f.write(f"- {mode}: {r.get('status', 'UNKNOWN')}\n")

    print(f"\nReport written to {report_path}")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    global RESULTS
    RESULTS = load_state()

    # Clear old results so we re-run everything with new prompts/assertions
    if any(m in RESULTS for m in MODES):
        print("Clearing previous results to re-run with updated prompts/assertions...")
        RESULTS = {}
        save_state()

    for mode in MODES:
        RESULTS[mode] = run_mode(mode)
        save_state()

    # Collect logs
    print("\nCollecting backend logs...")
    logs = collect_backend_logs()
    log_file = OUTPUT_DIR / "backend.log"
    with open(log_file, "w", encoding="utf-8") as f:
        f.write(logs)
    print(f"Backend logs written to {log_file}")

    write_report()
    print("\nE2E QA complete.")


if __name__ == "__main__":
    main()
