#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path


API_URL = "https://api.jiekou.ai/v3/gemini-3-pro-image-text-to-image"
DEFAULT_MODE = "method-overview"
SUPPORTED_MODES = {"teaser", "method-overview", "visual-abstract", "system-concept"}


def read_text(path_str: str) -> str:
    if path_str == "-":
        return sys.stdin.read()
    return Path(path_str).read_text(encoding="utf-8")


def detect_title(text: str) -> str:
    for line in text.splitlines():
        raw = line.strip()
        if raw.startswith("#"):
            return raw.lstrip("#").strip()
    for line in text.splitlines():
        raw = line.strip()
        if raw and len(raw) <= 80:
            return raw
    return "Untitled Research Figure"


def compact_text(text: str, limit: int = 1500) -> str:
    lines = []
    for line in text.splitlines():
        raw = line.strip()
        raw = re.sub(r"^#+\s*", "", raw)
        raw = re.sub(r"^\s*[-*+]\s*", "", raw)
        raw = raw.replace("`", "")
        raw = re.sub(r"\s+", " ", raw)
        if not raw:
            continue
        if raw.startswith(("```", "---")):
            continue
        lines.append(raw)
    cleaned = " ".join(lines)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + " ..."


def mode_instructions(mode: str) -> str:
    mapping = {
        "teaser": "Create a visually striking paper teaser with one dominant composition and a few strong supporting scientific elements.",
        "method-overview": "Create a structured method illustration with clear stages, limited readable labels, and a paper-friendly left-to-right or layered composition.",
        "visual-abstract": "Create a balanced visual abstract that summarizes the whole paper at a glance with a clean publication style.",
        "system-concept": "Create a scientific system concept illustration that emphasizes the system, its environment, and the major interactions.",
    }
    return mapping[mode]


def shared_constraints() -> str:
    return (
        "Use a clean academic illustration style, publication-quality composition, white or very light background, "
        "minimal clutter, sparse readable labels only, no watermark, no UI screenshot look, and no generic stock-photo look."
    )


def build_prompt(source_text: str, mode: str, extra_prompt: str | None, title: str | None) -> str:
    resolved_title = title or detect_title(source_text)
    compact = compact_text(source_text)
    sections = [
        f"Create a research paper illustration titled '{resolved_title}'.",
        mode_instructions(mode),
        shared_constraints(),
        "Main scientific content to visualize:",
        compact,
        "Focus on the core scientific story rather than decorative detail.",
    ]
    if mode == "method-overview":
        sections.append(
            "If the method has multiple stages, show a clear composition with a few major modules or agents and one visible feedback loop if important."
        )
    if extra_prompt:
        sections.append("Additional user constraints:")
        sections.append(extra_prompt.strip())
    return "\n".join(sections)


def resolve_api_key() -> str:
    for env_name in ("BANANA_API_KEY", "API_KEY"):
        value = os.environ.get(env_name)
        if value:
            return value
    raise RuntimeError("Missing API key. Set BANANA_API_KEY or API_KEY before running this script.")


def ensure_output_path(output: str | None, output_format: str) -> Path:
    if output:
        return Path(output)
    ext = ".png" if output_format == "image/png" else ".jpg"
    return Path(f"banana-paper-illustration{ext}")


def decode_json_image(payload: dict) -> bytes | None:
    candidates = []
    if isinstance(payload.get("data"), str):
        candidates.append(payload["data"])
    if isinstance(payload.get("image"), str):
        candidates.append(payload["image"])
    images = payload.get("images")
    if isinstance(images, list):
        for item in images:
            if isinstance(item, str):
                candidates.append(item)
            elif isinstance(item, dict):
                for key in ("b64_json", "data", "image"):
                    if isinstance(item.get(key), str):
                        candidates.append(item[key])
    for candidate in candidates:
        try:
            return base64.b64decode(candidate)
        except Exception:
            continue
    return None


