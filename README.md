# Software verifiche — versione online V1

Versione separata del **Software verifiche V20**, predisposta per essere pubblicata come app Streamlit online.

## Cosa contiene

- repository di esercizi `.tex` con metadati;
- selezione manuale e automatica degli esercizi;
- vincoli di difficoltà, punti e tempo;
- storico degli esercizi già utilizzati;
- anno scolastico configurabile;
- gestione delle immagini locali e remote;
- generazione del compito LaTeX;
- generazione online del PDF del compito;
- generazione online del PDF delle soluzioni;
- esportazione della repository;
- punteggi nel formato `1. (1 Punto)` / `2. (2 Punti)` sia nelle verifiche sia nella repository;
- 0,6 cm dopo ogni domanda e 1 cm prima della tabella finale dei punteggi.

## Pubblicazione online

Questa cartella è pensata per essere caricata in un repository GitHub e collegata a Streamlit Community Cloud.

Il file di ingresso è:

```text
app.py
```

Le dipendenze Python sono in `requirements.txt`.

## Avvio locale

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Nota sulla cronologia online

La cronologia usa SQLite (`database.sqlite`). In un deployment cloud la cronologia è disponibile durante la vita dell'istanza, ma il filesystem locale dell'app non va considerato uno storage permanente. Se in futuro si vuole una cronologia persistente anche dopo riavvii/redeploy, sarà possibile sostituire SQLite con un database online senza modificare il resto del programma.

## Compilazione PDF

Il PDF viene compilato tramite servizi LaTeX online; non è necessario installare una distribuzione LaTeX sul server Streamlit.
