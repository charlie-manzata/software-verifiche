import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from repository import scan_repository, remove_metadata
from generator import generate_test, generate_manual_test
from database import Database
from latex import build_repository_document, compile_project_online
from assets import prepare_image_assets, create_latex_zip

REPOSITORY = Path("esercizi")
OUTPUT_DIR = Path("output")
DB_PATH = Path("database.sqlite")


def difficulty_ok(e, lo, hi):
    try:
        d = int(e.get("difficolta", 1))
    except (TypeError, ValueError):
        d = 1
    return lo <= d <= hi


def compatible(e, used, lo, hi):
    return e.get("id") not in used and difficulty_ok(e, lo, hi)


def show_generated_result(result, db, materia, classe):
    """Mostra una verifica già generata. Rimane disponibile tra i rerun di Streamlit."""
    if result.get("warning"):
        st.warning(result["warning"])
    else:
        st.success("Verifica generata correttamente.")

    selected = result["exercises"]
    a, b, c = st.columns(3)
    a.metric("Esercizi", len(selected))
    b.metric("Punti", f'{result["total_points"]:g}')
    c.metric("Tempo", f'{result["total_time"]:g} min')

    st.subheader("Esercizi selezionati")
    for i, e in enumerate(selected, 1):
        st.write(
            f"{i}. **{e['id']}** — {e['argomento']} — "
            f"difficoltà {e['difficolta']} — {e['punti']:g} punti — {e['tempo']:g} min"
        )

    tex = Path(result["tex_path"])
    sol = Path(result["solution_path"])
    asset_files = result.get("asset_files", [])

    # Un solo pulsante per il compito: se non ci sono immagini basta il .tex;
    # se ci sono immagini viene scaricato lo ZIP con .tex + cartella assets/.
    if asset_files:
        package = Path(result["package_path"])
        st.download_button(
            "⬇️ Scarica compito LaTeX + immagini",
            package.read_bytes(), package.name,
            "application/zip", use_container_width=True, key="download_test_package"
        )
    else:
        st.download_button(
            "⬇️ Scarica compito LaTeX",
            tex.read_bytes(), tex.name,
            "text/plain", use_container_width=True, key="download_test_tex"
        )

    st.markdown("#### Soluzioni")
    st.caption("Le soluzioni possono contenere immagini e vengono quindi generate e scaricate esclusivamente in PDF online.")
    if st.button("☁️ Genera PDF soluzioni online", use_container_width=True, key="compile_solution_online"):
        with st.spinner("Compilo online le soluzioni…"):
            try:
                pdf_bytes = compile_project_online(result["project_dir"], sol)
                st.session_state["last_solution_pdf"] = pdf_bytes
                st.session_state["last_solution_pdf_name"] = sol.with_suffix(".pdf").name
                st.session_state["last_solution_pdf_error"] = None
            except Exception as exc:
                st.session_state["last_solution_pdf_error"] = str(exc)

    if st.session_state.get("last_solution_pdf_error"):
        st.error(st.session_state["last_solution_pdf_error"])
    if "last_solution_pdf" in st.session_state:
        st.download_button(
            "⬇️ Scarica PDF soluzioni",
            st.session_state["last_solution_pdf"],
            st.session_state.get("last_solution_pdf_name", "soluzioni.pdf"),
            "application/pdf", use_container_width=True, key="download_solution_pdf"
        )

    if result.get("asset_files"):
        st.caption(f"Immagini incluse nel progetto: {len(result['asset_files'])}")
    for err in result.get("asset_errors", []):
        st.warning(err)

    st.markdown("#### Compilazione PDF")
    st.caption("Il PDF viene compilato online. Le immagini vengono ottimizzate solo per l'invio al compilatore; gli originali restano nel download del progetto.")
    if st.button("☁️ Genera PDF online", use_container_width=True, key="compile_online"):
        with st.spinner("Invio il progetto a LaTeX.Online e attendo il PDF…"):
            try:
                pdf_bytes = compile_project_online(result["project_dir"], tex)
                st.session_state["last_pdf"] = pdf_bytes
                st.session_state["last_pdf_name"] = tex.with_suffix(".pdf").name
                st.session_state["last_pdf_error"] = None
            except Exception as exc:
                st.session_state["last_pdf_error"] = str(exc)

    if st.session_state.get("last_pdf_error"):
        st.error(st.session_state["last_pdf_error"])
    if "last_pdf" in st.session_state:
        st.download_button(
            "⬇️ Scarica PDF online",
            st.session_state["last_pdf"],
            st.session_state.get("last_pdf_name", "verifica.pdf"),
            "application/pdf", use_container_width=True, key="download_online_pdf"
        )

    if st.button("↩️ Azzera verifica generata", use_container_width=True, key="reset_generated"):
        for key in (
            "last_result", "last_pdf", "last_pdf_name", "last_pdf_error",
            "last_solution_pdf", "last_solution_pdf_name", "last_solution_pdf_error",
        ):
            st.session_state.pop(key, None)
        st.rerun()


