"""
lolmake.py  —  датасет-генератор v2

Изменения:
  • Теги: <PLAYER>, <CHAR_Lilith>, <NPC_Name>, <NPC_Crowd>, <SCENE>
  • Диалоги с NPC тоже включены (не только YOU+LILITH)
  • Спрайты Лилит → *эмоция* перед репликой
  • <SCENE> из back_creat команд
  • Очистка всех game-тегов, #line: ID, цветовых тегов
  • Пример начинается с <PLAYER>, заканчивается на <CHAR_Lilith>
"""

import os
import re
import json
from collections import Counter

from text import detect_speaker, normalize_speaker, clean_final_text
from translate import load_translation
from graph import build_graph
from subgraphs import find_valid_subgraphs, extract_all_paths
from tokenizer import MAX_TOKENS, find_window_size, estimate_tokens, MAX_WINDOW_TURNS

# ─────────────────────────────────────────────────────────────
#  EMOTION MAPS  (expression_id → описание)
# ─────────────────────────────────────────────────────────────

LILITH_EMOTIONS = {
    'ru': {
        0: "невозмутимо", 1: "спокойно", 2: "слегка улыбаясь",
        3: "с лёгкой усмешкой", 4: "мягко улыбаясь", 5: "задумчиво",
        6: "внимательно глядя", 7: "с любопытством", 8: "удивлённо",
        9: "с тёплой улыбкой", 10: "слегка оживившись", 11: "с лёгкой тревогой",
        12: "серьёзно", 13: "холодно", 14: "с лёгкой грустью",
        15: "задумавшись", 16: "смущённо", 17: "нахмурившись",
        18: "безучастно", 19: "взволнованно", 20: "недовольно",
        21: "сердито", 22: "испуганно", 23: "растерянно",
        24: "устало", 25: "с болью", 26: "с горечью",
        27: "почти шёпотом", 28: "с тихой грустью", 29: "с тоской",
        30: "неуверенно", 31: "искренне удивившись", 32: "с облегчением",
        33: "радостно", 34: "отстранённо", 35: "смущённо-растерянно",
        36: "ошеломлённо", 37: "с нескрываемым смущением", 38: "с благодарностью",
        39: "с лёгкой иронией", 40: "решительно", 41: "торжественно",
        42: "с сомнением", 43: "тепло-сдержанно",
    },
    'en': {
        0: "impassively", 1: "calmly", 2: "with a faint smile",
        3: "with a slight smirk", 4: "smiling gently", 5: "thoughtfully",
        6: "attentively", 7: "curiously", 8: "in surprise",
        9: "with a warm smile", 10: "brightening slightly", 11: "with faint unease",
        12: "seriously", 13: "coldly", 14: "with mild sadness",
        15: "lost in thought", 16: "flustered", 17: "frowning",
        18: "indifferently", 19: "agitated", 20: "displeased",
        21: "angrily", 22: "frightened", 23: "confused",
        24: "wearily", 25: "pained", 26: "with bitterness",
        27: "almost whispering", 28: "with quiet sadness", 29: "longingly",
        30: "hesitantly", 31: "genuinely astonished", 32: "with relief",
        33: "joyfully", 34: "detachedly", 35: "flustered and lost",
        36: "stunned", 37: "visibly embarrassed", 38: "gratefully",
        39: "with a touch of irony", 40: "resolutely", 41: "solemnly",
        42: "doubtfully", 43: "warmly yet composed",
    },
    'zh': {
        0: "面无表情地", 1: "平静地", 2: "微微一笑",
        3: "轻轻一哂", 4: "温柔地笑着", 5: "若有所思地",
        6: "专注地望着", 7: "好奇地", 8: "惊讶地",
        9: "带着温柔的微笑", 10: "微微振作", 11: "隐隐不安",
        12: "严肃地", 13: "冷淡地", 14: "略显忧郁",
        15: "陷入沉思", 16: "慌乱地", 17: "皱眉道",
        18: "漠然地", 19: "激动地", 20: "不悦地",
        21: "愤怒地", 22: "惊恐地", 23: "茫然地",
        24: "疲倦地", 25: "痛苦地", 26: "带着苦涩",
        27: "几乎轻声呢喃", 28: "带着淡淡的忧伤", 29: "怅然地",
        30: "迟疑地", 31: "真诚地惊愕", 32: "如释重负地",
        33: "欢欣地", 34: "疏离地", 35: "慌张而迷茫地",
        36: "震惊地", 37: "明显局促", 38: "感激地",
        39: "带着一丝讽意", 40: "坚定地", 41: "庄重地",
        42: "将信将疑地", 43: "温柔而克制地",
    },
}

