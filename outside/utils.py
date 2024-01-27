def a_or_an(word: str, style=None):
    if style:
        inner = f"[{style}]{word}[/{style}]"
    else:
        inner = word

    if word[0].lower() in "aeiou":
        return f"an {inner}"
    return f"a {inner}"
