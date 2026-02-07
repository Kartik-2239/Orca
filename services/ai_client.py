from __future__ import annotations

import random
from dataclasses import dataclass
import json
from typing import Optional

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency
    OpenAI = None


@dataclass
class AIResult:
    items: list[str]


@dataclass
class RenameResult:
    old_names: list[str]
    new_names: list[str]


@dataclass
class RenameRules:
    preserve_extensions: bool = True
    extension: str = ""
    case: str = "none"  # "lower", "upper", "none"
    prefix: str = ""
    suffix: str = ""
    replace: list[dict[str, str]] | None = None
    skip_if_matches: list[str] | None = None
    numbering: dict[str, object] | None = None


def generate_text(prompt: str, count: int, mode: str = "content", api_key: Optional[str] = None) -> AIResult:
    """Lightweight AI helper. Falls back to local placeholder when no API key."""
    api_key = (api_key or "").strip()
    if OpenAI is not None and api_key:
        return _generate_with_openai(prompt, count, mode, api_key)
    return _generate_placeholder(prompt, count, mode)


def ai_available(api_key: Optional[str]) -> bool:
    return OpenAI is not None and bool((api_key or "").strip())


def generate_rename_plan(prompt: str, filenames: list[str], api_key: Optional[str] = None) -> RenameResult:
    api_key = (api_key or "").strip()
    if OpenAI is not None and api_key and filenames:
        return _rename_with_openai(prompt, filenames, api_key)
    return _rename_placeholder(filenames)


def generate_rename_rules(prompt: str, filenames: list[str], api_key: Optional[str] = None) -> RenameRules:
    api_key = (api_key or "").strip()
    if OpenAI is not None and api_key and filenames:
        return _rules_with_openai(prompt, filenames, api_key)
    return RenameRules()


def _rename_with_openai(prompt: str, filenames: list[str], api_key: str) -> RenameResult:
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    system = (
        "You rename files. Return JSON array of strings only, length must equal input. "
        "Each output string is the new filename for the corresponding input. "
        "Preserve extensions unless user explicitly requests changes. "
        "If a file should remain unchanged, return the original name."
    )
    user = (
        "Rename these files based on the user's request.\n"
        f"Request: {prompt}\n"
        f"Files: {filenames}"
    )
    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    text = ""
    if resp and resp.choices:
        text = resp.choices[0].message.content or ""
    items = _parse_json_list(text)
    if len(items) == len(filenames):
        return RenameResult(old_names=filenames, new_names=items)
    return _rename_placeholder(filenames)


def _rules_with_openai(prompt: str, filenames: list[str], api_key: str) -> RenameRules:
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    system = (
        "You generate rename rules as JSON object only. "
        "Keys: preserve_extensions (bool), extension (string), case (\"lower\"|\"upper\"|\"none\"), "
        "prefix (string), suffix (string), replace (list of {pattern, replacement}), "
        "skip_if_matches (list of regex strings), numbering (object with enabled(bool), start(int), "
        "padding(int), prefix(string), suffix(string), skip_if_numbered(bool)). "
        "Return JSON only."
    )
    user = (
        "Create rename rules based on the user request. "
        f"Request: {prompt}\n"
        f"Files: {filenames}"
    )
    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.2,
    )
    text = ""
    if resp and resp.choices:
        text = resp.choices[0].message.content or ""
    data = _parse_json_object(text)
    if isinstance(data, dict):
        return _coerce_rules(data)
    return RenameRules()


def _rename_placeholder(filenames: list[str]) -> RenameResult:
    return RenameResult(old_names=filenames, new_names=list(filenames))


def _generate_with_openai(prompt: str, count: int, mode: str, api_key: str) -> AIResult:
    client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    if mode == "names":
        system = (
            "The file names should be in lowercase and should tell exactly what is in the document "
            "STRICTLY adhere to the word limit if specified"
            "like name of a chapter in a story, use unique strings, if similar names are preset add numbers. "
            "Return JSON array of strings only."
        )
        user = f"Generate {count} filename stems for: {prompt}"
    else:
        system = (
            "Generate documents exactly the way users asks for and the number of items in array "
            f"should be strictly equal to {count or ""} even if the user asks for more or less. "
            "Return JSON array of strings only."
        )
        user = (
            f"Generate {count} items"
            f"and read like a short document section. Prompt: {prompt}"
        )
    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.3,
    )
    text = ""
    if resp and resp.choices:
        text = resp.choices[0].message.content or ""
    items = _parse_json_list(text)
    if items:
        return AIResult(items=items[:count])
    return _generate_placeholder(prompt, count, mode)


