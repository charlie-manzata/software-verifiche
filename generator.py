from itertools import combinations
from pathlib import Path
from datetime import datetime
import random

from repository import remove_metadata, get_solution_path

from latex import build_document, build_solution_document
from assets import prepare_image_assets, create_latex_zip


def _difficulty_ok(ex, lo, hi):
    d = int(ex.get("difficolta", 1))
    return lo <= d <= hi


def find_combination(exercises, requested, max_points, max_time, min_difficulty,
                     max_difficulty, excluded_ids=None, seed=None,
                     target_points=None, target_time=None, max_combinations=250000):
    rng = random.Random(seed)
    excluded_ids = excluded_ids or set()
    pools = {}
    for topic, count in requested.items():
        pool = [e for e in exercises if e.get("argomento", "") == topic
                and e.get("id") not in excluded_ids
                and _difficulty_ok(e, min_difficulty, max_difficulty)]
        if len(pool) < count:
            return None, f"Non ci sono abbastanza esercizi disponibili per l'argomento '{topic}'. Richiesti: {count}, disponibili: {len(pool)}."
        rng.shuffle(pool)
        pools[topic] = pool

    if not requested:
        return None, "Non è stato selezionato alcun argomento."

    # Per evitare esplosioni combinatorie, campioniamo le combinazioni di ogni topic.
    choices = []
    for topic, count in requested.items():
        pool = pools[topic]
        combos = list(combinations(pool, count))
        if len(combos) > 3000:
            combos = rng.sample(combos, 3000)
        choices.append(combos)

    best = None
    best_score = float("inf")
    checked = 0

    def score(selected):
        points = sum(float(e.get("punti", 1)) for e in selected)
        time = sum(float(e.get("tempo", 10)) for e in selected)
        score = 0.0
        if max_points is not None:
            score += max(0.0, points - max_points) * 100000
        if max_time is not None:
            score += max(0.0, time - max_time) * 100000
        if target_points is not None:
            score += abs(points - target_points) * 100
        if target_time is not None:
            score += abs(time - target_time)
        return score, points, time

    def visit(i, selected):
        nonlocal best, best_score, checked
        if checked >= max_combinations:
            return
        if i == len(choices):
            checked += 1
            s, p, t = score(selected)
            if s < best_score:
                best_score = s
                best = list(selected), p, t
            return
        for combo in choices[i]:
            new = selected + list(combo)
            p = sum(float(e.get("punti", 1)) for e in new)
            t = sum(float(e.get("tempo", 10)) for e in new)
            if max_points is not None and p > max_points:
                continue
            if max_time is not None and t > max_time:
                continue
            visit(i + 1, new)
            if checked >= max_combinations:
                return

    visit(0, [])

    if best is None:
        return None, "Non è stata trovata alcuna combinazione che rispetti i limiti di punti e tempo."

    selected, points, time = best
    warning = None
    if target_points is not None and abs(points - target_points) > 1e-9:
        warning = f"La combinazione migliore ha {points:g} punti invece dei {target_points:g} richiesti."
    if target_time is not None and abs(time - target_time) > 1e-9:
        extra = f" Il tempo è {time:g} minuti invece dei {target_time:g} richiesti."
        warning = (warning or "") + extra
    return selected, warning


def _write_project(exercises, output_dir, materia, classe, seed, anno_scolastico,
                   show_metadata=False, prefix="verifica"):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    base = f"{prefix}_{materia.replace(' ', '_')}_{classe}_{stamp}"
    project_dir = output_dir / base
    project_dir.mkdir(parents=True, exist_ok=True)

    assets = prepare_image_assets(exercises, project_dir, get_solution_path)
    replacements = assets["replacements"]

    document = build_document(
        materia, exercises, remove_metadata, show_metadata=show_metadata,
        anno_scolastico=anno_scolastico, image_replacements=replacements,
    )
    tex_path = project_dir / f"{base}.tex"
    tex_path.write_text(document, encoding="utf-8")

    solutions = build_solution_document(
        materia, classe, exercises, get_solution_path, remove_metadata,
        image_replacements=replacements,
    )
    sol_path = project_dir / f"{base}_soluzioni.tex"
    sol_path.write_text(solutions, encoding="utf-8")

    zip_path = output_dir / f"{base}.zip"
    create_latex_zip(project_dir, zip_path)

    return {
        "tex_path": tex_path,
        "solution_path": sol_path,
        "project_dir": project_dir,
        "package_path": zip_path,
        "asset_files": assets["copied"],
        "asset_errors": assets["errors"],
        "seed": seed,
    }


def generate_manual_test(exercises, output_dir, materia, classe,
                         show_metadata=False, anno_scolastico="2026/2027", seed=None):
    selected = list(exercises)
    if not selected:
        return {"success": False, "error": "Non hai selezionato alcun esercizio."}

    project = _write_project(
        selected, output_dir, materia, classe, seed, anno_scolastico,
        show_metadata=show_metadata,
    )
    return {
        "success": True,
        "exercises": selected,
        "total_points": sum(float(e.get("punti", 1)) for e in selected),
        "total_time": sum(float(e.get("tempo", 10)) for e in selected),
        "warning": None,
        **project,
    }


def generate_test(exercises, requested, output_dir, materia, classe,
                  max_points=20, max_time=60, min_difficulty=1,
                  max_difficulty=5, excluded_ids=None, seed=None,
                  show_metadata=False, target_points=None, target_time=None,
                  anno_scolastico="2026/2027"):
    selected, warning = find_combination(
        exercises, requested, max_points, max_time,
        min_difficulty, max_difficulty, excluded_ids, seed,
        target_points, target_time
    )
    if selected is None:
        return {"success": False, "error": warning}

    project = _write_project(
        selected, output_dir, materia, classe, seed, anno_scolastico,
        show_metadata=show_metadata,
    )
    return {
        "success": True,
        "exercises": selected,
        "total_points": sum(float(e.get("punti", 1)) for e in selected),
        "total_time": sum(float(e.get("tempo", 10)) for e in selected),
        "warning": warning,
        **project,
    }
