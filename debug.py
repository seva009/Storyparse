from text import clean_final_text, normalize_speaker, detect_speaker

def debug_trace_line(target_id, graph, subgraphs, real_dialogs, translation):
    print(f"\n--- DEBUG TRACE FOR ID: {target_id} ---")
    
    # Этап 1: Есть ли в графе?
    full_id = next((nid for nid in graph.nodes if target_id in nid), None)
    if not full_id:
        print("[-] Stage 1 (Parsing): FAILED. ID not found in Graph. Check regex or file paths.")
        return
    print(f"[+] Stage 1 (Parsing): SUCCESS. Found as {full_id}")

    # Этап 2: Попал ли в подграфы?
    in_subgraph = any(full_id in [n.id for n in sg] for sg in subgraphs)
    if not in_subgraph:
        print("[-] Stage 2 (Grouping): FAILED. Node is isolated (no parents/children).")
        return
    print("[+] Stage 2 (Grouping): SUCCESS. Node is part of a subgraph.")

    # Этап 3: Прошел ли фильтр диалогов (YOU + LILITH)?
    in_real = any(full_id in path for path in real_dialogs)
    if not in_real:
        print("[-] Stage 3 (Filtering): FAILED. Path doesn't contain both YOU and LILITH, or has OTHERS.")
        return
    print("[+] Stage 3 (Filtering): SUCCESS. Node is in a valid dialog path.")

    # Этап 4: Что осталось после чистки текста?
    raw_text = translation.get(target_id, {}).get('ru', '')
    cleaned = clean_final_text(raw_text)
    if not cleaned:
        print(f"[-] Stage 4 (Cleaning): FAILED. Text '{raw_text}' became empty after cleaning.")
    else:
        print(f"[+] Stage 4 (Cleaning): SUCCESS. Final text: '{cleaned}'")

def visualize_node_branch(target_id, graph, translation):
    # 1. Находим полный ID в графе
    full_id = next((nid for nid in graph.nodes if target_id in nid), None)
    if not full_id:
        print(f"ID {target_id} не найден в графе!")
        return

    node = graph.nodes[full_id]
    
    # 2. Находим "подграф" (всех предков и потомков)
    # Для простоты выведем один самый длинный путь, в котором участвует этот узел
    def get_full_path(current_node, visited=None):
        if visited is None: visited = set()
        if current_node in visited: return [current_node.id]
        visited.add(current_node)
        
        # Идем назад к самому началу
        path_back = []
        curr = current_node
        while curr.parents:
            parent = list(curr.parents)[0] # берем первого родителя
            if parent in visited: break
            path_back.append(parent.id)
            curr = parent
            visited.add(curr)
        
        # Идем вперед до конца
        path_forward = []
        curr = current_node
        while curr.children:
            child = list(curr.children)[0] # берем первого ребенка
            if child in visited: break
            path_forward.append(child.id)
            curr = child
            visited.add(curr)
            
        return path_back[::-1] + [current_node.id] + path_forward

    path = get_full_path(node)

    print(f"\n=== ТРАССИРОВКА ВЕТКИ ДЛЯ ID: {target_id} ===")
    print(f"Путь содержит {len(path)} узлов.\n")

    for nid in path:
        raw_id = nid.split(":")[-1]
        data = translation.get(raw_id, {})
        en_text = data.get("en", "---")
        ru_text = data.get("ru", "---")
        
        # Смотрим, как отрабатывает логика распознавания
        raw_speaker = detect_speaker(en_text)
        norm_speaker = normalize_speaker(raw_speaker)
        
        marker = ">>>" if raw_id == target_id else "   "
        
        print(f"{marker} [{norm_speaker.ljust(8)}] (Raw: {raw_speaker})")
        print(f"    RU: {ru_text}")
        print(f"    EN: {en_text}")
        print("-" * 50)

    # Проверка финального вердикта
    speakers = set(normalize_speaker(detect_speaker(translation.get(nid.split(":")[-1], {}).get("en", ""))) for nid in path)
    print(f"\nИТОГО ДЛЯ ФИЛЬТРА:")
    print(f"- Содержит LILITH: {'LILITH' in speakers}")
    print(f"- Содержит YOU:    {'YOU' in speakers}")
    print(f"- Другие роли:     {speakers - {'LILITH', 'YOU', 'THOUGHT', 'NARRATOR'}}")


def debug_target_path(target_id, graph, translation, window=40):
    """
    Дебаг вокруг целевой ноды: показывает путь ±window узлов.
    """
    # 1. Находим полный ID в графе
    full_id = next((nid for nid in graph.nodes if target_id in nid), None)
    if not full_id:
        print(f"ID {target_id} не найден в графе!")
        return

    node = graph.nodes[full_id]

    # 2. Получаем путь назад (по родителям)
    back_path = []
    curr = node
    visited_back = set()
    while curr.parents and len(back_path) < window:
        parent = list(curr.parents)[0]
        if parent.id in visited_back:
            break
        back_path.append(parent)
        curr = parent
        visited_back.add(parent.id)
    back_path = back_path[::-1]  # чтобы идти от старта к target

    # 3. Путь вперёд (по детям)
    forward_path = []
    curr = node
    visited_fwd = set()
    while curr.children and len(forward_path) < window:
        child = list(curr.children)[0]
        if child.id in visited_fwd:
            break
        forward_path.append(child)
        curr = child
        visited_fwd.add(child.id)

    # 4. Собираем общий путь
    full_path = back_path + [node] + forward_path

    print(f"\n=== DEBUG PATH FOR TARGET {target_id} ===")
    print(f"Total nodes in window: {len(full_path)}")
    print(f"Showing {len(back_path)} nodes before, {len(forward_path)} nodes after\n")

    for n in full_path:
        raw_id = n.id.split(":")[-1]
        data = translation.get(raw_id, {})
        en_text = data.get("en", "---")
        ru_text = data.get("ru", "---")
        raw_speaker = detect_speaker(en_text)
        norm_speaker = normalize_speaker(raw_speaker)

        marker = ">>> " if n.id == full_id else "    "
        print(f"{marker}[{norm_speaker.ljust(8)}] {n.id}")
        print(f"     RU: {ru_text}")
        print(f"     EN: {en_text}")
        print(f"     parents: {len(n.parents)}, children: {len(n.children)}")
        print("-" * 50)

