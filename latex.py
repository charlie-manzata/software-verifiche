from pathlib import Path
import re
import shutil

from assets import rewrite_images


DOCUMENT_TEMPLATE = r'''\documentclass[10pt]{exam}

\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{multicol}
\usepackage{graphicx}
\usepackage{float}
\usepackage{subcaption}
\usepackage{nopageno}
\usepackage{wrapfig}
\usepackage{textcomp}
\usepackage{eurosym}
\usepackage[inline]{enumitem}
\usepackage{fontawesome}

\renewcommand{\theenumi}{\Alph{enumi}}

%\pagestyle{head}
%\firstpageheader{}{}{}
%\runningheader{\class}{\examnum\ - Page \thepage\ of \numpages}{\examdate}
%\runningheadrule

\usepackage{mathtools}

\hpword{Punteggio massimo:}
\htword{Totale}
\hsword{Punteggio:}
\hqword{Esercizio:}


\begin{document}

\noindent
\centering\textbf{IISS Copernico Pasoli - VRIS01900L - a.s. __ANNO_SCOLASTICO__
\\ \vspace{.3cm} \Large Verifica di __MATERIA__} \\ 

\vspace{.5cm}

\begin{tabular*}{\textwidth}{l rl l}

\textbf{Cognome e Nome:} \makebox[3in]{\hrulefill}&&\\

&&\\

\textbf{Classe:} \makebox[2in]{\hrulefill} \hspace{1cm}\textbf{Data:} \makebox[2in]{\hrulefill}&&\\

&&\\

& &

\end{tabular*}\\

\rule[2ex]{\textwidth}{2pt}


\pointpoints{Punto}{Punti}
\addpoints

%----------------------------------------------------------------------------------------------------------------------


\begin{questions}

__ESERCIZI__

\end{questions}

\vspace{1cm}

\gradetable[h]

\end{document}
'''


SOLUTION_TEMPLATE = r'''\documentclass[10pt]{exam}
\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{multicol}
\usepackage{graphicx}
\usepackage{float}
\usepackage{subcaption}
\usepackage{nopageno}
\usepackage{wrapfig}
\usepackage{textcomp}
\usepackage{eurosym}
\usepackage[inline]{enumitem}
\usepackage{fontawesome}
\usepackage{mathtools}
\renewcommand{\theenumi}{\Alph{enumi}}
\begin{document}
\begin{center}
{\Large\textbf{Soluzioni -- Verifica di __MATERIA__}}\\[0.4cm]
Classe __CLASSE__
\end{center}
\vspace{0.5cm}
__SOLUZIONI__
\end{document}
'''


def fill_template(template, values):
    for key, value in values.items():
        template = template.replace(f"__{key.upper()}__", str(value))
    return template