# ─────────────────────────────────────────────────────────────
#  SCENE MAPS  (bg_name → локация)
# ─────────────────────────────────────────────────────────────

BG_SCENES = {
    'ru': {
        'BG-0': 'Гильдия. День.', 'BG_GUILD': 'Гильдия. День.',
        'BG-1': 'Гильдия. День.', 'BG-2': 'Гильдия. Вечер.',
        'BG-3': 'Городская улица. День.', 'BG-4': 'Городская улица. Вечер.',
        'BG-5': 'Рынок. День.', 'BG-6': 'Таверна.',
        'BG-7': 'Таверна. Ночь.', 'BG-8': 'Карета. День.',
        'BG-8-2': 'Карета. Ночь.', 'BG-9': 'Лес.',
        'BG-10': 'Руины.', 'BG-13': 'Замок.',
        'BG-16': 'Подземелье.', 'BG-17': 'Библиотека.',
        'BG-20': 'Городская площадь.', 'BG-24-2': 'Берег реки.',
        'BF-2': 'Поле боя. День.', 'BF-4': 'Поле боя. Вечер.',
        'BF-5': 'Поле боя. Ночь.', 'SKY': 'Под открытым небом.',
        'AFTERTRAIN': 'Тренировочный зал. После занятий.',
    },
    'en': {
        'BG-0': 'Guild hall. Daytime.', 'BG_GUILD': 'Guild hall. Daytime.',
        'BG-1': 'Guild hall. Daytime.', 'BG-2': 'Guild hall. Evening.',
        'BG-3': 'City street. Daytime.', 'BG-4': 'City street. Evening.',
        'BG-5': 'Market. Daytime.', 'BG-6': 'Tavern.',
        'BG-7': 'Tavern. Night.', 'BG-8': 'Carriage. Daytime.',
        'BG-8-2': 'Carriage. Night.', 'BG-9': 'Forest.',
        'BG-10': 'Ruins.', 'BG-13': 'Castle.',
        'BG-16': 'Dungeon.', 'BG-17': 'Library.',
        'BG-20': 'Town square.', 'BG-24-2': 'Riverbank.',
        'BF-2': 'Battlefield. Daytime.', 'BF-4': 'Battlefield. Evening.',
        'BF-5': 'Battlefield. Night.', 'SKY': 'Open sky.',
        'AFTERTRAIN': 'Training hall. After practice.',
    },
    'zh': {
        'BG-0': '公会大厅。白天。', 'BG_GUILD': '公会大厅。白天。',
        'BG-1': '公会大厅。白天。', 'BG-2': '公会大厅。傍晚。',
        'BG-3': '城市街道。白天。', 'BG-4': '城市街道。傍晚。',
        'BG-5': '市场。白天。', 'BG-6': '酒馆。',
        'BG-7': '酒馆。夜晚。', 'BG-8': '马车。白天。',
        'BG-8-2': '马车。夜晚。', 'BG-9': '森林。',
        'BG-10': '废墟。', 'BG-13': '城堡。',
        'BG-16': '地下城。', 'BG-17': '图书馆。',
        'BG-20': '广场。', 'BG-24-2': '河岸。',
        'BF-2': '战场。白天。', 'BF-4': '战场。傍晚。',
        'BF-5': '战场。夜晚。', 'SKY': '露天之下。',
        'AFTERTRAIN': '训练场。练习结束后。',
    },
}

# ─────────────────────────────────────────────────────────────
#  YARN METADATA EXTRACTOR
# ─────────────────────────────────────────────────────────────

