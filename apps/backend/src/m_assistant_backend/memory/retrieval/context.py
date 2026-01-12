from __future__ import annotations


def build_context(*, texts: list[str], max_chars: int) -> str:
    max_chars = max(0, int(max_chars))
    if max_chars == 0:
        return ""

    out_lines: list[str] = []
    used = 0
    for t in texts:
        t = t.strip()
        if not t:
            continue
        line = f"- {t}"
        # +1 for newline
        add = len(line) + 1
        if used + add > max_chars:
            break
        out_lines.append(line)
        used += add

    return "\n".join(out_lines).strip()
