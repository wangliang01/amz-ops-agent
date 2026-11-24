"""Deterministic checks for the real-LLM eval entrypoint.

Runs without an API key: verifies the no-key guard, the cost cap, failure
injection, the fallback eval, and report hygiene. Real provider calls are
verified manually with `--require-llm` after a key is configured.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _check(name: str, ok: bool, detail: str = "") -> bool:
    print(f"{'PASS' if ok else 'FAIL'} {name}" + (f"  [{detail}]" if detail else ""))
    return ok


def _fake_case(case_id: str) -> dict:
    return {"case_id": case_id, "sku_id": "SKU-TEST"}


def _runner(cost: float, calls: int):
    def run(case: dict) -> dict:
        return {
            "case_id": case["case_id"],
            "sku_id": case["sku_id"],
            "passed": True,
            "failures": [],
            "llm_calls": calls,
            "tokens": {"prompt": 10, "completion": 5, "total": 15},
            "cost_usd": cost,
            "latency_sec": 0.01,
        }

    return run


def main() -> int:
    ok = True

    # AC-1: --require-llm without a key exits 2 and runs no cases.
    env = dict(os.environ)
    env["OPENAI_API_KEY"] = ""
    env["LLM_ENABLED"] = "false"
    with tempfile.TemporaryDirectory(prefix="amz-eval-") as tmp:
        report_path = Path(tmp) / "no_key_report.json"
        proc = subprocess.run(
            [PY, "-m", "evals.run_eval", "--require-llm", "--report", str(report_path)],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        output = proc.stdout + proc.stderr
        ok &= _check("AC-1 exit code 2", proc.returncode == 2, f"rc={proc.returncode}")
        ok &= _check("AC-1 message names OPENAI_API_KEY", "OPENAI_API_KEY" in output)
        ok &= _check("AC-1 no cases executed", "G-001" not in output)
        ok &= _check("AC-1 no report written", not report_path.exists())

    # AC-4 / AC-8: deterministic paths with a fake runner.
    from evals.run_eval import run_cases

    cases = [_fake_case("X-001"), _fake_case("X-002")]
    results, total_cost, aborted = run_cases(
        cases,
        _runner(cost=0.001, calls=3),
        require_llm=True,
        max_cost_usd=0.0001,
        expected_calls=3,
    )
    ok &= _check(
        "AC-4 cost cap aborts after first case",
        aborted == "cost_cap" and len(results) == 1 and total_cost == 0.001,
        f"aborted={aborted} results={len(results)}",
    )

    results, _, _ = run_cases(
        cases,
        _runner(cost=0.0, calls=0),
        require_llm=True,
        max_cost_usd=None,
        expected_calls=3,
    )
    ok &= _check(
        "AC-8 llm_not_used fails the case",
        not results[0]["passed"] and "llm_not_used" in results[0]["failures"],
        f"failures={results[0]['failures']}",
    )

    results, _, _ = run_cases(
        cases,
        _runner(cost=0.0, calls=2),
        require_llm=True,
        max_cost_usd=None,
        expected_calls=3,
    )
    ok &= _check(
        "AC-8 partial fallback fails the case",
        not results[0]["passed"]
        and any("llm_calls_below_expected" in f for f in results[0]["failures"]),
        f"failures={results[0]['failures']}",
    )

    # AC-6: fallback eval still passes 10/10.
    env = dict(os.environ)
    env["LLM_ENABLED"] = "false"
    env["EMBEDDING_ENABLED"] = "false"
    proc = subprocess.run(
        [PY, "-m", "evals.run_eval"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    ok &= _check(
        "AC-6 fallback eval 10/10",
        proc.returncode == 0 and "10/10 passed" in proc.stdout,
        f"rc={proc.returncode}",
    )

    # AC-5: the LLM report is ignored by git.
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    ok &= _check("AC-5 llm_report ignored", "evals/llm_report.json" in gitignore)

    print("LLM_EVAL_VERIFY_OK" if ok else "LLM_EVAL_VERIFY_FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
