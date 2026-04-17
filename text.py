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
    s = speaker.replace("[", "").replace("]", "").strip().lower()
    
    if s in ["you", "player", "ты"]: return "YOU"
    if s in ["lilith", "???", "strange girl", "莉莉丝"]: return "LILITH"
    if s in ["thought", "мысль", "система", "system"]: return "THOUGHT"
    
    return "OTHER"

def get_node_speaker(node, translation):
    # вытаскиваем line_id
    raw_id = node.id.split(":")[-1]

    if raw_id in translation:
        text = translation[raw_id]["en"]
    else:
        text = node.text  # fallback

    speaker = detect_speaker(text)
    return normalize_speaker(speaker)


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