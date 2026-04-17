"""
lolmake.py  —  датасет-генератор v3

Ключевое изменение архитектуры:
  НЕТ перебора путей (экспоненциальный взрыв).
  Вместо этого: топологический обход каждой компоненты графа → линейная
  последовательность нод → скользящее окно по этой последовательности.

Формат:
  <PLAYER>, <CHAR_Lilith>, <NPC_Name>, <NPC_Crowd>, <SCENE>
  Эмоции Лилит из спрайтов: *описание*
  Пример начинается с user, заканчивается на <CHAR_Lilith>
"""

import os, re, json
from collections import Counter, deque

from text import detect_speaker, normalize_speaker, clean_final_text, classify_node
from translate import load_translation
from graph import build_graph
from tokenizer import MAX_TOKENS, find_window_size, estimate_tokens, MAX_WINDOW_TURNS

# ─────────────────────────────────────────────────────────────
#  EMOTION / SCENE MAPS
# ─────────────────────────────────────────────────────────────

LILITH_EMOTIONS = {
    'ru': {
        0:"невозмутимо", 1:"спокойно", 2:"слегка улыбаясь",
        3:"с лёгкой усмешкой", 4:"мягко улыбаясь", 5:"задумчиво",
        6:"внимательно глядя", 7:"с любопытством", 8:"удивлённо",
        9:"с тёплой улыбкой", 10:"слегка оживившись", 11:"с лёгкой тревогой",
        12:"серьёзно", 13:"холодно", 14:"с лёгкой грустью",
        15:"задумавшись", 16:"смущённо", 17:"нахмурившись",
        18:"безучастно", 19:"взволнованно", 20:"недовольно",
        21:"сердито", 22:"испуганно", 23:"растерянно",
        24:"устало", 25:"с болью", 26:"с горечью",
        27:"почти шёпотом", 28:"с тихой грустью", 29:"с тоской",
        30:"неуверенно", 31:"искренне удивившись", 32:"с облегчением",
        33:"радостно", 34:"отстранённо", 35:"смущённо-растерянно",
        36:"ошеломлённо", 37:"с нескрываемым смущением", 38:"с благодарностью",
        39:"с лёгкой иронией", 40:"решительно", 41:"торжественно",
        42:"с сомнением", 43:"тепло-сдержанно",
    },
    'en': {
        0:"impassively", 1:"calmly", 2:"with a faint smile",
        3:"with a slight smirk", 4:"smiling gently", 5:"thoughtfully",
        6:"attentively", 7:"curiously", 8:"in surprise",
        9:"with a warm smile", 10:"brightening slightly", 11:"with faint unease",
        12:"seriously", 13:"coldly", 14:"with mild sadness",
        15:"lost in thought", 16:"flustered", 17:"frowning",
        18:"indifferently", 19:"agitated", 20:"displeased",
        21:"angrily", 22:"frightened", 23:"confused",
        24:"wearily", 25:"pained", 26:"with bitterness",
        27:"almost whispering", 28:"with quiet sadness", 29:"longingly",
        30:"hesitantly", 31:"genuinely astonished", 32:"with relief",
        33:"joyfully", 34:"detachedly", 35:"flustered and lost",
        36:"stunned", 37:"visibly embarrassed", 38:"gratefully",
        39:"with a touch of irony", 40:"resolutely", 41:"solemnly",
        42:"doubtfully", 43:"warmly yet composed",
    },
    'zh': {
        0:"面无表情地", 1:"平静地", 2:"微微一笑",
        3:"轻轻一哂", 4:"温柔地笑着", 5:"若有所思地",
        6:"专注地望着", 7:"好奇地", 8:"惊讶地",
        9:"带着温柔的微笑", 10:"微微振作", 11:"隐隐不安",
        12:"严肃地", 13:"冷淡地", 14:"略显忧郁",
        15:"陷入沉思", 16:"慌乱地", 17:"皱眉道",
        18:"漠然地", 19:"激动地", 20:"不悦地",
        21:"愤怒地", 22:"惊恐地", 23:"茫然地",
        24:"疲倦地", 25:"痛苦地", 26:"带着苦涩",
        27:"几乎轻声呢喃", 28:"带着淡淡的忧伤", 29:"怅然地",
        30:"迟疑地", 31:"真诚地惊愕", 32:"如释重负地",
        33:"欢欣地", 34:"疏离地", 35:"慌张而迷茫地",
        36:"震惊地", 37:"明显局促", 38:"感激地",
        39:"带着一丝讽意", 40:"坚定地", 41:"庄重地",
        42:"将信将疑地", 43:"温柔而克制地",
    },
}