st.set_page_config(page_title="Generatore di verifiche — Online", layout="wide")
st.title("📝 Generatore di verifiche — Online")

db = Database(DB_PATH)

anno_scolastico = st.sidebar.text_input(
    "Anno scolastico",
    value="2026/2027",
    help="Anno scolastico riportato nell'intestazione del LaTeX, ad esempio 2026/2027."
)

exercises = scan_repository(REPOSITORY)
if not exercises:
    st.warning("Nessun esercizio trovato nella cartella 'esercizi'.")
    st.stop()

materie = sorted({e.get("materia", "") for e in exercises if e.get("materia")})
materia = st.sidebar.selectbox("Materia", materie)
classi = sorted({e.get("classe", "") for e in exercises if e.get("materia") == materia and e.get("classe")})
classe = st.sidebar.selectbox("Classe", classi)
filtered = [e for e in exercises if e.get("materia") == materia and e.get("classe") == classe]

st.sidebar.header("Vincoli")
min_diff, max_diff = st.sidebar.slider("Difficoltà ammesse", 1, 5, (1, 5))
max_points = st.sidebar.number_input("Punti massimi", min_value=0.0, value=20.0, step=0.5)
max_time = st.sidebar.number_input("Tempo massimo (min)", min_value=0.0, value=60.0, step=5.0)
use_target_points = st.sidebar.checkbox("Punta a un punteggio preciso")
target_points = st.sidebar.number_input("Punteggio obiettivo", min_value=0.0, value=20.0, step=0.5) if use_target_points else None
use_target_time = st.sidebar.checkbox("Punta a un tempo preciso")
target_time = st.sidebar.number_input("Tempo obiettivo (min)", min_value=0.0, value=60.0, step=5.0) if use_target_time else None
recent_n = st.sidebar.number_input("Evita esercizi delle ultime N verifiche", min_value=0, max_value=100, value=3, step=1)
seed_value = st.sidebar.number_input("Seed (0 = casuale)", min_value=0, value=0, step=1)
seed = None if seed_value == 0 else int(seed_value)
show_metadata = st.sidebar.checkbox("Mostra metadati nella verifica")

used = db.get_recent_used_ids(int(recent_n))
compatible_all = [e for e in filtered if compatible(e, used, min_diff, max_diff)]

st.subheader(f"{materia.capitalize()} — Classe {classe}")
a, b, c = st.columns(3)
a.metric("Esercizi totali", len(filtered))
b.metric("Compatibili con i vincoli", len(compatible_all))
c.metric("Esclusi dallo storico", len([e for e in filtered if e.get("id") in used]))

selection_mode = st.radio(
    "Modalità di selezione",
    ["Selezione manuale", "Selezione automatica"],
    horizontal=True,
    help="Nella modalità manuale scegli direttamente gli esercizi. Nella modalità automatica il programma sceglie una combinazione rispettando i vincoli."
)

st.subheader("Argomenti")
requested = {}
manual_selected = []
topics = sorted({e.get("argomento", "") for e in filtered if e.get("argomento")})

if selection_mode == "Selezione manuale":
    st.caption("Scegli direttamente gli esercizi. I vincoli di difficoltà, storico, punti e tempo restano attivi come controlli.")
    for topic in topics:
        all_topic = [e for e in filtered if e.get("argomento") == topic]
        compatible_topic = [e for e in all_topic if compatible(e, used, min_diff, max_diff)]
        with st.expander(f"{topic} — {len(compatible_topic)} compatibili", expanded=True):
            difficulties = sorted({int(e.get("difficolta", 1)) for e in all_topic})
            for difficulty in difficulties:
                diff_exercises = [e for e in compatible_topic if int(e.get("difficolta", 1)) == difficulty]
                if not diff_exercises:
                    continue
                options = [
                    f"{e['id']} — {e.get('sottoargomento', '') or 'senza sottoargomento'} — "
                    f"{float(e.get('punti', 1)):g} pt — {float(e.get('tempo', 10)):g} min"
                    for e in diff_exercises
                ]
                chosen = st.multiselect(f"Difficoltà {difficulty}", options, key=f"manual_{topic}_{difficulty}")
                chosen_ids = {x.split(" — ", 1)[0] for x in chosen}
                manual_selected.extend([e for e in diff_exercises if e.get("id") in chosen_ids])
