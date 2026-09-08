from __future__ import annotations

import hashlib
import re
import shutil
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

INCLUDEGRAPHICS_RE = re.compile(
    r"\\includegraphics(?:\s*\[[^\]]*\])?\s*\{([^{}]+)\}"
)


def _safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)
    return value.strip("._") or "image"


def _asset_name(exercise: dict, ref: str, index: int, extension: str | None = None) -> str:
    """Genera un nome asset mantenendo sempre l'estensione reale del file."""
    exid = _safe_name(str(exercise.get("id", "exercise")))
    parsed = urllib.parse.urlparse(ref)
    base = Path(parsed.path).name or f"image_{index}"
    base = _safe_name(base)

    # Se il riferimento originale non contiene un'estensione, usiamo quella
    # del file effettivamente copiato/scaricato. LaTeX/graphicx può anche
    # lavorare senza estensione, ma qui vogliamo un progetto ZIP esplicito e
    # portabile, con riferimenti che puntano esattamente al file presente.
    if extension:
        extension = extension if extension.startswith(".") else "." + extension
        if not Path(base).suffix:
            base += extension.lower()

    digest = hashlib.sha1(ref.encode("utf-8")).hexdigest()[:8]
    return f"{exid}_{digest}_{base}"


def _download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Software-Verifiche/8.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        destination.write_bytes(response.read())


def _process_source(source_path: Path, exercise: dict, asset_dir: Path, replacements: dict,
                    copied: list[Path], errors: list[str], label: str) -> None:
    try:
        text = source_path.read_text(encoding="utf-8")
    except Exception as exc:
        errors.append(f"{label}: impossibile leggere il file: {exc}")
        return

    refs = list(dict.fromkeys(m.group(1).strip() for m in INCLUDEGRAPHICS_RE.finditer(text)))
    for index, ref in enumerate(refs, 1):
        # Per i file locali determiniamo prima il file reale, così possiamo
        # mantenere la sua estensione anche quando nel .tex è scritto, ad
        # esempio, \includegraphics{figura} invece di figura.png.
        source_image = None
        if ref.startswith(("http://", "https://")):
            destination = asset_dir / _asset_name(exercise, ref, index)
            try:
                _download(ref, destination)
            except Exception as exc:
                errors.append(f"{label}: impossibile scaricare {ref}: {exc}")
                continue

            # Se l'URL non contiene l'estensione, prova a ricavarla dal
            # Content-Type del file già scaricato.
            if not destination.suffix:
                try:
                    import mimetypes
                    ext = mimetypes.guess_extension(
                        mimetypes.guess_type(ref)[0] or ""
                    )
                    if ext:
                        renamed = destination.with_suffix(ext)
                        destination.rename(renamed)
                        destination = renamed
                except Exception:
                    pass
        else:
            candidate = (source_path.parent / ref).resolve()
            candidates = [candidate]
            if not candidate.suffix:
                candidates.extend(candidate.with_suffix(ext) for ext in (".png", ".jpg", ".jpeg", ".pdf", ".eps"))
            source_image = next((p for p in candidates if p.exists() and p.is_file()), None)
            if source_image is None:
                errors.append(f"{label}: immagine non trovata: {ref}")
                continue

            destination = asset_dir / _asset_name(
                exercise, ref, index, source_image.suffix
            )
            try:
                shutil.copy2(source_image, destination)
            except Exception as exc:
                errors.append(f"{label}: impossibile copiare {ref}: {exc}")
                continue

        replacements[(str(source_path.resolve()), ref)] = (Path("assets") / destination.name).as_posix()
        if destination not in copied:
            copied.append(destination)


def prepare_image_assets(exercises: list[dict], project_dir: Path, get_solution_path=None) -> dict:
    """Prepara tutte le immagini usate da esercizi e soluzioni.

    Le immagini locali vengono copiate; quelle richiamate con URL http/https
    vengono scaricate. I riferimenti \\includegraphics vengono poi riscritti
    verso assets/<nome>.
    """
    project_dir = Path(project_dir)
    asset_dir = project_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)

    replacements = {}
    copied = []
    errors = []

    for exercise in exercises:
        source_path = Path(exercise["path"]).resolve()
        _process_source(source_path, exercise, asset_dir, replacements, copied, errors, str(source_path))

        if get_solution_path:
            solution_path = get_solution_path(exercise)
            if solution_path and Path(solution_path).exists():
                solution_exercise = dict(exercise)
                solution_exercise["path"] = str(Path(solution_path).resolve())
                _process_source(Path(solution_path).resolve(), solution_exercise, asset_dir,
                                replacements, copied, errors, str(solution_path))

    return {"replacements": replacements, "copied": copied, "errors": errors}


def rewrite_images(text: str, exercise: dict, replacements: dict) -> str:
    source_path = str(Path(exercise["path"]).resolve())

    def repl(match):
        ref = match.group(1).strip()
        new_ref = replacements.get((source_path, ref))
        if not new_ref:
            return match.group(0)
        full = match.group(0)
        start = full.find("{")
        end = full.rfind("}")
        return full[:start + 1] + new_ref + full[end:]

    return INCLUDEGRAPHICS_RE.sub(repl, text)


def create_latex_zip(project_dir: Path, zip_path: Path) -> Path:
    project_dir = Path(project_dir)
    zip_path = Path(zip_path)
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in project_dir.rglob("*"):
            if path.is_file():
                zf.write(path, path.relative_to(project_dir))
    return zip_path


def create_latex_tarball(project_dir: Path) -> bytes:
    """Crea il tar.gz accettato dall'endpoint /data di LaTeX.Online."""
    import io
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tf:
        for path in Path(project_dir).rglob("*"):
            if path.is_file():
                tf.add(path, arcname=path.relative_to(project_dir).as_posix())
    return buffer.getvalue()
