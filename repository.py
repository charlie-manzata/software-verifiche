from pathlib import Path

START = "% --- METADATA ---"
END = "% --- END METADATA ---"

DEFAULTS = {
    "id": "",
    "materia": "",
    "classe": "",
    "argomento": "",
    "sottoargomento": "",
    "difficolta": 1,
    "tempo": 10,
    "punti": 1,
    "tags": "",
}


def _number(value, default, integer=False):
    try:
        return int(value) if integer else float(value)
    except (TypeError, ValueError):
        return default


def parse_metadata(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    data = dict(DEFAULTS)
    inside = False

    for raw in text.splitlines():
        line = raw.strip()
        if line == START:
            inside = True
            continue
        if line == END:
            inside = False
            continue
        if inside and line.startswith("%") and ":" in line:
            key, value = line[1:].strip().split(":", 1)
            data[key.strip().lower()] = value.strip()

    data["id"] = data["id"] or path.stem
    data["difficolta"] = _number(data["difficolta"], 1, True)
    data["tempo"] = _number(data["tempo"], 10)
    data["punti"] = _number(data["punti"], 1)
    data["path"] = str(path)
    return data


def scan_repository(root: Path) -> list[dict]:
    if not root.exists():
        return []
    result = []
    for path in sorted(root.rglob("*.tex")):
        if path.name.endswith("_sol.tex"):
            continue
        try:
            result.append(parse_metadata(path))
        except Exception as exc:
            print(f"Errore leggendo {path}: {exc}")
    return result


def remove_metadata(text: str) -> str:
    out, inside = [], False
    for line in text.splitlines():
        if line.strip() == START:
            inside = True
            continue
        if line.strip() == END:
            inside = False
            continue
        if not inside:
            out.append(line)
    return "\n".join(out).strip()


def get_solution_path(exercise: dict):
    path = Path(exercise["path"])
    candidate = path.with_name(path.stem + "_sol.tex")
    return candidate if candidate.exists() else None