BG_SCENES = {
    'ru': {
        'BG-0':'Гильдия. День.', 'BG_GUILD':'Гильдия. День.',
        'BG-1':'Гильдия. День.', 'BG-2':'Гильдия. Вечер.',
        'BG-3':'Городская улица. День.', 'BG-4':'Городская улица. Вечер.',
        'BG-5':'Рынок. День.', 'BG-6':'Таверна.',
        'BG-7':'Таверна. Ночь.', 'BG-8':'Карета. День.',
        'BG-8-2':'Карета. Ночь.', 'BG-9':'Лес.',
        'BG-10':'Руины.', 'BG-13':'Замок.',
        'BG-16':'Подземелье.', 'BG-17':'Библиотека.',
        'BG-20':'Городская площадь.', 'BG-24-2':'Берег реки.',
        'BF-2':'Поле боя. День.', 'BF-4':'Поле боя. Вечер.',
        'BF-5':'Поле боя. Ночь.', 'SKY':'Под открытым небом.',
        'AFTERTRAIN':'Тренировочный зал. После занятий.',
    },
    'en': {
        'BG-0':'Guild hall. Daytime.', 'BG_GUILD':'Guild hall. Daytime.',
        'BG-1':'Guild hall. Daytime.', 'BG-2':'Guild hall. Evening.',
        'BG-3':'City street. Daytime.', 'BG-4':'City street. Evening.',
        'BG-5':'Market. Daytime.', 'BG-6':'Tavern.',
        'BG-7':'Tavern. Night.', 'BG-8':'Carriage. Daytime.',
        'BG-8-2':'Carriage. Night.', 'BG-9':'Forest.',
        'BG-10':'Ruins.', 'BG-13':'Castle.',
        'BG-16':'Dungeon.', 'BG-17':'Library.',
        'BG-20':'Town square.', 'BG-24-2':'Riverbank.',
        'BF-2':'Battlefield. Daytime.', 'BF-4':'Battlefield. Evening.',
        'BF-5':'Battlefield. Night.', 'SKY':'Open sky.',
        'AFTERTRAIN':'Training hall. After practice.',
    },
    'zh': {
        'BG-0':'公会大厅。白天。', 'BG_GUILD':'公会大厅。白天。',
        'BG-1':'公会大厅。白天。', 'BG-2':'公会大厅。傍晚。',
        'BG-3':'城市街道。白天。', 'BG-4':'城市街道。傍晚。',
        'BG-5':'市场。白天。', 'BG-6':'酒馆。',
        'BG-7':'酒馆。夜晚。', 'BG-8':'马车。白天。',
        'BG-8-2':'马车。夜晚。', 'BG-9':'森林。',
        'BG-10':'废墟。', 'BG-13':'城堡。',
        'BG-16':'地下城。', 'BG-17':'图书馆。',
        'BG-20':'广场。', 'BG-24-2':'河岸。',
        'BF-2':'战场。白天。', 'BF-4':'战场。傍晚。',
        'BF-5':'战场。夜晚。', 'SKY':'露天之下。',
        'AFTERTRAIN':'训练场。练习结束后。',
    },
}

# ─────────────────────────────────────────────────────────────
#  YARN METADATA
# ─────────────────────────────────────────────────────────────

LINE_RE = re.compile(r'#line:([0-9a-f]+)')
BG_RE   = re.compile(r'<<back_creat\s+(\S+)', re.IGNORECASE)
CHAR_RE = re.compile(r'<<char(?:_creat)?\s+Lilith\S*\s+\d+\s+(\d+)', re.IGNORECASE)


def extract_yarn_metadata(yarn_folder):
    node_bg, node_emotion = {}, {}
    for fname in os.listdir(yarn_folder):
        if not fname.endswith('.yarn'):
            continue
        with open(os.path.join(yarn_folder, fname), encoding='utf-8') as fh:
            lines = fh.readlines()
        cur_bg = cur_em = None
        for raw in lines:
            s = raw.strip()
            m = BG_RE.search(s)
            if m: cur_bg = m.group(1).upper()
            m = CHAR_RE.search(s)
            if m: cur_em = int(m.group(1))
            m = LINE_RE.search(s)
            if m:
                lid = m.group(1)
                if cur_bg is not None: node_bg[lid] = cur_bg
                if cur_em is not None: node_emotion[lid] = cur_em
    return node_bg, node_emotion


# ─────────────────────────────────────────────────────────────
#  SPEAKER
# ─────────────────────────────────────────────────────────────

NAMED_NPC = {
    'kallen':'Kallen', 'green':'Green', 'fouco':'Fouco',
    'sartre':'Sartre', 'karen':'Karen', 'eileen':'Eileen',
    'doria':'Doria', 'ronnie':'Ronnie', 'toru':'Toru',
    'tom':'Tom', 'wilson':'Wilson', 'jerry':'Jerry',
    'ander':'Ander', 'andre':'Andre', 'justus':'Justus',
}