else:
    for topic in topics:
        all_topic = [e for e in filtered if e.get("argomento") == topic]
        pool = [e for e in all_topic if compatible(e, used, min_diff, max_diff)]
        dist = {}
        for e in pool:
            d = int(e.get("difficolta", 1))
            dist[d] = dist.get(d, 0) + 1
        dist_text = ", ".join(f"d{d}: {n}" for d, n in sorted(dist.items())) or "nessuno"
        with st.expander(f"{topic} — {len(pool)} compatibili", expanded=True):
            st.caption(f"Totali: {len(all_topic)} · Compatibili: {len(pool)} · {dist_text}")
            n = st.number_input("Numero di esercizi", min_value=0, max_value=len(pool), value=0, step=1, key=f"n_{topic}")
            if n:
                requested[topic] = int(n)

st.divider()
if selection_mode == "Selezione manuale":
    total_manual_points = sum(float(e.get("punti", 1)) for e in manual_selected)
    total_manual_time = sum(float(e.get("tempo", 10)) for e in manual_selected)
    st.write(f"**Selezionati:** {len(manual_selected)} esercizi · **{total_manual_points:g} punti** · **{total_manual_time:g} min**")
    if manual_selected:
        st.caption(" · ".join(e["id"] for e in manual_selected))
else:
    if requested:
        st.write("**Richiesta:** " + " · ".join(f"{t}: {n}" for t, n in requested.items()))
    else:
        st.info("Seleziona almeno un esercizio per argomento.")

if st.button("🎲 Genera verifica", type="primary", use_container_width=True):
    if selection_mode == "Selezione manuale":
        selected = manual_selected
        if not selected:
            st.error("Non hai selezionato alcun esercizio.")
        elif len({e.get("id") for e in selected}) != len(selected):
            st.error("È stato selezionato due volte lo stesso esercizio.")
        else:
            total_points = sum(float(e.get("punti", 1)) for e in selected)
            total_time = sum(float(e.get("tempo", 10)) for e in selected)
            if total_points > max_points:
                st.error(f"I punti degli esercizi selezionati sono {total_points:g}, oltre il limite di {max_points:g}.")
            elif total_time > max_time:
                st.error(f"Il tempo degli esercizi selezionati è {total_time:g} minuti, oltre il limite di {max_time:g}.")
            else:
                if target_points is not None and abs(total_points - target_points) > 1e-9:
                    st.warning(f"Hai selezionato {total_points:g} punti invece dei {target_points:g} dell'obiettivo.")
                if target_time is not None and abs(total_time - target_time) > 1e-9:
                    st.warning(f"Hai selezionato {total_time:g} minuti invece dei {target_time:g} dell'obiettivo.")
                result = generate_manual_test(
                    selected, OUTPUT_DIR, materia, classe,
                    show_metadata=show_metadata, anno_scolastico=anno_scolastico, seed=seed
                )
                st.session_state["last_result"] = result
                st.session_state.pop("last_pdf", None)
                db.save_test(materia, classe, result["total_points"], result["total_time"], result["seed"], [e["id"] for e in selected])
                st.rerun()
    else:
        problems = []
        for topic, n in requested.items():
            available = len([e for e in filtered if e.get("argomento") == topic and compatible(e, used, min_diff, max_diff)])
            if available < n:
                problems.append(f"{topic}: richiesti {n}, disponibili {available}")
        if problems:
            st.error("Impossibile generare la verifica:")
            for p in problems:
                st.write("- " + p)
        else:
            result = generate_test(
                exercises=filtered, requested=requested, output_dir=OUTPUT_DIR,
                materia=materia, classe=classe, max_points=max_points, max_time=max_time,
                min_difficulty=min_diff, max_difficulty=max_diff, excluded_ids=used,
                seed=seed, show_metadata=show_metadata, target_points=target_points,
                target_time=target_time, anno_scolastico=anno_scolastico,
            )
            if not result["success"]:
                st.error(result["error"])
            else:
                st.session_state["last_result"] = result
                st.session_state.pop("last_pdf", None)
                db.save_test(materia, classe, result["total_points"], result["total_time"], result["seed"], [e["id"] for e in result["exercises"]])
                st.rerun()

if "last_result" in st.session_state:
    st.divider()
    st.header("Verifica generata")
    show_generated_result(st.session_state["last_result"], db, materia, classe)