def debug_full_trace(target_id, graph, subgraphs, real_dialogs, translation, window=40):
    print(f"\n=== DEBUG FULL TRACE FOR TARGET ID: {target_id} ===")

    # --- 1️⃣ Исходный граф ---
    print("\n--- Stage 1: Original Graph ---")
    node = next((n for nid, n in graph.nodes.items() if target_id in nid), None)
    if not node:
        print("Node not found in graph!")
    else:
        # путь назад
        back = []
        curr = node
        visited_back = set()
        while curr.parents and len(back) < window:
            parent = list(curr.parents)[0]
            if parent.id in visited_back:
                break
            back.append(parent)
            curr = parent
            visited_back.add(parent.id)
        back = back[::-1]

        # путь вперёд
        fwd = []
        curr = node
        visited_fwd = set()
        while curr.children and len(fwd) < window:
            child = list(curr.children)[0]
            if child.id in visited_fwd:
                break
            fwd.append(child)
            curr = child
            visited_fwd.add(child.id)

        path = back + [node] + fwd
        print(f"Nodes shown: {len(path)} (before: {len(back)}, after: {len(fwd)})")
        for n in path:
            raw_id = n.id.split(":")[-1]
            ru = translation.get(raw_id, {}).get("ru", "---")
            en = translation.get(raw_id, {}).get("en", "---")
            print(f"{'>>>' if n==node else '   '} {n.id} [{len(n.parents)}p, {len(n.children)}c] RU: {ru[:40]} EN: {en[:40]}")

    # --- 2️⃣ Подграфы ---
    print("\n--- Stage 2: Subgraphs ---")
    sg_found = False
    for sg in subgraphs:
        if any(n.id.split(":")[-1]==target_id for n in sg):
            sg_found = True
            # сортируем по порядку добавления (можно использовать DFS)
            idx = next(i for i, n in enumerate(sg) if n.id.split(":")[-1]==target_id)
            start = max(0, idx - window)
            end = min(len(sg), idx + window + 1)
            print(f"Subgraph length: {len(sg)}, showing nodes {start}..{end}")
            for n in sg[start:end]:
                raw_id = n.id.split(":")[-1]
                ru = translation.get(raw_id, {}).get("ru", "---")
                en = translation.get(raw_id, {}).get("en", "---")
                marker = ">>>" if raw_id==target_id else "   "
                print(f"{marker} {n.id} RU: {ru[:40]} EN: {en[:40]}")
            break
    if not sg_found:
        print("Node not found in any valid subgraph!")

    # --- 3️⃣ Очистка / финальные пути ---
    print("\n--- Stage 3: Real Dialog Paths ---")
    found_in_path = False
    for i, path in enumerate(real_dialogs):
        if any(target_id in nid for nid in path):
            found_in_path = True
            idx = next(j for j, nid in enumerate(path) if target_id in nid)
            start = max(0, idx - window)
            end = min(len(path), idx + window + 1)
            print(f"Path {i}, length: {len(path)}, showing nodes {start}..{end}")
            for nid in path[start:end]:
                raw_id = nid.split(":")[-1]
                ru = translation.get(raw_id, {}).get("ru", "---")
                en = translation.get(raw_id, {}).get("en", "---")
                marker = ">>>" if raw_id==target_id else "   "
                print(f"{marker} {nid} RU: {ru[:40]} EN: {en[:40]}")
    if not found_in_path:
        print("Node not found in any real dialog path!")

def find_unused_translations(graph, translation, limit=50):
    """
    Находит строки перевода, которых нет в графе (yarn).
    """

    # --- все ID из графа ---
    graph_ids = set()
    for node in graph.nodes.values():
        raw_id = node.id.split(":")[-1]
        graph_ids.add(raw_id)

    # --- все ID из перевода ---
    translation_ids = set(translation.keys())

    # --- разница ---
    unused_ids = translation_ids - graph_ids

    print("\n=== UNUSED TRANSLATIONS ===")
    print(f"Total unused: {len(unused_ids)}")

    # покажем примеры
    for i, tid in enumerate(unused_ids):
        if i >= limit:
            break

        data = translation[tid]
        print(f"\nID: {tid}")
        print(f"EN: {data.get('en', '')}")
        print(f"RU: {data.get('ru', '')}")

    return unused_ids

def find_missing_translations(graph, translation, limit=50):
    graph_ids = set(
        node.id.split(":")[-1]
        for node in graph.nodes.values()
    )

    translation_ids = set(translation.keys())

    missing = graph_ids - translation_ids

    print("\n=== MISSING TRANSLATIONS ===")
    print(f"Total missing: {len(missing)}")

    for i, mid in enumerate(missing):
        if i >= limit:
            break

        node = next(
            n for n in graph.nodes.values()
            if n.id.endswith(mid)
        )

        print(f"\nID: {mid}")
        print(f"TEXT: {node.text}")

    return missing