def classify_speaker(en_text):
    raw  = detect_speaker(en_text)
    norm = normalize_speaker(raw)
    if norm in ('YOU', 'LILITH', 'THOUGHT'):
        return norm
    s = raw.strip().lower()
    for key, tag in NAMED_NPC.items():
        if key in s:
            return f'NPC_{tag}'
    return 'NPC_Crowd'


def format_message(sp_type, text, emotion_id=None, lang='ru'):
    if sp_type == 'YOU':
        return f'<PLAYER> {text}'
    if sp_type == 'LILITH':
        emo = LILITH_EMOTIONS.get(lang, {}).get(emotion_id) if emotion_id is not None else None
        if emo:
            return f'<CHAR_Lilith> *{emo}* {text}'
        return f'<CHAR_Lilith> {text}'
    if sp_type == 'THOUGHT':
        return f'<PLAYER> *{text}*'
    return f'<{sp_type}> {text}'   # NPC_Kallen, NPC_Crowd


# ─────────────────────────────────────────────────────────────
#  КОМПОНЕНТЫ  (без DFS по путям — только связные компоненты)
# ─────────────────────────────────────────────────────────────

def find_components(graph, translation):
    """
    Делит граф на связные компоненты, включая NPC ноды.
    Возвращает только компоненты, где есть хотя бы одна нода YOU и одна LILITH.
    """
    node_type = {n: classify_node(n, translation) for n in graph.nodes.values()}
    # Все ноды с реальным контентом (не чистые команды без текста)
    content_nodes = {n for n in graph.nodes.values()
                     if n.id.split(':')[-1] in translation or n.text.strip()}

    visited = set()
    components = []

    for start in content_nodes:
        if start in visited:
            continue
        comp = []
        stack = [start]
        visited.add(start)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in list(cur.children) + list(cur.parents):
                if nb not in visited:
                    visited.add(nb)
                    stack.append(nb)

        # Фильтр: нужны YOU и LILITH
        types_in_comp = {node_type.get(n, 3) for n in comp}
        if 1 in types_in_comp and 2 in types_in_comp:
            components.append(comp)

    print(f'Components with YOU+LILITH: {len(components)}')
    return components


# ─────────────────────────────────────────────────────────────
#  ТОПОЛОГИЧЕСКАЯ ЛИНЕАРИЗАЦИЯ  (BFS по топологическому порядку)
#
#  Граф — DAG с ветвлениями (choices). Мы берём одну линейную
#  цепочку нод методом «жадного BFS»: на каждом шаге выбираем
#  первого доступного потомка. Ветки схлопываются обратно, когда
#  их indegree падает до нуля.
#  Это даёт O(N) обход вместо O(2^N) перебора путей.
# ─────────────────────────────────────────────────────────────

def topological_sequence(component):
    """
    Возвращает список нод в топологическом порядке (приближение).
    Циклы — пропускаются через seen-set.
    """
    comp_set = set(component)
    # Считаем in-degree внутри компоненты
    in_deg = {n: sum(1 for p in n.parents if p in comp_set) for n in comp_set}

    # Стартуем с нод без входящих рёбер внутри компоненты
    queue = deque(sorted([n for n in comp_set if in_deg[n] == 0],
                         key=lambda n: n.id))
    seq = []
    seen = set()

    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        seq.append(node)
        for child in sorted(node.children, key=lambda n: n.id):
            if child in comp_set and child not in seen:
                in_deg[child] -= 1
                if in_deg[child] <= 0:
                    queue.append(child)

    # Добавляем не посещённые (циклические хвосты)
    for n in component:
        if n not in seen:
            seq.append(n)

    return seq


# ─────────────────────────────────────────────────────────────
#  СБОРКА SPEAKER-БЛОКОВ из линейной последовательности
# ─────────────────────────────────────────────────────────────

def sequence_to_blocks(seq, translation, node_bg, node_emotion, lang):
    """
    Преобразует топологическую последовательность нод в список speaker-блоков.
    Блок = одна «реплика» (возможно многострочная, если подряд идут ноды одного спикера).
    """
    blocks = []
    current = None
    last_scene = None

    for node in seq:
        raw_id = node.id.split(':')[-1]
        if raw_id not in translation:
            continue

        en_text  = translation[raw_id].get('en', '')
        tgt_text = translation[raw_id].get(lang, '')
        cleaned  = clean_final_text(tgt_text)
        if not cleaned:
            continue

        sp_type = classify_speaker(en_text)
        emotion = node_emotion.get(raw_id)

        # Сцена
        bg = node_bg.get(raw_id)
        if bg:
            scenes = BG_SCENES.get(lang, BG_SCENES['en'])
            label  = scenes.get(bg.upper(), bg)
            scene_tag = f'<SCENE> {label} </SCENE>'
        else:
            scene_tag = None

        scene_changed = scene_tag and scene_tag != last_scene
        if scene_changed:
            last_scene = scene_tag

        same = current and current['role'] == sp_type and not scene_changed
        if same:
            current['lines'].append(cleaned)
            if emotion is not None:
                current['emotion'] = emotion
        else:
            if current:
                blocks.append(current)
            current = {
                'role':    sp_type,
                'lines':   [cleaned],
                'scene':   scene_tag if scene_changed else None,
                'emotion': emotion,
            }

    if current:
        blocks.append(current)

    return blocks


