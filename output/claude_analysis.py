"""
claude_analysis.py — Claude API integration for sim result analysis

Takes a SimulationResults object, formats it into a structured prompt,
and returns natural language analysis from Claude.

Usage:
    from output.claude_analysis import analyze, compare

    analysis = analyze(results, context="Legacy locals vs Lands/Delver/Elves field")
    print(analysis)

    diff = compare(results_a, results_b,
                   label_a="4x Bugler", label_b="3x Bugler + 1x Recruiter")
    print(diff)
"""

import os
import json
import requests
from typing import Optional

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL     = "claude-sonnet-4-20250514"
MAX_TOKENS        = 1024


def _get_api_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not set. "
            "Add it to your environment or a .env file."
        )
    return key


def _call_claude(prompt: str, system: str) -> str:
    """Raw Claude API call. Returns assistant text."""
    headers = {
        "x-api-key":         _get_api_key(),
        "anthropic-version": "2023-06-01",
        "content-type":      "application/json",
    }
    body = {
        "model":      DEFAULT_MODEL,
        "max_tokens": MAX_TOKENS,
        "system":     system,
        "messages":   [{"role": "user", "content": prompt}],
    }
    resp = requests.post(ANTHROPIC_API_URL, headers=headers,
                         json=body, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["content"][0]["text"].strip()


SYSTEM_PROMPT = """You are an expert Magic: The Gathering analyst specializing in competitive \
format analysis (Legacy, Modern, Pioneer). You interpret goldfish simulation data to give \
concise, actionable deckbuilding recommendations. You understand that goldfish simulations \
model solo consistency — they don't account for interaction, but they reveal clock speed, \
mana consistency, and curve efficiency.

Always respond in plain prose. No bullet lists unless comparing two builds. \
Be specific: cite the actual numbers from the data. Limit your response to 200 words."""


def _format_results(results) -> str:
    """Serialize SimulationResults into a compact JSON string for the prompt."""
    d = results.to_dict()
    return json.dumps({
        "archetype":        d["archetype"],
        "n_games":          d["n_games"],
        "win_rate_pct":     round(d["win_rate"] * 100, 1),
        "avg_kill_turn":    d["avg_kill_turn"],
        "median_kill_turn": d["median_kill_turn"],
        "win_by_t3_pct":    d["win_by_t3"],
        "win_by_t4_pct":    d["win_by_t4"],
        "win_by_t5_pct":    d["win_by_t5"],
        "avg_mulligans":    d["avg_mulligans"],
        "mull_rate_pct":    d["mull_rate"],
        "kill_distribution": d["kill_distribution"],
    }, indent=2)


def analyze(
    results,
    context: Optional[str] = None,
    question: Optional[str] = None,
) -> str:
    """
    Analyze a single SimulationResults object.

    Args:
        results:  SimulationResults from run_simulation()
        context:  Optional meta context (e.g. "Legacy locals field: Lands, Delver, Elves")
        question: Optional specific question (e.g. "Is this fast enough to race Lands g1?")

    Returns:
        Claude's analysis as a string.
    """
    data_str = _format_results(results)

    prompt_parts = [
        f"Here are goldfish simulation results for {results.archetype}:",
        f"```json\n{data_str}\n```",
    ]

    if context:
        prompt_parts.append(f"Tournament context: {context}")

    if question:
        prompt_parts.append(f"Specific question: {question}")
    else:
        prompt_parts.append(
            "Analyze these results. Comment on: clock speed vs the expected meta, "
            "consistency, mulligan rate, and one concrete deckbuilding recommendation "
            "based on the data."
        )

    return _call_claude("\n\n".join(prompt_parts), SYSTEM_PROMPT)


def compare(
    results_a,
    results_b,
    label_a: Optional[str] = None,
    label_b: Optional[str] = None,
    context: Optional[str] = None,
) -> str:
    """
    Compare two simulation results and recommend which build is better.

    Args:
        results_a / results_b: SimulationResults objects
        label_a / label_b:     Human-readable labels (e.g. "4x Militia Bugler")
        context:               Optional meta context

    Returns:
        Claude's comparison as a string.
    """
    label_a = label_a or results_a.archetype
    label_b = label_b or results_b.archetype

    data_a = _format_results(results_a)
    data_b = _format_results(results_b)

    prompt_parts = [
        "Compare these two goldfish simulation results and recommend which build to play:",
        f"Build A — {label_a}:",
        f"```json\n{data_a}\n```",
        f"Build B — {label_b}:",
        f"```json\n{data_b}\n```",
    ]

    if context:
        prompt_parts.append(f"Tournament context: {context}")

    prompt_parts.append(
        "Identify the key differences in clock speed and consistency. "
        "State clearly which build you recommend and why, citing specific numbers."
    )

    return _call_claude("\n\n".join(prompt_parts), SYSTEM_PROMPT)


def ask(results, question: str) -> str:
    """
    Free-form question about simulation results.

    Args:
        results:  SimulationResults
        question: Any question about the data

    Returns:
        Claude's answer as a string.
    """
    return analyze(results, question=question)
