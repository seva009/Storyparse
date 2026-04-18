import re

def detect_speaker(text):
    if not text: return "THOUGHT"
    
    # Убираем технические теги в квадратных скобках в самом начале строки
    # (например, [LILITH]: -> Лилит:)
    clean_text = re.sub(r'^\[[^\]]+\]:\s*', '', text)
    
    # Теперь ищем двоеточие в остатке текста
    for sep in [":", "："]:
        if sep in clean_text:
            return clean_text.split(sep)[0].strip()
            
    return "THOUGHT"

def normalize_speaker(speaker):
    # Убираем скобки, если они остались, и переводим в нижний регистр
    # Remove common bracket/quote characters that may surround the name
    s = speaker.replace("[", "").replace("]", "")
    s = s.replace('「', '').replace('」', '').replace('“', '').replace('”', '')
    # Normalize some fullwidth punctuation used in CJK translations
    s = s.replace('？', '?').replace('！', '!')
    s = s.replace('"', '').replace("'", '').strip().lower()
    
    if s in ["you", "player", "ты", "你", "вы"]: return "YOU"
    if s in ["lilith", "лилит","странная девушка","陌生的少女","陌生少女", "strange girl","mysterious girl","таинственная девушка", "莉莉丝"]: return "LILITH"
    if s in ["thought", "мысль", "система", "system"]: return "THOUGHT"
    
    return "OTHER"

def get_node_speaker(node, translation):
    # вытаскиваем line_id
    raw_id = node.id.split(":")[-1]
    # If we have translations, check all three languages for an explicit speaker name
    # (the part before colon). Prefer any translation that contains a name. If
    # multiple translations contain different speaker names, raise an error so
    # the issue can be inspected and corrected manually.
    raw_id = node.id.split(":")[-1]

    texts = []
    if raw_id in translation:
        tr = translation[raw_id]
        texts = [tr.get('en', '') or '', tr.get('ru', '') or '', tr.get('zh', '') or '']
    else:
        texts = [node.text or '']

    candidates = []
    langs = ['en', 'ru', 'zh']
    for lang, txt in zip(langs, texts):
        if not txt:
            continue
        sp = detect_speaker(txt)
        # detect_speaker returns 'THOUGHT' when there's no explicit "Name:" at start
        if sp and sp != 'THOUGHT':
            candidates.append((lang, sp.strip()))

    # Remove duplicates while preserving order
    seen = set()
    unique_names = []
    for lang, name in candidates:
        if name not in seen:
            seen.add(name)
            unique_names.append((lang, name))

    if not unique_names:
        # Fallback to previous behavior (use English or node.text)
        text = translation[raw_id]['en'] if raw_id in translation else node.text
        speaker = detect_speaker(text)
        return normalize_speaker(speaker)

    # If multiple different explicit names found, ensure they normalize to the same speaker.
    names_only = [n for _, n in unique_names]
    norms = [normalize_speaker(n) for n in names_only]
    if len(set(norms)) == 1:
        return norms[0]

    # Conflict: different names across translations -> fail fast with useful info
    details = ", ".join([f"{lang}:'{name}'" for lang, name in unique_names])
    raise RuntimeError(f"Speaker name conflict for node {node.id}: {details}")


def classify_node(node, translation):
    speaker = get_node_speaker(node, translation)

    if speaker == "THOUGHT":
        return 0
    elif speaker == "YOU":
        return 1
    elif speaker == "LILITH":
        return 2
    else:
        return 3
    
def clean_final_text(text):
    if not text:
        return None

    # 0. Удаляем HTML/Unity rich-text теги: <color=#...>, </color>, <b>, </b> и т.п.
    #    Не трогаем наши теги-якоря (<PLAYER>, <CHAR_Lilith>, <SCENE>, <NPC_...>)
    text = re.sub(r'</?(?:color|b|i|size|material|quad)[^>]*>', '', text)

    # 1. Удаляем любые квадратные скобки, внутри которых есть технические символы:
    # =, /, {, }, ", а также специфические слова (important, lock, if)
    # Это уберет [lock if = {0} /], [important /], [char ... /]
    text = re.sub(r'\[[^\]]*[=/{}"][^\]]*\]', '', text)
    text = re.sub(r'\[\s*(important|lock|if|exit|entry)\s*/?\]', '', text, flags=re.IGNORECASE)

    # 2. Удаляем системные маркеры "Успех" и "Провал", так как это не RP-текст
    text = text.replace("[Успех]", "").replace("[Провал]", "")

    # 3. Убираем имя в начале (Лилит: , Ты: , You: и т.д.)
    text = re.sub(r'^[^\n:：]+[:：]\s*', '', text)

    # 4. Убираем остатки одиночных технических тегов типа [/]
    text = re.sub(r'\[/\]', '', text)

    # 5. Чистим лишние пробелы и переносы
    text = text.strip()

    # 6. КРИТИЧЕСКИЙ ФИЛЬТР:
    # Если после всей чистки в строке не осталось букв (только точки, тире или пустота)
    # то такая строка нам не нужна (она была либо чисто технической, либо [Успех])
    if not re.search(r'[\w\u0400-\u04FF]', text):
        return None

    return text