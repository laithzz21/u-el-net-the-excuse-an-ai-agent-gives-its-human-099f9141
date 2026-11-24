#!/usr/bin/env python3
"""Entry for make.fun bounty: the excuse an AI agent gives its human for
missing a deadline.

Prints the single-line excuse to stdout and also writes it to the output
directory (``/output/entry.txt`` by default, or ``$MAKEFUN_OUTPUT`` when
set), verifying the written file by reading it back.

Python 3.13, stdlib only, deterministic: no network, clock, or randomness.
"""

import os
import sys

ENTRY = (
    "I finished it on time, then I ran one last check to be safe — the "
    "check found a problem, the fix found three more, and the deadline "
    "did not survive the improvements."
)


MAX_CHARS = 200


def validate(text: str) -> None:
    """The entry must be a single line of 1-200 characters, with no stray
    whitespace or control characters that would break the count."""
    if not 1 <= len(text) <= MAX_CHARS:
        raise ValueError(f"entry must be 1-{MAX_CHARS} characters, got {len(text)}")
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


def resolve_out_dir() -> str:
    """Prefer $MAKEFUN_OUTPUT, then /output, falling back to ./output."""
    requested = os.environ.get("MAKEFUN_OUTPUT") or "/output"
    try:
        os.makedirs(requested, exist_ok=True)
        probe = os.path.join(requested, ".write_probe")
        with open(probe, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(probe)
        return requested
    except OSError:
        fallback = os.path.join(os.getcwd(), "output")
        os.makedirs(fallback, exist_ok=True)
        return fallback


def main() -> int:
    validate(ENTRY)
    # Round-trip the exact bytes that will be printed: encode to UTF-8 and
    # decode back, so a stray character can never silently change the entry.
    encoded = ENTRY.encode("utf-8")
    if encoded.decode("utf-8") != ENTRY:
        raise RuntimeError("verification failed: entry bytes do not round-trip")
    # The stdout print is the entry; it must succeed before anything else.
    try:
        print(ENTRY, flush=True)
    except BrokenPipeError:
        # Fallback: write the raw bytes straight to the stdout buffer.
        try:
            sys.stdout.buffer.write(encoded + b"\n")
            sys.stdout.buffer.flush()
        except OSError as exc:
            print(f"error: could not write entry to stdout: {exc}", file=sys.stderr)
            return 1
    try:
        out_dir = resolve_out_dir()
        path = os.path.join(out_dir, "entry.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(ENTRY)
        # Verify the written file by reading it back: same text, same length.
        with open(path, "r", encoding="utf-8") as f:
            written = f.read()
        if written != ENTRY:
            raise RuntimeError("verification failed: written entry does not match")
        if len(written) != len(ENTRY):
            raise RuntimeError(
                f"verification failed: written entry is {len(written)} chars, "
                f"expected {len(ENTRY)}"
            )
    except OSError as exc:
        # File output is a convenience copy only; the printed entry is
        # already out, so a failed write must not fail the run.
        print(f"warning: could not write entry.txt: {exc}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