LINE_RE = re.compile(r'#line:([0-9a-f]+)')
BG_RE   = re.compile(r'<<back_creat\s+(\S+)', re.IGNORECASE)
CHAR_RE = re.compile(r'<<char(?:_creat)?\s+Lilith\S*\s+\d+\s+(\d+)', re.IGNORECASE)


def extract_yarn_metadata(yarn_folder):
    """Возвращает {line_id: bg_name_upper}, {line_id: emotion_id}"""
    node_bg = {}
    node_emotion = {}

    for fname in os.listdir(yarn_folder):
        if not fname.endswith('.yarn'):
            continue
        with open(os.path.join(yarn_folder, fname), encoding='utf-8') as fh:
            lines = fh.readlines()

        current_bg = None
        current_emotion = None

        for raw in lines:
            s = raw.strip()
            m_bg = BG_RE.search(s)
            if m_bg:
                current_bg = m_bg.group(1).upper()

            m_em = CHAR_RE.search(s)
            if m_em:
                current_emotion = int(m_em.group(1))

            m_line = LINE_RE.search(s)
            if m_line:
                lid = m_line.group(1)
                if current_bg is not None:
                    node_bg[lid] = current_bg
                if current_emotion is not None:
                    node_emotion[lid] = current_emotion

    return node_bg, node_emotion


# ─────────────────────────────────────────────────────────────
#  SPEAKER CLASSIFICATION
# ─────────────────────────────────────────────────────────────

NAMED_NPC = {
    'kallen': 'Kallen', 'green': 'Green', 'fouco': 'Fouco',
    'sartre': 'Sartre', 'karen': 'Karen', 'eileen': 'Eileen',
    'doria': 'Doria', 'ronnie': 'Ronnie', 'toru': 'Toru',
    'tom': 'Tom', 'wilson': 'Wilson', 'jerry': 'Jerry',
    'ander': 'Ander', 'andre': 'Andre', 'justus': 'Justus',
}


def get_npc_tag(raw_speaker: str) -> str:
    s = raw_speaker.strip().lower()
    for key, tag in NAMED_NPC.items():
        if key in s:
            return f'NPC_{tag}'
    return 'NPC_Crowd'


def classify_speaker(en_text: str) -> str:
    """YOU | LILITH | THOUGHT | NPC_<Name> | NPC_Crowd"""
    raw  = detect_speaker(en_text)
    norm = normalize_speaker(raw)
    if norm in ('YOU', 'LILITH', 'THOUGHT'):
        return norm
    return get_npc_tag(raw)


# ─────────────────────────────────────────────────────────────
#  ФИЛЬТР ПУТЕЙ
# ─────────────────────────────────────────────────────────────

def is_real_dialog(path, translation):
    """Путь валиден: есть YOU и LILITH."""
    speakers = set()
    for nid in path:
        raw_id = nid.split(':')[-1]
        if raw_id in translation:
            speakers.add(classify_speaker(translation[raw_id]['en']))
    return 'YOU' in speakers and 'LILITH' in speakers


# ─────────────────────────────────────────────────────────────
#  ФОРМАТИРОВАНИЕ РЕПЛИКИ
# ─────────────────────────────────────────────────────────────

def format_message(sp_type: str, text: str, emotion_id=None, lang='ru') -> str:
    if sp_type == 'YOU':
        return f'<PLAYER> {text}'
    if sp_type == 'LILITH':
        emo = LILITH_EMOTIONS.get(lang, {}).get(emotion_id) if emotion_id is not None else None
        if emo:
            return f'<CHAR_Lilith> *{emo}* {text}'
        return f'<CHAR_Lilith> {text}'
    if sp_type == 'THOUGHT':
        return f'<PLAYER> *{text}*'
    # NPC
    tag = sp_type  # уже вида NPC_Kallen или NPC_Crowd
    return f'<{tag}> {text}'


