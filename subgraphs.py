from text import classify_node

def find_valid_subgraphs(graph, translation):
    node_type = {}
    for node in graph.nodes.values():
        node_type[node] = classify_node(node, translation)

    visited = set()
    subgraphs = []

    # Заранее отбираем только нужные типы нод
    # Тип 3 = NPC — включаем, чтобы сцены с NPC+Лилит не обрезались
    valid_nodes = {n for n, t in node_type.items() if t in (0, 1, 2, 3)}

    for node in valid_nodes:
        if node in visited:
            continue

        component = []
        stack = [node]
        visited.add(node) # Сразу добавляем в visited, чтобы избежать дублей в стеке

        while stack:
            cur = stack.pop()
            component.append(cur)

            # Идем по детям
            for child in cur.children:
                if child in valid_nodes and child not in visited:
                    visited.add(child)
                    stack.append(child)
            
            # 🔥 ИСПРАВЛЕНИЕ: Обязательно идем и по родителям тоже!
            # Иначе диалоги будут резаться на куски.
            for parent in cur.parents:
                if parent in valid_nodes and parent not in visited:
                    visited.add(parent)
                    stack.append(parent)

        if component:
            subgraphs.append(component)

    print(f"Total valid subgraphs: {len(subgraphs)}")
    return subgraphs


def analyze_subgraphs(subgraphs):
    sizes = [len(sg) for sg in subgraphs]

    print("\n=== SUBGRAPH STATS ===")
    print(f"Total: {len(subgraphs)}")

    if sizes:
        print(f"Min size: {min(sizes)}")
        print(f"Max size: {max(sizes)}")
        print(f"Avg size: {sum(sizes)/len(sizes):.2f}")

def filter_subgraphs(subgraphs):
    filtered = [sg for sg in subgraphs if len(sg) > 1]

    print("\n=== FILTERED SUBGRAPH STATS ===")
    print(f"Total: {len(filtered)}")

    if filtered:
        sizes = [len(sg) for sg in filtered]
        print(f"Min size: {min(sizes)}")
        print(f"Max size: {max(sizes)}")
        print(f"Avg size: {sum(sizes)/len(sizes):.2f}")

    return filtered

def analyze_unique_nodes(graph, subgraphs):
    # все ноды в подграфах
    nodes_in_subgraphs = set()

    for sg in subgraphs:
        for node in sg:
            nodes_in_subgraphs.add(node)

    total_nodes = len(graph.nodes)
    unique_nodes = len(nodes_in_subgraphs)

    percent = (unique_nodes / total_nodes) * 100 if total_nodes > 0 else 0

    print("\n=== UNIQUE NODE COVERAGE ===")
    print(f"Total nodes in graph: {total_nodes}")
    print(f"Unique nodes in subgraphs: {unique_nodes}")
    print(f"Coverage: {percent:.2f}%")

    return percent

def analyze_subgraph_duplicates(subgraphs):
    all_ids = []
    unique_ids = set()

    for sg in subgraphs:
        for node in sg:
            all_ids.append(node.id)
            unique_ids.add(node.id)

    total = len(all_ids)
    unique = len(unique_ids)

    percent_unique = (unique / total) * 100 if total > 0 else 0
    percent_duplicates = 100 - percent_unique

    print("\n=== NODE ID UNIQUENESS ===")
    print(f"Total node occurrences: {total}")
    print(f"Unique node ids: {unique}")
    print(f"Unique ratio: {percent_unique:.2f}%")
    print(f"Duplicate ratio: {percent_duplicates:.2f}%")

    return percent_unique

def extract_paths_from_subgraph(subgraph, max_depth=2000):
    sg_nodes = set(subgraph)
    all_paths = []

    start_nodes = [n for n in subgraph if not (n.parents & sg_nodes)]
    if not start_nodes:
        start_nodes = [subgraph[0]]

    def dfs(node, path, depth):
        if depth > max_depth:
            all_paths.append(list(path))
            #print(f"[DFS] Max depth reached at node {node.id}, path length: {len(path)}")
            return

        children = [c for c in node.children if c in sg_nodes]

        if not children:
            all_paths.append(list(path))
            #print(f"[DFS] Leaf node {node.id}, path length: {len(path)}")
            return

        for child in children:
            if child.id in path:  # цикл
                print(f"[DFS] Skipping cycle at {child.id}")
                continue
            dfs(child, path + [child.id], depth + 1)

    for start in start_nodes:
        dfs(start, [start.id], 1)

    return all_paths

def extract_all_paths(subgraphs):
    all_paths = []

    for i, sg in enumerate(subgraphs):
        paths = extract_paths_from_subgraph(sg)

        all_paths.extend(paths)

        if i % 100 == 0:
            print(f"Processed subgraphs: {i}, total paths: {len(all_paths)}")

    return all_paths