def _generate_placeholder(prompt: str, count: int, mode: str) -> AIResult:
    rng = random.SystemRandom()
    if mode == "names":
        pool = [
            "northwind",
            "blueprint",
            "cobalt",
            "lighthouse",
            "vector",
            "archway",
            "ripple",
            "summit",
            "cascade",
            "orbit",
            "ember",
            "atlas",
            "horizon",
            "prism",
            "glyph",
            "stencil",
            "delta",
            "harbor",
            "marble",
            "signal",
        ]
        rng.shuffle(pool)
        return AIResult(items=pool[:count])

    pool = [
        (
            "The skyline shifted as the clouds cleared, revealing a stretch of "
            "light that moved slowly across the desk. The draft took shape as "
            "a sequence of small, practical steps, each one tightening the focus "
            "on what mattered most. By the end, the message was clear and easy "
            "to follow, with enough detail to guide the next action."
        ),
        (
            "A quiet algorithm stitched the data together, turning raw notes into "
            "a cohesive section. The text emphasized clarity, breaking ideas into "
            "short paragraphs with concrete examples. It read like a concise memo, "
            "usable immediately without needing extra interpretation."
        ),
        (
            "The outline favored direct language and steady pacing. Each sentence "
            "built on the last, giving the section a clear arc from problem to "
            "resolution. The final paragraph summarized the takeaway and suggested "
            "the next obvious step."
        ),
        (
            "The system response settled into a practical rhythm, making room for "
            "both instruction and context. It avoided filler, opting for concrete "
            "detail that could translate directly into a task. The ending reinforced "
            "the key point without repeating the full explanation."
        ),
        (
            "A fresh draft emerged with a calm tone and clear structure. The first "
            "paragraph established purpose, the middle clarified decisions, and the "
            "closing sentence highlighted the expected outcome. It read like a short "
            "section of documentation."
        ),
    ]
    return AIResult(items=[rng.choice(pool) for _ in range(count)])


def _parse_json_list(text: str) -> list[str]:
    try:
        data = json.loads(text)
        if isinstance(data, list):
            return [str(item).strip() for item in data if str(item).strip()]
    except Exception:
        data = None
    if isinstance(data, list):
        return [str(item).strip() for item in data if str(item).strip()]
    # Fallback: split lines if model didn't return JSON
    lines = []
    for line in text.splitlines():
        cleaned = line.strip().lstrip("-*•").strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _parse_json_object(text: str) -> dict | None:
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            data = json.loads(snippet)
            if isinstance(data, dict):
                return data
        except Exception:
            return None
    return None


def _coerce_rules(data: dict) -> RenameRules:
    rules = RenameRules()
    rules.preserve_extensions = bool(data.get("preserve_extensions", rules.preserve_extensions))
    rules.extension = str(data.get("extension", rules.extension) or "")
    rules.case = str(data.get("case", rules.case) or "none").lower()
    rules.prefix = str(data.get("prefix", rules.prefix) or "")
    rules.suffix = str(data.get("suffix", rules.suffix) or "")
    replace = data.get("replace")
    if isinstance(replace, list):
        cleaned = []
        for item in replace:
            if isinstance(item, dict) and "pattern" in item and "replacement" in item:
                cleaned.append({"pattern": str(item["pattern"]), "replacement": str(item["replacement"])})
        rules.replace = cleaned or None
    skip = data.get("skip_if_matches")
    if isinstance(skip, list):
        rules.skip_if_matches = [str(item) for item in skip if str(item)]
    numbering = data.get("numbering")
    if isinstance(numbering, dict):
        rules.numbering = {
            "enabled": bool(numbering.get("enabled", False)),
            "start": int(numbering.get("start", 1)),
            "padding": int(numbering.get("padding", 2)),
            "prefix": str(numbering.get("prefix", "") or ""),
            "suffix": str(numbering.get("suffix", "") or ""),
            "skip_if_numbered": bool(numbering.get("skip_if_numbered", True)),
        }
    return rules


def _stable_seed(prompt: str, mode: str) -> int:
    return abs(hash((prompt.strip().lower(), mode))) % (2**32)