def first_image_url(payload: dict) -> str | None:
    for key in ("image_url", "url"):
        value = payload.get(key)
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    image_urls = payload.get("image_urls")
    if isinstance(image_urls, list):
        for item in image_urls:
            if isinstance(item, str) and item.startswith(("http://", "https://")):
                return item
    images = payload.get("images")
    if isinstance(images, list):
        for item in images:
            if isinstance(item, dict):
                for key in ("url", "image_url"):
                    value = item.get(key)
                    if isinstance(value, str) and value.startswith(("http://", "https://")):
                        return value
    return None


def download_url(url: str, output_path: Path, timeout: int) -> None:
    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Image URL HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Image URL download failed: {exc}") from exc
    output_path.write_bytes(data)


def write_prompt_file(output_path: Path, prompt: str) -> Path:
    prompt_path = output_path.with_suffix(output_path.suffix + ".prompt.txt")
    prompt_path.write_text(prompt + "\n", encoding="utf-8")
    return prompt_path


def make_request(
    prompt: str,
    api_key: str,
    output_path: Path,
    aspect_ratio: str,
    size: str,
    output_format: str,
    web_search: bool,
    timeout: int,
) -> tuple[Path, Path]:
    payload = {
        "size": size,
        "google": {"web_search": web_search},
        "prompt": prompt,
        "aspect_ratio": aspect_ratio,
        "output_format": output_format,
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        API_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    prompt_path = write_prompt_file(output_path, prompt)

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            content_type = response.headers.get("Content-Type", "")
            data = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc}") from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if content_type.startswith("image/"):
        output_path.write_bytes(data)
        return output_path, prompt_path

    try:
        payload = json.loads(data.decode("utf-8"))
    except Exception as exc:
        raise RuntimeError("API returned non-image, non-JSON content.") from exc

    image_bytes = decode_json_image(payload)
    if image_bytes is not None:
        output_path.write_bytes(image_bytes)
        return output_path, prompt_path

    image_url = first_image_url(payload)
    if image_url:
        download_url(image_url, output_path, timeout)
        return output_path, prompt_path

    raise RuntimeError("API returned JSON but no decodable image payload or image URL was found.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a paper-style illustration via the Banana text-to-image API.")
    parser.add_argument("--prompt", help="Direct prompt to send to the API.")
    parser.add_argument("--source-file", help="Source Markdown/text file used to derive the prompt.")
    parser.add_argument("--mode", default=DEFAULT_MODE, choices=sorted(SUPPORTED_MODES))
    parser.add_argument("--title", help="Optional explicit figure title.")
    parser.add_argument("--extra-prompt", help="Additional prompt constraints appended after the source-derived prompt.")
    parser.add_argument("--aspect-ratio", default="16:9")
    parser.add_argument("--size", default="1K")
    parser.add_argument("--output-format", default="image/png", choices=["image/png", "image/jpeg"])
    parser.add_argument("--output", help="Output image path.")
    parser.add_argument("--web-search", action="store_true", help="Enable Google web search in the upstream API request.")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved prompt and output paths without calling the API.")
    args = parser.parse_args()

    if not args.prompt and not args.source_file:
        parser.error("Provide either --prompt or --source-file.")

    source_text = ""
    if args.source_file:
        source_text = read_text(args.source_file)
    prompt = args.prompt or build_prompt(source_text, args.mode, args.extra_prompt, args.title)
    output_path = ensure_output_path(args.output, args.output_format).resolve()

    if args.dry_run:
        prompt_path = write_prompt_file(output_path, prompt)
        print(f"output={output_path}")
        print(f"prompt_file={prompt_path}")
        print("--- prompt ---")
        print(prompt)
        return 0

    api_key = resolve_api_key()
    try:
        image_path, prompt_path = make_request(
            prompt=prompt,
            api_key=api_key,
            output_path=output_path,
            aspect_ratio=args.aspect_ratio,
            size=args.size,
            output_format=args.output_format,
            web_search=args.web_search,
            timeout=args.timeout,
        )
    except RuntimeError as exc:
        print(f"[generate_banana_illustration] {exc}", file=sys.stderr)
        return 1

    print(image_path)
    print(prompt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
