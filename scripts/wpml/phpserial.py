"""Minimal PHP serialize()/unserialize() with correct UTF-8 BYTE lengths.

The whole point of this module is the `s:<n>:"..."` prefix: PHP counts BYTES,
not characters. "qualité" is 7 characters and 8 bytes. Getting it wrong makes
PHP's unserialize() return false and WordPress silently drops the meta value.
"""


class PHPSerialError(ValueError):
    pass


def loads(text):
    value, index = _parse(text, 0)
    if index != len(text):
        raise PHPSerialError(f"trailing data at byte {index}")
    return value


def dumps(value):
    if value is None:
        return "N;"
    if isinstance(value, bool):
        return f"b:{1 if value else 0};"
    if isinstance(value, int):
        return f"i:{value};"
    if isinstance(value, float):
        return f"d:{value!r};"
    if isinstance(value, str):
        return f's:{len(value.encode("utf-8"))}:"{value}";'
    if isinstance(value, dict):
        body = "".join(dumps(k) + dumps(v) for k, v in value.items())
        return f"a:{len(value)}:{{{body}}}"
    if isinstance(value, (list, tuple)):
        body = "".join(dumps(i) + dumps(v) for i, v in enumerate(value))
        return f"a:{len(value)}:{{{body}}}"
    raise PHPSerialError(f"cannot serialize {type(value).__name__}")


def is_serialized(text):
    return isinstance(text, str) and text[:2] in ("a:", "s:", "i:", "b:", "d:", "O:") or text == "N;"


def _parse(text, i):
    kind = text[i:i + 2]
    if kind == "N;":
        return None, i + 2
    if kind == "b:":
        return text[i + 2] == "1", i + 4
    if kind == "i:":
        end = text.index(";", i)
        return int(text[i + 2:end]), end + 1
    if kind == "d:":
        end = text.index(";", i)
        return float(text[i + 2:end]), end + 1
    if kind == "s:":
        colon = text.index(":", i + 2)
        nbytes = int(text[i + 2:colon])
        start = colon + 2                       # skip the opening quote
        # Walk forward until exactly nbytes of UTF-8 have been consumed.
        consumed, end = 0, start
        while consumed < nbytes:
            consumed += len(text[end].encode("utf-8"))
            end += 1
        if consumed != nbytes:
            raise PHPSerialError(f"string length {nbytes} splits a character at {i}")
        if text[end:end + 2] != '";':
            raise PHPSerialError(f"string at {i} is not terminated by \";")
        return text[start:end], end + 2
    if kind == "a:":
        colon = text.index(":", i + 2)
        count = int(text[i + 2:colon])
        i = colon + 2                           # skip ':{'
        out = {}
        for _ in range(count):
            key, i = _parse(text, i)
            val, i = _parse(text, i)
            out[key] = val
        if text[i] != "}":
            raise PHPSerialError(f"array at {i} is not closed")
        return out, i + 1
    raise PHPSerialError(f"unknown type {kind!r} at byte {i}")


def translate_in_place(text, keys, translate):
    """Re-emit a serialized blob with `keys` passed through `translate`.

    Walks nested arrays. Only string values stored under a whitelisted key are
    touched; every other value, and the whole array shape, is preserved.
    """
    if not text.strip():
        return text
    data = loads(text)

    def walk(node):
        if isinstance(node, dict):
            return {k: (translate(v) if k in keys and isinstance(v, str) else walk(v))
                    for k, v in node.items()}
        return node

    return dumps(walk(data))