def get_scene_tag(line_id: str, node_bg: dict, lang: str):
    bg = node_bg.get(line_id)
    if not bg:
        return None
    scenes = BG_SCENES.get(lang, BG_SCENES['en'])
    label  = scenes.get(bg.upper(), bg)
    return f'<SCENE> {label} </SCENE>'


# ─────────────────────────────────────────────────────────────
#  СБОРКА БЛОКОВ
# ─────────────────────────────────────────────────────────────

def create_speaker_blocks(path, translation, node_bg, node_emotion, lang):
    blocks = []
    current = None
    last_scene = None

    for nid in path:
        raw_id = nid.split(':')[-1]
        if raw_id not in translation:
            continue

        en_text  = translation[raw_id].get('en', '')
        tgt_text = translation[raw_id].get(lang, '')
        cleaned  = clean_final_text(tgt_text)
        if not cleaned:
            continue

        sp_type = classify_speaker(en_text)
        emotion = node_emotion.get(raw_id)

        scene_tag = get_scene_tag(raw_id, node_bg, lang)
        scene_changed = scene_tag and scene_tag != last_scene
        if scene_changed:
            last_scene = scene_tag

        same_role = current and current['role'] == sp_type and not scene_changed
        if same_role:
            current['lines'].append(cleaned)
            if emotion is not None:
                current['emotion'] = emotion
        else:
            if current:
                blocks.append(current)
            current = {
                'role': sp_type,
                'lines': [cleaned],
                'scene': scene_tag if scene_changed else None,
                'emotion': emotion,
            }

    if current:
        blocks.append(current)

    return blocks


# ─────────────────────────────────────────────────────────────
#  REFINE WINDOW
# ─────────────────────────────────────────────────────────────

def refine_window_v2(system_content, blocks, lang):
    if not blocks:
        return None

    processed = []
    for b in blocks:
        text  = '\n'.join(b['lines'])
        fmted = format_message(b['role'], text, b.get('emotion'), lang)
        if b.get('scene'):
            fmted = b['scene'] + '\n' + fmted

        chat_role = 'assistant' if b['role'] == 'LILITH' else 'user'
        processed.append({'role': chat_role, 'content': fmted})

    # Начинаем с user
    while processed and processed[0]['role'] != 'user':
        processed.pop(0)

    # Склеиваем одинаковые роли
    merged = []
    for msg in processed:
        if merged and merged[-1]['role'] == msg['role']:
            merged[-1]['content'] += '\n' + msg['content']
        else:
            merged.append(dict(msg))

    # Заканчиваем на assistant
    while merged and merged[-1]['role'] != 'assistant':
        merged.pop()

    if len(merged) < 2:
        return None

    return {'messages': [{'role': 'system', 'content': system_content}] + merged}


# ─────────────────────────────────────────────────────────────
#  SYSTEM PROMPTS
# ─────────────────────────────────────────────────────────────

SYSTEM_PROMPTS = {
    'ru': (
        'Ты — Лилит, таинственная участница гильдии Huis Clos. '
        'Ты предана Гильдмастеру (ГГ). В твоих словах иногда чувствуется '
        'недосказанность и лёгкая мистика. '
        'Свои действия и внутреннее состояние описывай в *звёздочках*. '
        'Всегда отвечай как <CHAR_Lilith>.'
    ),
    'en': (
        'You are Lilith, a mysterious member of the Huis Clos guild. '
        'You are devoted to the Guild Master (the protagonist). '
        'Your words carry an undertone of mystique and subtle depth. '
        'Describe your actions and inner state in *asterisks*. '
        'Always respond as <CHAR_Lilith>.'
    ),
    'zh': (
        '你是莉莉丝（Lilith），Huis Clos 公会的一名神秘成员。'
        '你效忠于公会首领（男主角）。'
        '你的话语中偶尔透出言外之意和淡淡的神秘感。'
        '用*星号*描述你的动作和内心状态。'
        '始终以 <CHAR_Lilith> 身份回应。'
    ),
}


# ─────────────────────────────────────────────────────────────
#  SAVE DATASET
# ─────────────────────────────────────────────────────────────

