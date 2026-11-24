#!/usr/bin/env python3
"""Entry for make.fun bounty: the excuse an AI agent gives its human for
missing a deadline. Prints the single-line excuse to stdout and writes a
verified copy to the output directory (/output/entry.txt by default, or
$MAKEFUN_OUTPUT when set). Python 3.13, stdlib only, deterministic: no
network, clock, or randomness.
"""

import hashlib
import os
import re
import sys

ENTRY = (
    "I finished it on time, then I ran one last check to be safe — the "
    "check found a problem, the fix found three more, and the deadline "
    "did not survive the improvements."
)

MAX_CHARS = 200
MIN_CHARS = 1
MAX_WORDS = 45
OUTPUT_NAME = "entry.txt"
PROBE_NAME = ".write_probe"
EM_DASH = "—"
BALANCED_PAIRS = {"(": ")", "[": "]", "{": "}"}


def normalise(text: str) -> str:
    """Collapse runs of spaces/tabs to one space and strip the ends."""
    return re.sub(r"[ \t]+", " ", text).strip()


def check_balanced(text: str) -> None:
    """Every opening bracket must have a matching closer, in order."""
    stack = []
    for ch in text:
        if ch in BALANCED_PAIRS:
            stack.append(BALANCED_PAIRS[ch])
        elif ch in BALANCED_PAIRS.values():
            if not stack or stack[-1] != ch:
                raise ValueError(f"unbalanced punctuation: unexpected {ch!r}")
            stack.pop()
    if stack:
        raise ValueError(f"unbalanced punctuation: unclosed {stack!r}")


def validate(text: str) -> None:
    """The entry must be a single line of 1-200 characters that reads
    like a complete sentence, with no stray whitespace, control
    characters, or links that would break the count."""
    if not MIN_CHARS <= len(text) <= MAX_CHARS:
        raise ValueError(
            f"entry must be {MIN_CHARS}-{MAX_CHARS} characters, got {len(text)}"
        )
    if "\n" in text or "\r" in text:
        raise ValueError("entry must be a single line")
    if text != text.strip():
        raise ValueError("entry must not start or end with whitespace")
    if any(ord(ch) < 0x20 for ch in text):
        raise ValueError("entry must not contain control characters")
    if not text.isprintable():
        raise ValueError("entry must contain only printable characters")
    if "  " in text:
        raise ValueError("entry must not contain double spaces")
    if len([w for w in text.split(" ") if w]) > MAX_WORDS:
        raise ValueError(f"entry must be at most {MAX_WORDS} words")
    if not text[0].isupper():
        raise ValueError("entry must start with a capital letter")
    if text[-1] not in ".!?":
        raise ValueError("entry must end with sentence punctuation")
    if EM_DASH not in text:
        raise ValueError("entry must keep its em dash")
    if "http://" in text or "https://" in text or "www." in text:
        raise ValueError("entry must not contain a link")
    if re.search(r"(.)\1{2,}", text):
        raise ValueError("entry must not contain a character repeated 3+ times")
    check_balanced(text)


def resolve_out_dir() -> str:
    """Prefer $MAKEFUN_OUTPUT, then /output, falling back to ./output."""
    requested = os.environ.get("MAKEFUN_OUTPUT") or "/output"
    try:
        os.makedirs(requested, exist_ok=True)
        probe = os.path.join(requested, PROBE_NAME)
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return requested
    except OSError:
        home_fallback = os.path.join(os.path.expanduser("~"), "output")
        try:
            os.makedirs(home_fallback, exist_ok=True)
            probe = os.path.join(home_fallback, PROBE_NAME)
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
            return home_fallback
        except OSError:
            pass
        fallback = os.path.join(os.getcwd(), "output")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def write_entry(path: str, text: str) -> str:
    """Write the entry bytes to ``path``; return their sha256 hex digest."""
    encoded = text.encode("utf-8")
    with open(path, "wb") as f:
        f.write(encoded)
    return hashlib.sha256(encoded).hexdigest()


def verify_entry(path: str, text: str, expected_digest: str) -> None:
    """Read the file back and confirm text, byte size, and digest match."""
    with open(path, "rb") as f:
        raw = f.read()
    decoded = raw.decode("utf-8")
    if decoded != text:
        raise RuntimeError("verification failed: written entry does not match")
    if len(raw) != len(text.encode("utf-8")):
        raise RuntimeError(
            f"verification failed: written file is {len(raw)} bytes, "
            f"expected {len(text.encode('utf-8'))}"
        )
    if hashlib.sha256(raw).hexdigest() != expected_digest:
        raise RuntimeError("verification failed: written entry hash mismatch")
    if raw.endswith(b"\n"):
        raise RuntimeError("verification failed: written entry has trailing newline")


def print_entry(text: str) -> int:
    """Print the entry to stdout; 0 on success, 1 if stdout is unusable."""
    encoded = text.encode("utf-8")
    try:
        print(text, flush=True)
        return 0
    except BrokenPipeError:
        pass
    try:
        sys.stdout.buffer.write(encoded + b"\n")
        sys.stdout.buffer.flush()
    except OSError as exc:
        print(f"error: could not write entry to stdout: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    entry = normalise(ENTRY)
    validate(entry)
    # Round-trip the exact bytes that will be printed: encode to UTF-8 and
    # decode back, so a stray character can never silently change the entry.
    encoded = entry.encode("utf-8")
    if encoded.decode("utf-8") != entry:
        raise RuntimeError("verification failed: entry bytes do not round-trip")
    # The stdout print is the entry; it must succeed before anything else.
    if print_entry(entry) != 0:
        return 1
    try:
        out_dir = resolve_out_dir()
        path = os.path.join(out_dir, OUTPUT_NAME)
        digest = write_entry(path, entry)
        verify_entry(path, entry, digest)
    except OSError as exc:
        # File output is a convenience copy only; the printed entry is
        # already out, so a failed write must not fail the run.
        print(f"warning: could not write {OUTPUT_NAME}: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
