"""Build CharacterToken instances from raw file bytes."""

from pathlib import Path

from shared.character_token import CharacterToken


def tokens_from_bytes(
    raw_data: bytes,
    display_name: str,
    std_name: str,
    file_path: str | Path,
) -> list[CharacterToken]:
    """将字节序列解码为 CharacterToken 列表，保留原始字节偏移"""
    if not raw_data:
        return []

    file_path = Path(file_path)
    if std_name in ("utf-16", "utf-16-le", "utf-16-be"):
        return _tokens_from_utf16(raw_data, display_name, std_name, str(file_path))

    bom_len = 0
    reencode_name = std_name
    if std_name == "utf-8-sig":
        reencode_name = "utf-8"
        bom_len = 3

    text = raw_data.decode(std_name, errors="surrogateescape")
    tokens = []
    byte_pos = bom_len
    for char in text:
        char_bytes = char.encode(reencode_name, errors="surrogateescape")
        source_bytes = raw_data[byte_pos:byte_pos + len(char_bytes)]
        display_char = "?" if 0xDC00 <= ord(char) <= 0xDCFF else char
        tokens.append(_make_token(display_char, display_name, file_path, source_bytes))
        byte_pos += len(char_bytes)

    return tokens


def _tokens_from_utf16(
    raw_data: bytes,
    display_name: str,
    std_name: str,
    file_path: str,
) -> list[CharacterToken]:
    """UTF-16 专用 tokenization（surrogateescape 不支持 UTF-16）"""
    bom_len = 0
    reencode_name = std_name
    if std_name == "utf-16":
        reencode_name = "utf-16-le" if raw_data[:2] == b"\xff\xfe" else "utf-16-be"
        bom_len = 2

    text = raw_data.decode(std_name, errors="replace")
    tokens = []
    byte_pos = bom_len
    for char in text:
        try:
            char_bytes = char.encode(reencode_name)
        except UnicodeEncodeError:
            step = 2
            source_bytes = raw_data[byte_pos:byte_pos + step]
            byte_pos += step
            tokens.append(_make_token(char, display_name, file_path, source_bytes))
            continue

        source_bytes = raw_data[byte_pos:byte_pos + len(char_bytes)]
        byte_pos += len(char_bytes)
        tokens.append(_make_token(char, display_name, file_path, source_bytes))

    return tokens


def _make_token(
    char: str,
    display_name: str,
    file_path: str | Path,
    source_bytes: bytes,
) -> CharacterToken:
    """构造一个 CharacterToken 实例"""
    return CharacterToken(
        char=char,
        source_encoding=display_name,
        source_file=str(file_path),
        source_bytes=source_bytes,
    )
