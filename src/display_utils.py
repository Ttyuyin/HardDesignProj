"""Display formatting utilities — hex / codepoint strings."""


def bytes_to_hex(b: bytes) -> str:
    return " ".join(f"{b:02X}" for b in b)


def codepoint_display(char: str) -> str:
    return f"U+{ord(char):04X}"