# ─────────────────────────────────────────────────────────────
#  СКОЛЬЗЯЩЕЕ ОКНО  →  примеры датасета
# ─────────────────────────────────────────────────────────────

def blocks_to_examples(blocks, sys_content, lang):
    """
    Нарезает список блоков скользящим окном.
    Размер окна подбирается адаптивно по токенам.
    Каждый пример: начинается user, заканчивается <CHAR_Lilith>.
    """
    if len(blocks) < 2:
        return []

    token_counts = [estimate_tokens('\n'.join(b['lines'])) for b in blocks]
    window_size  = find_window_size(token_counts, MAX_TOKENS)
    step = 5 if window_size >= 20 else 1

    examples = []
    for i in range(0, max(1, len(blocks) - window_size + 1), step):
        window = blocks[i : i + window_size]
        ex = build_example(sys_content, window, lang)
        if ex:
            examples.append(ex)

    return examples


def build_example(sys_content, blocks, lang):
    """Собирает один пример из окна блоков."""
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

    # Склеиваем одинаковые роли подряд
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

    return {'messages': [{'role': 'system', 'content': sys_content}] + merged}


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
#  ГЛАВНАЯ ФУНКЦИЯ
# ─────────────────────────────────────────────────────────────

def save_dataset(components, translation, node_bg, node_emotion,
                 output_file, lang='ru'):
    sys_content = SYSTEM_PROMPTS.get(lang, SYSTEM_PROMPTS['en'])
    dataset = []
    diag_sizes = Counter()

    for comp in components:
        seq    = topological_sequence(comp)
        blocks = sequence_to_blocks(seq, translation, node_bg, node_emotion, lang)
        diag_sizes[len(blocks)] += 1
        examples = blocks_to_examples(blocks, sys_content, lang)
        dataset.extend(examples)

    # Дедупликация
    unique = {json.dumps(ex, sort_keys=True, ensure_ascii=False): ex
              for ex in dataset}

    with open(output_file, 'w', encoding='utf-8') as f:
        for entry in unique.values():
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')

    n   = len(unique)
    avg = sum(len(ex['messages'])-1 for ex in unique.values()) / n if n else 0
    print(f'  [diag] blocks/comp : {dict(sorted(diag_sizes.items())[:10])}')
    print(f'[{lang}] {n} examples → {output_file}  (avg turns: {avg:.1f})')
    return n


def print_final_stats(components, datasets_by_lang):
    print('\n' + '='*48)
    print('           DATASET STATISTICS')
    print('='*48)
    print(f'Components (YOU+LILITH): {len(components)}')
    for lang, ds in datasets_by_lang.items():
        if not ds:
            continue
        mc   = [len(d['messages']) for d in ds]
        chars= [sum(len(m['content']) for m in d['messages']) for d in ds]
        npc  = sum(1 for d in ds if any('<NPC_' in m['content'] for m in d['messages']))
        scn  = sum(1 for d in ds if any('<SCENE>' in m['content'] for m in d['messages']))
        emo  = sum(1 for d in ds if any(
            re.search(r'\*[^*]+\*', m['content'])
            for m in d['messages'] if m['role']=='assistant'))
        print(f'\n  [{lang.upper()}]  n={len(ds)}  avg_turns={sum(mc)/len(mc):.1f}'
              f'  avg_chars={sum(chars)/len(chars):.0f}')
        print(f'         <SCENE>={scn}  *emotion*={emo}  <NPC_*>={npc}')
    print('='*48)


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

    print('\n=== Step 4: Find YOU+LILITH components ===')
    components = find_components(graph, translation)

    print(f'\nMAX_TOKENS={MAX_TOKENS}  MAX_WINDOW_TURNS={MAX_WINDOW_TURNS}')

    datasets_by_lang = {}
    total = 0
    for lang, out in [
        ('ru', 'lilith_dataset_ru.jsonl'),
        ('en', 'lilith_dataset_en.jsonl'),
        ('zh', 'lilith_dataset_zh.jsonl'),
    ]:
        print(f'\n--- [{lang}] ---')
        n = save_dataset(components, translation, node_bg, node_emotion, out, lang=lang)
        total += n
        with open(out, encoding='utf-8') as f:
            datasets_by_lang[lang] = [json.loads(l) for l in f]

    print(f'\nTotal across all languages: {total}')
    print_final_stats(components, datasets_by_lang)