st.sidebar.divider()
with st.sidebar.expander("📚 Esporta repository", expanded=False):
    st.write("Genera un unico file LaTeX con tutti gli esercizi di una disciplina e di una classe.")
    repo_materia = st.selectbox("Disciplina", materie, key="repo_materia")
    repo_classi = sorted({e.get("classe", "") for e in exercises if e.get("materia") == repo_materia and e.get("classe")})
    if repo_classi:
        repo_classe = st.selectbox("Classe", repo_classi, key="repo_classe")
        repo_exercises = [e for e in exercises if e.get("materia") == repo_materia and e.get("classe") == repo_classe]
        st.caption(f"Esercizi nella repository: {len(repo_exercises)}")
        if st.button("📥 Genera repository LaTeX", key="generate_repo", use_container_width=True):
            repo_stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            repo_base = f"repository_{repo_materia.replace(' ', '_')}_{repo_classe}_{repo_stamp}"
            repo_project = OUTPUT_DIR / repo_base
            repo_project.mkdir(parents=True, exist_ok=True)
            repo_assets = prepare_image_assets(repo_exercises, repo_project)
            repo_tex = build_repository_document(
                repo_materia, repo_classe, repo_exercises, remove_metadata,
                image_replacements=repo_assets["replacements"], anno_scolastico=anno_scolastico,
            )
            repo_tex_path = repo_project / f"{repo_base}.tex"
            repo_tex_path.write_text(repo_tex, encoding="utf-8")
            repo_zip = OUTPUT_DIR / f"{repo_base}.zip"
            create_latex_zip(repo_project, repo_zip)
            st.session_state["repo_project"] = str(repo_project)
            st.session_state["repo_tex_path"] = str(repo_tex_path)
            st.session_state["repo_zip"] = str(repo_zip)
            st.session_state["repo_asset_errors"] = repo_assets["errors"]
            st.session_state.pop("repo_pdf", None)
            st.rerun()

        if "repo_zip" in st.session_state:
            repo_zip = Path(st.session_state["repo_zip"])
            repo_tex_path = Path(st.session_state["repo_tex_path"])
            repo_has_assets = any(Path(st.session_state["repo_project"]).joinpath("assets").glob("*"))
            if repo_has_assets:
                st.download_button("⬇️ Scarica repository LaTeX + immagini", repo_zip.read_bytes(), repo_zip.name, "application/zip", use_container_width=True, key="download_repo_package")
            else:
                st.download_button("⬇️ Scarica repository LaTeX", repo_tex_path.read_bytes(), repo_tex_path.name, "text/plain", use_container_width=True, key="download_repo_tex")
            for err in st.session_state.get("repo_asset_errors", []):
                st.warning(err)
            if st.button("☁️ Genera PDF online", key="compile_repo_online", use_container_width=True):
                with st.spinner("Invio la repository a LaTeX.Online…"):
                    try:
                        pdf = compile_project_online(Path(st.session_state["repo_project"]), repo_tex_path)
                        st.session_state["repo_pdf"] = pdf
                        st.session_state["repo_pdf_name"] = repo_tex_path.with_suffix(".pdf").name
                        st.session_state["repo_pdf_error"] = None
                    except Exception as exc:
                        st.session_state["repo_pdf_error"] = str(exc)
            if st.session_state.get("repo_pdf_error"):
                st.error(st.session_state["repo_pdf_error"])
            if "repo_pdf" in st.session_state:
                st.download_button("⬇️ Scarica PDF online", st.session_state["repo_pdf"], st.session_state.get("repo_pdf_name", "repository.pdf"), "application/pdf", use_container_width=True, key="download_repo_pdf")
    else:
        st.info("Nessuna classe disponibile per questa disciplina.")

st.sidebar.divider()
if st.sidebar.button("🗑️ Azzera storico", use_container_width=True):
    db.clear_history()
    st.sidebar.success("Storico cancellato.")
    st.rerun()

with st.expander("📚 Storico verifiche"):
    rows = db.get_tests(20)
    if rows:
        history_columns = [
            "ID",
            "Data",
            "Materia",
            "Classe",
            "Punti",
            "Tempo (min)",
            "Seed",
        ]
        history_df = pd.DataFrame(rows, columns=history_columns)
        st.dataframe(
            history_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn("ID", format="%d"),
                "Data": st.column_config.TextColumn("Data"),
                "Materia": st.column_config.TextColumn("Materia"),
                "Classe": st.column_config.TextColumn("Classe"),
                "Punti": st.column_config.NumberColumn("Punti", format="%.2f"),
                "Tempo (min)": st.column_config.NumberColumn("Tempo (min)", format="%.1f"),
                "Seed": st.column_config.NumberColumn("Seed", format="%d"),
            },
        )
    else:
        st.info("Nessuna verifica generata.")