def latex_escape(value):
    """Escape dei caratteri speciali per testo LaTeX semplice."""
    text = "" if value is None else str(value)
    replacements = [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"),
        ("%", r"\%"),
        ("$", r"\$"),
        ("#", r"\#"),
        ("_", r"\_"),
        ("{", r"\{"),
        ("}", r"\}"),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def build_exercise(exercise, number, remove_metadata, show_metadata=False, image_replacements=None):
    """Costruisce una domanda per l'ambiente exam/questions.

    Il formato del punteggio è sempre quello standard della classe exam:
    numero della domanda seguito da (N Punto/Punti). In questo modo il
    comportamento è identico sia nella verifica sia nell'esportazione della
    repository, indipendentemente dal contenuto dell'esercizio (minipage,
    immagini, parts, ecc.).
    """
    points = float(exercise.get("punti", 1))
    text = Path(exercise["path"]).read_text(encoding="utf-8")
    text = remove_metadata(text).strip()
    if image_replacements:
        text = rewrite_images(text, exercise, image_replacements)

    parts = [r"\noqformat", rf"\question[{points:g}] "]
    if show_metadata:
        parts.append(
            rf"\textit{{Argomento: {latex_escape(exercise.get('argomento', ''))} -- "
            rf"Difficoltà: {int(exercise.get('difficolta', 1))} -- "
            rf"Tempo: {float(exercise.get('tempo', 10)):g} min}}"
        )
        parts.append(r"\par\medskip")
    parts.append(text)
    parts.append(r"\vspace*{0.6cm}")
    return "\n".join(parts)


def build_solution(exercise, number, get_solution_path, remove_metadata, image_replacements=None):
    path = get_solution_path(exercise)
    if not path:
        return f"\\section*{{Esercizio {number}}}\n\\textit{{Soluzione non disponibile.}}"
    text = remove_metadata(path.read_text(encoding="utf-8")).strip()
    if image_replacements:
        solution_exercise = dict(exercise)
        solution_exercise["path"] = str(path)
        text = rewrite_images(text, solution_exercise, image_replacements)
    return f"\\section*{{Esercizio {number}}}\n\n{text}"


def build_document(materia, esercizi, remove_metadata, show_metadata=False, anno_scolastico="2026/2027", image_replacements=None):
    exercise_text = "\n\n".join(
        build_exercise(e, i, remove_metadata, show_metadata, image_replacements)
        for i, e in enumerate(esercizi, 1)
    )
    return fill_template(
        DOCUMENT_TEMPLATE,
        {
            "materia": latex_escape(str(materia).strip().capitalize()),
            "anno_scolastico": latex_escape(str(anno_scolastico).strip()),
            "esercizi": exercise_text,
        },
    )


def build_solution_document(materia, classe, esercizi, get_solution_path, remove_metadata, image_replacements=None):
    solution_text = "\n\n".join(
        build_solution(e, i, get_solution_path, remove_metadata, image_replacements)
        for i, e in enumerate(esercizi, 1)
    )
    return fill_template(
        SOLUTION_TEMPLATE,
        {
            "materia": latex_escape(materia),
            "classe": latex_escape(classe),
            "soluzioni": solution_text,
        },
    )



REPOSITORY_TEMPLATE = r"""\documentclass[10pt]{exam}

\usepackage[utf8]{inputenc}
\usepackage[italian]{babel}
\usepackage[margin=1in]{geometry}
\usepackage{amsmath,amssymb}
\usepackage{multicol}
\usepackage{graphicx}
\usepackage{float}
\usepackage{subcaption}
\usepackage{nopageno}
\usepackage{wrapfig}
\usepackage{textcomp}
\usepackage{eurosym}
\usepackage[inline]{enumitem}
\usepackage{fontawesome}
\renewcommand{\theenumi}{\Alph{enumi}}
\usepackage{mathtools}

\pointpoints{Punto}{Punti}
\addpoints

\begin{document}

\begin{center}
{\Large\textbf{Repository di __MATERIA__ -- Classe __CLASSE__}}\\[0.2cm]
{\small a.s. __ANNO_SCOLASTICO__}\\[0.3cm]
{\small Tutti gli esercizi presenti nella repository}
\end{center}

\begin{questions}

__ESERCIZI__

\end{questions}

\end{document}
"""


def build_repository_document(materia, classe, esercizi, remove_metadata, image_replacements=None, anno_scolastico="2026/2027"):
    """Genera un unico documento LaTeX con tutti gli esercizi della disciplina/classe."""
    ordered = sorted(esercizi, key=lambda e: (
        str(e.get("argomento", "")).lower(),
        str(e.get("sottoargomento", "")).lower(),
        str(e.get("id", "")).lower(),
    ))
    blocks = []
    current_topic = None
    for i, exercise in enumerate(ordered, 1):
        topic = str(exercise.get("argomento", "")).strip()
        if topic != current_topic:
            if current_topic is not None:
                blocks.append("\\newpage")
            blocks.append(f"\\section*{{{latex_escape(topic or 'Senza argomento')}}}")
            current_topic = topic
        blocks.append(build_exercise(exercise, i, remove_metadata, show_metadata=True, image_replacements=image_replacements))
    return fill_template(REPOSITORY_TEMPLATE, {
        "materia": latex_escape(str(materia).strip().capitalize()),
        "classe": latex_escape(str(classe).strip()),
        "anno_scolastico": latex_escape(str(anno_scolastico).strip()),
        "esercizi": "\n\n".join(blocks),
    })



def _compress_image_for_online(source: Path, destination: Path) -> Path:
    """Riduce le immagini raster solo per l'invio al compilatore online.

    Gli asset originali del progetto non vengono modificati: la compressione
    riguarda esclusivamente la copia temporanea usata per la compilazione.
    """
    suffix = source.suffix.lower()
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError(
            "Per la compilazione online con immagini serve Pillow. "
            "Installa le dipendenze con: pip install -r requirements.txt"
        ) from exc

    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        shutil.copy2(source, destination)
        return destination

    with Image.open(source) as im:
        # Le foto ad alta risoluzione sono la causa principale del 413.
        # 1800 px sono più che sufficienti per una verifica A4.
        im.thumbnail((1800, 1800), Image.Resampling.LANCZOS)
        has_alpha = im.mode in ("RGBA", "LA") or (
            im.mode == "P" and "transparency" in im.info
        )

        if has_alpha:
            out = im.convert("RGBA")
            out.save(destination, format="PNG", optimize=True)
        else:
            out = im.convert("RGB")
            # JPEG è molto più compatto per immagini fotografiche/scansioni.
            destination = destination.with_suffix(".jpg")
            out.save(destination, format="JPEG", quality=78, optimize=True, progressive=True)
    return destination


def _build_online_project(project_dir: Path, target_tex: Path):
    """Crea un progetto temporaneo minimo, comprimendo gli asset raster."""
    import tempfile
    from assets import INCLUDEGRAPHICS_RE

    tmp = tempfile.TemporaryDirectory(prefix="verifiche_online_")
    root = Path(tmp.name)
    text = target_tex.read_text(encoding="utf-8")
    refs = list(dict.fromkeys(m.group(1).strip() for m in INCLUDEGRAPHICS_RE.finditer(text)))
    replacements = {}
    asset_dir = root / "assets"
    asset_dir.mkdir()

    for ref in refs:
        source = (project_dir / ref).resolve()
        try:
            source.relative_to(project_dir.resolve())
        except ValueError:
            source = None
        if source is None or not source.is_file():
            tmp.cleanup()
            raise RuntimeError(f"Immagine referenziata non trovata: {ref}")

        dest = asset_dir / source.name
        online_dest = _compress_image_for_online(source, dest)
        new_ref = (Path("assets") / online_dest.name).as_posix()
        replacements[ref] = new_ref

    for old, new in replacements.items():
        text = text.replace("{" + old + "}", "{" + new + "}")

    tex = root / target_tex.name
    tex.write_text(text, encoding="utf-8")
    return tmp, root, tex


def _compile_with_ytotech(project_root: Path, target_tex: Path) -> bytes:
    """Compila tramite YtoTech LaTeX-on-HTTP usando la API JSON documentata."""
    import base64
    import json
    import requests

    resources = [{
        "main": True,
        "content": target_tex.read_text(encoding="utf-8"),
    }]
    asset_dir = project_root / "assets"
    if asset_dir.exists():
        for path in sorted(asset_dir.rglob("*")):
            if path.is_file():
                resources.append({
                    "path": path.relative_to(project_root).as_posix(),
                    "file": base64.b64encode(path.read_bytes()).decode("ascii"),
                })

    # Usiamo solo le opzioni ufficialmente documentate dall'API. In particolare
    # force=True evita che latexmk si fermi per un primo passaggio incompleto,
    # mentre log_files_on_failure rende l'errore diagnostico disponibile.
    payload = {
        "compiler": "pdflatex",
        "resources": resources,
        "options": {
            "compiler": {
                "force": True,
                "halt_on_error": False,
                "bibliography": False,
            },
            "response": {
                "log_files_on_failure": True,
                "commands": True,
            },
        },
    }
    response = requests.post(
        "https://latex.ytotech.com/builds/sync",
        json=payload,
        headers={
            "User-Agent": "Software-Verifiche/17.0",
            "Accept": "application/pdf, application/json",
            "Content-Type": "application/json",
        },
        timeout=(20, 300),
    )
    ctype = response.headers.get("content-type", "").lower()
    if 200 <= response.status_code < 300 and "application/pdf" in ctype:
        return response.content

    try:
        detail = json.dumps(response.json(), ensure_ascii=False, indent=2)
    except Exception:
        detail = response.text.strip()
    raise RuntimeError(f"YtoTech: HTTP {response.status_code}\n{detail[:12000]}")

def _compile_with_latexonline(project_root: Path, target_tex: Path) -> bytes:
    """Fallback LaTeX.Online /data per progetti già ridotti."""
    import io
    import tarfile
    import requests

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tf:
        tf.add(target_tex, arcname=target_tex.name)
        assets = project_root / "assets"
        if assets.exists():
            for path in assets.rglob("*"):
                if path.is_file():
                    tf.add(path, arcname=f"assets/{path.name}")
    tarball = buffer.getvalue()
    response = requests.post(
        "https://latexonline.cc/data",
        params={"target": target_tex.name, "command": "pdflatex", "force": "true"},
        files={"file": ("project.tar.gz", tarball, "application/gzip")},
        headers={"User-Agent": "Software-Verifiche/17.0"},
        timeout=(20, 300),
    )
    ctype = response.headers.get("content-type", "").lower()
    if 200 <= response.status_code < 300 and "application/pdf" in ctype:
        return response.content
    raise RuntimeError(f"LaTeX.Online: HTTP {response.status_code}\n{response.text[:6000]}")


def compile_project_online(project_dir, target_tex):
    """Compila online.

    Senza immagini usa LaTeX.Online /compile?text=, già collaudato.
    Con immagini usa YtoTech LaTeX-on-HTTP, che accetta risorse binarie come
    file base64 via POST JSON; gli asset raster vengono ridotti solo nella
    copia temporanea per evitare i limiti di upload del reverse proxy di
    LaTeX.Online /data. Se YtoTech non è disponibile, prova /data con lo
    stesso progetto ridotto.
    """
    import requests
    import re
    from assets import INCLUDEGRAPHICS_RE

    project_dir = Path(project_dir).resolve()
    target_tex = Path(target_tex).resolve()
    if not project_dir.is_dir() or not target_tex.is_file():
        raise RuntimeError("Progetto o file LaTeX principale non trovato.")

    text = target_tex.read_text(encoding="utf-8")
    refs = list(dict.fromkeys(m.group(1).strip() for m in INCLUDEGRAPHICS_RE.finditer(text)))
    headers = {"User-Agent": "Software-Verifiche/17.0"}

    if not refs:
        try:
            response = requests.get(
                "https://latexonline.cc/compile",
                params={"text": text, "command": "pdflatex", "force": "true"},
                headers=headers, timeout=(20, 300),
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Impossibile raggiungere LaTeX.Online: {exc}") from exc
        ctype = response.headers.get("content-type", "").lower()
        if 200 <= response.status_code < 300 and "application/pdf" in ctype:
            return response.content
        raise RuntimeError(f"La compilazione online è fallita (HTTP {response.status_code}).\n{response.text[:8000]}")

    tmp = root = tex = None
    errors = []
    try:
        tmp, root, tex = _build_online_project(project_dir, target_tex)
        total_size = sum(p.stat().st_size for p in root.rglob("*") if p.is_file())
        try:
            return _compile_with_ytotech(root, tex)
        except Exception as exc:
            errors.append(str(exc))
        try:
            return _compile_with_latexonline(root, tex)
        except Exception as exc:
            errors.append(str(exc))
        raise RuntimeError(
            "La compilazione online con immagini è fallita su tutti i servizi disponibili. "
            f"Progetto compresso inviato: {total_size / 1024:.1f} KB.\n\n" + "\n\n".join(errors)
        )
    finally:
        if tmp is not None:
            tmp.cleanup()

