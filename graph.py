from collections import defaultdict
import os
from fp import parse_file

# --- NODE ---
class DialogueNode:
    def __init__(self, node_id, text, title):
        self.id = node_id
        self.text = text
        self.title = title

        self.children = set()
        self.parents = set()

    def add_child(self, node):
        self.children.add(node)
        node.parents.add(self)

    def __repr__(self):
        return f"Node({self.id})"


# --- GRAPH ---
class DialogueGraph:
    def __init__(self):
        self.nodes = {}
        self.title_to_nodes = defaultdict(list)

        # временные jump'ы: (from_node, target_title)
        self.pending_jumps = []

    def get_or_create(self, node_id, text, title):
        if node_id not in self.nodes:
            node = DialogueNode(node_id, text, title)
            self.nodes[node_id] = node
            self.title_to_nodes[title].append(node)
        return self.nodes[node_id]

    def add_edge(self, a, b):
        a.add_child(b)

    # --- НАХОДИМ ENTRY НОДУ ---
    def find_entry_node(self, title):
        nodes = self.title_to_nodes[title]

        # entry = нода без родителей внутри этого title
        candidates = [n for n in nodes if not any(p.title == title for p in n.parents)]

        if not candidates:
            # fallback: первая нода
            return nodes[0]

        if len(candidates) > 1:
            # можно логировать
            pass

        return candidates[0]

    # --- РЕЗОЛВ JUMP ---
    def resolve_jumps(self):
        for from_node, target_title in self.pending_jumps:
            if target_title not in self.title_to_nodes:
                print(f"[WARN] jump target not found: {target_title}")
                continue

            entry = self.find_entry_node(target_title)

            from_node.add_child(entry)

    # --- ВАЛИДАЦИЯ ---
    def validate(self, expected_lines):
        actual = len(self.nodes)

        print(f"Lines parsed: {expected_lines}")
        print(f"Unique nodes: {actual}")

        if actual != expected_lines:
            print(f"[WARN] mismatch (это нормально если line_id повторяются)")

        # проверка связности
        orphans = [n for n in self.nodes.values() if not n.parents]
        print(f"Root nodes (forest size): {len(orphans)}")

    def stats(self):
        edges = sum(len(n.children) for n in self.nodes.values())
        print(f"Nodes: {len(self.nodes)}")
        print(f"Edges: {edges}")


# --- BUILD ---
def build_graph(folder):
    graph = DialogueGraph()
    total_lines = 0

    for file in os.listdir(folder):
        if file.endswith(".yarn"):
            path = os.path.join(folder, file)
            total_lines += parse_file(path, graph)

    # 🔥 ключевой шаг
    graph.resolve_jumps()

    graph.validate(total_lines)
    graph.stats()

    return graph

def find_reachable_nodes(graph):
    visited = set()
    stack = []

    # стартуем со всех root
    roots = [n for n in graph.nodes.values() if not n.parents]
    stack.extend(roots)

    while stack:
        node = stack.pop()

        if node in visited:
            continue

        visited.add(node)

        for child in node.children:
            stack.append(child)

    return visited

def find_unreachable_nodes(graph):
    reachable = find_reachable_nodes(graph)

    unreachable = [
        n for n in graph.nodes.values()
        if n not in reachable
    ]

    print(f"\n=== Unreachable nodes: {len(unreachable)} ===")

    for n in unreachable[:20]:  # ограничим вывод
        print(n.id, "->", n.text[:50])

    return unreachable