# --- ТОКЕНИЗАЦИЯ ---
# Бюджет токенов на одно обучающее окно (одинаков для всех языков,
# но окно будет разного размера т.к. токены считаются для каждого языка отдельно)
MAX_TOKENS = 1024

# Жёсткий потолок в блоках (speaker turns) независимо от токенов
MAX_WINDOW_TURNS = 50

# Пытаемся загрузить настоящий токенайзер (tiktoken cl100k_base).
# Установка: pip install tiktoken
try:
    import tiktoken as _tiktoken
    _ENC = _tiktoken.get_encoding("cl100k_base")

    def estimate_tokens(text: str) -> int:
        return max(1, len(_ENC.encode(text)))

    print("[tokenizer] tiktoken cl100k_base loaded ✓")

except Exception:
    import re as _re

    _WORD_RE = _re.compile(
        r"[\s]?[a-zA-Zа-яёА-ЯЁ\u4e00-\u9fff]+|[0-9]+|[^\w\s]",
        _re.UNICODE,
    )
    _CYR = range(0x0400, 0x04FF)
    _CJK = range(0x4E00, 0x9FFF)

    def _word_tokens(word: str) -> int:
        stripped = word.strip()
        if not stripped:
            return 1
        cp = ord(stripped[0])
        if cp in _CYR:
            return max(1, round(len(stripped) / 2.0))   # кириллица ~2 символа/токен
        if cp in _CJK:
            return len(stripped)                         # CJK: каждый иероглиф ~ токен
        return max(1, round(len(stripped) / 3.5))        # ASCII ~3.5 символа/токен

    def estimate_tokens(text: str) -> int:
        chunks = _WORD_RE.findall(text)
        if not chunks:
            return max(1, len(text) // 4)
        return max(1, sum(_word_tokens(c) for c in chunks))

    print("[tokenizer] tiktoken unavailable, using Unicode-aware fallback")

def find_window_size(token_counts: list, max_tokens: int) -> int:
    """
    Жадно набирает блоки реплик, пока не превысим max_tokens или MAX_WINDOW_TURNS.
    Возвращает кол-во блоков в окне (минимум 2).
    """
    total = 0
    for i, tc in enumerate(token_counts):
        if i >= MAX_WINDOW_TURNS:
            return i
        total += tc
        if total > max_tokens:
            return max(2, i)
    return min(max(2, len(token_counts)), MAX_WINDOW_TURNS)