def save_refined_dataset(all_paths, translation, node_bg, node_emotion,
                         output_file, lang='ru'):
    sys_content = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS['en'])
    dataset = []
    diag_blocks = Counter()
    diag_ws     = Counter()

    for path in all_paths:
        blocks = create_speaker_blocks(path, translation, node_bg, node_emotion, lang)
        diag_blocks[len(blocks)] += 1
        if len(blocks) < 2:
            continue

        token_counts = [estimate_tokens('\n'.join(b['lines'])) for b in blocks]
        window_size  = find_window_size(token_counts, MAX_TOKENS)
        diag_ws[window_size] += 1
        step = 5 if window_size >= 20 else 1

        for i in range(0, max(1, len(blocks) - window_size + 1), step):
            ex = refine_window_v2(sys_content, blocks[i:i+window_size], lang)
            if ex:
                dataset.append(ex)

    unique = {json.dumps(ex, sort_keys=True, ensure_ascii=False): ex for ex in dataset}

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in unique.values():
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    n = len(unique)
    avg = sum(len(ex['messages'])-1 for ex in unique.values()) / n if n else 0
    print(f'  [diag] blocks/path  : {dict(sorted(diag_blocks.items())[:8])}')
    print(f'  [diag] window_sizes : {dict(sorted(diag_ws.items())[:8])}')
    print(f'[{lang}] {n} examples → {output_file}  (avg turns: {avg:.1f})')
    return n


# ─────────────────────────────────────────────────────────────
#  STATS
# ─────────────────────────────────────────────────────────────

def print_final_stats(real_paths, datasets_by_lang):
    print('\n' + '='*45)
    print('            DATASET STATISTICS')
    print('='*45)
    print(f'Valid dialog paths: {len(real_paths)}')
    for lang, ds in datasets_by_lang.items():
        if not ds:
            continue
        msg_c = [len(d['messages']) for d in ds]
        chars = [sum(len(m['content']) for m in d['messages']) for d in ds]
        print(f'\n  [{lang.upper()}]  examples={len(ds)}  avg_turns={sum(msg_c)/len(msg_c):.1f}'
              f'  avg_chars={sum(chars)/len(chars):.0f}  max_chars={max(chars)}')
    print('='*45)


# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    YARN_FOLDER     = 'yarn_scripts'
    TRANSLATION_CSV = 'en_ru_pairs.csv'

    print('=== Step 1: Build graph ===')
    graph = build_graph(YARN_FOLDER)

    print('\n=== Step 2: Load translation ===')
    translation = load_translation(TRANSLATION_CSV)
    print(f'Translation entries: {len(translation)}')

    print('\n=== Step 3: Extract yarn metadata ===')
    node_bg, node_emotion = extract_yarn_metadata(YARN_FOLDER)
    print(f'BG entries     : {len(node_bg)}')
    print(f'Emotion entries: {len(node_emotion)}')

    print('\n=== Step 4: Paths ===')
    subgraphs = find_valid_subgraphs(graph, translation)
    all_paths = extract_all_paths(subgraphs)
    print(f'Total paths: {len(all_paths)}')

    print('\n=== Step 5: Filter Lilith dialogs ===')
    real_dialogs = [p for p in all_paths if is_real_dialog(p, translation)]
    print(f'Valid paths: {len(real_dialogs)}')

    print(f'\nMAX_TOKENS={MAX_TOKENS}  MAX_WINDOW_TURNS={MAX_WINDOW_TURNS}')

    datasets_by_lang = {}
    total = 0
    for lang, out in [
        ('ru', 'lilith_dataset_ru.jsonl'),
        ('en', 'lilith_dataset_en.jsonl'),
        ('zh', 'lilith_dataset_zh.jsonl'),
    ]:
        print(f'\n--- [{lang}] ---')
        n = save_refined_dataset(real_dialogs, translation, node_bg, node_emotion, out, lang=lang)
        total += n
        with open(out, encoding='utf-8') as f:
            datasets_by_lang[lang] = [json.loads(l) for l in f]

    print(f'\nTotal across all languages: {total}')
    print_final_stats(real_dialogs, datasets_by_lang)