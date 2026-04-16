import re

LINE_REGEX = re.compile(r'#line:([0-9a-f]+)')
JUMP_REGEX = re.compile(r'<<jump\s+([\w\d_]+)>>')


# =========================
# UTILS
# =========================

def is_command(line: str) -> bool:
    return line.startswith("<<") and line.endswith(">>")


def extract_line_id(line: str):
    match = LINE_REGEX.search(line)
    return match.group(1) if match else None


def extract_jump(line: str):
    match = JUMP_REGEX.search(line)
    return match.group(1) if match else None


def create_node(graph, title, raw_id, text):
    node_id = f"{title}:{raw_id}"
    return graph.get_or_create(node_id, text, title)


class ChoiceBlock:
    """Класс для отслеживания текущего блока выборов по уровню отступа."""
    def __init__(self, indent, parents_before):
        self.indent = indent
        self.parents_before = parents_before  # Ноды, от которых начинается этот выбор
        self.branch_ends = []                 # Ноды, которыми заканчиваются разные ветки (для слияния)


# =========================
# MAIN PARSER
# =========================

def parse_file(filepath, graph):
    title = None
    active_parents = []
    stack = []  # Стек активных блоков выбора (ChoiceBlock)
    nodes_in_file = []

    with open(filepath, encoding="utf-8") as f:
        lines = f.readlines()

    i = 0
    n = len(lines)

    while i < n:
        raw = lines[i].rstrip("\n")
        stripped = raw.strip()

        # Пропускаем пустые строки, чтобы они не ломали логику отступов
        if not stripped:
            i += 1
            continue

        # --- Разделители ---
        if stripped == "===":
            active_parents = []
            stack = []
            title = None
            i += 1
            continue

        if stripped == "---":
            i += 1
            continue

        # --- Заголовок узла ---
        if stripped.startswith("title:"):
            title = stripped.split("title:", 1)[1].strip()
            active_parents = []
            stack = []
            i += 1
            continue

        if not title:
            i += 1
            continue

        # Считаем уровень отступа текущей строки
        indent = len(raw) - len(raw.lstrip())

        # =========================
        # 1. ПРОВЕРКА ВЫХОДА ИЗ БЛОКА ВЫБОРА
        # =========================
        # Если отступ стал меньше, чем у текущего блока выбора, или отступ такой же, 
        # но это не начало новой ветки '->', значит блок выбора закончился.
        while stack:
            top_block = stack[-1]
            if indent < top_block.indent or (indent == top_block.indent and not stripped.startswith("->")):
                popped_block = stack.pop()
                
                # Добавляем текущую оборвавшуюся ветку в общую копилку концов этого блока
                if active_parents:
                    popped_block.branch_ends.extend(active_parents)
                
                # После выхода из блока выбора все его "хвосты" становятся активными родителями 
                # для следующей строки (чтобы поток объединился). Удаляем дубликаты.
                unique_parents = []
                seen = set()
                for p in popped_block.branch_ends:
                    if p not in seen:
                        seen.add(p)
                        unique_parents.append(p)
                
                active_parents = unique_parents
            else:
                break

        # =========================
        # 2. ОБРАБОТКА СТРОКИ
        # =========================
        
        # --- Блок Выбора (Choice) ---
        if stripped.startswith("->"):
            if stack and stack[-1].indent == indent:
                # Это еще один вариант выбора в уже существующем блоке
                top_block = stack[-1]
                if active_parents:
                    # Сохраняем конец предыдущей ветки
                    top_block.branch_ends.extend(active_parents)
                # Новая ветка должна расти из тех же родителей, что и весь блок выбора
                current_branch_parents = top_block.parents_before
            else:
                # Это начало совершенно нового блока выбора
                new_block = ChoiceBlock(indent, list(active_parents))
                stack.append(new_block)
                current_branch_parents = active_parents

            raw_id = extract_line_id(stripped)
            if raw_id:
                node = create_node(graph, title, raw_id, stripped)
                for p in current_branch_parents:
                    p.add_child(node)
                active_parents = [node]
                nodes_in_file.append(node)
            else:
                # Если у выбора нет #line, мы не создаем ноду,
                # но ветка всё равно логически начнется от current_branch_parents
                active_parents = list(current_branch_parents)

        # --- Команды ---
        elif is_command(stripped):
            target = extract_jump(stripped)
            if target:
                for p in active_parents:
                    graph.pending_jumps.append((p, target))
                active_parents = []  # После jump ветка мертва, дальше идти некуда
            else:
                # Обработка других команд (как в вашем оригинальном скрипте)
                if stripped.startswith("<<if ") or stripped.startswith("<<elseif ") or stripped.startswith("<<else"):
                    j = i + 1
                    next_text = ""
                    while j < n:
                        l2 = lines[j].strip()
                        if l2 and not l2.startswith("<<"):
                            next_text = l2[:80]
                            break
                        j += 1
                    #print(f"[CONDITION] {stripped} -> {next_text}")

        # --- Обычный текст ---
        else:
            raw_id = extract_line_id(stripped)
            if raw_id:
                node = create_node(graph, title, raw_id, stripped)
                
                # Привязываем к активным родителям (это может быть одна нода, или сразу несколько, 
                # если мы только что вышли из блока выбора)
                for p in active_parents:
                    p.add_child(node)
                
                active_parents = [node]
                nodes_in_file.append(node)

        i += 1

    return len(nodes_in_file)