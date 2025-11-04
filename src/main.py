from pathlib import Path
import csv, sys
import json
from typing import Any, List, Dict
from mcp.server.fastmcp import FastMCP

try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    csv.field_size_limit(2**31 - 1)  # ~2.1 miliardi di caratteri

mcp = FastMCP("CSV Analyst")

DATA_DIR = (Path(__file__).parents[1] / "data").resolve()

# ------------------------- Resources -------------------------

@mcp.resource("csv://index")
def csv_index() -> str:
    """Lista dei file CSV disponibili sotto DATA_DIR."""
    files = sorted(p.name for p in DATA_DIR.glob("*.csv"))
    if not files:
        return f"Nessun CSV trovato in {DATA_DIR}"
    return "CSV disponibili:\n" + "\n".join(f"- {name}" for name in files)

# --------------------------- Tools ---------------------------

@mcp.tool()
def list_csvs() -> List[str]:
    """Ritorna i nomi dei CSV presenti in DATA_DIR."""
    return sorted(p.name for p in DATA_DIR.glob("*.csv"))

@mcp.tool()
def preview_csv(filename: str, n: int = 5) -> Dict[str, Any]:
    """
    Ritorna header e prime N righe del CSV.
    filename: nome file (es. 'games.csv') presente in DATA_DIR.
    """
    path = (DATA_DIR / filename).resolve()
    _validate_path(path)
    rows: List[Dict[str, str]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = reader.fieldnames or []
        for i, row in enumerate(reader):
            if i >= n:
                break
            rows.append(row)
    return {"columns": header, "rows": rows, "count_returned": len(rows)}

@mcp.tool()
def describe_csv(filename: str, sample_rows: int = 1000) -> Dict[str, Any]:
    """
    Calcola statistiche leggere su max 'sample_rows' righe:
    - tipo stimato (numeric / text_or_mixed)
    - nulls / non_nulls
    - min/max per numeric
    """
    path = (DATA_DIR / filename).resolve()
    _validate_path(path)

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        stats: Dict[str, Dict[str, Any]] = {
            c: {"nulls": 0, "non_nulls": 0, "numeric": True, "min": None, "max": None}
            for c in cols
        }

        row_count = 0
        for i, row in enumerate(reader):
            if i >= sample_rows:
                break
            row_count += 1
            for c in cols:
                val = row.get(c, "")
                if val is None or val == "":
                    stats[c]["nulls"] += 1
                else:
                    stats[c]["non_nulls"] += 1
                    try:
                        x = float(val)
                        if stats[c]["min"] is None or x < stats[c]["min"]:
                            stats[c]["min"] = x
                        if stats[c]["max"] is None or x > stats[c]["max"]:
                            stats[c]["max"] = x
                    except ValueError:
                        stats[c]["numeric"] = False

        summary: Dict[str, Any] = {}
        for c, s in stats.items():
            inferred_type = "numeric" if s["numeric"] and s["non_nulls"] > 0 else "text_or_mixed"
            summary[c] = {
                "type": inferred_type,
                "nulls": s["nulls"],
                "non_nulls": s["non_nulls"],
                "min": s["min"] if inferred_type == "numeric" else None,
                "max": s["max"] if inferred_type == "numeric" else None,
            }

        sampled_rows = row_count
        return {"columns": list(cols), "summary": summary, "sampled_rows": sampled_rows}

@mcp.tool()
def filter_equals(filename: str, column: str, value: str, limit: int = 10) -> Dict[str, Any]:
    """
    Filtra le righe dove 'column' == 'value'.
    - prova confronto numerico se possibile, altrimenti confronto stringhe (trim)
    """
    path = (DATA_DIR / filename).resolve()
    _validate_path(path)

    # normalizza il "value" in due forme: numerica (se possibile) e testuale
    value_str = (value or "").strip()
    try:
        value_num = float(value_str)
    except ValueError:
        value_num = None

    out_rows: List[Dict[str, str]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        if column not in cols:
            raise ValueError(f"Colonna '{column}' non trovata. Disponibili: {cols}")

        for row in reader:
            cell = row.get(column, "")
            cell_str = (cell or "").strip()

            match = False
            if value_num is not None:
                # prova confronto numerico
                try:
                    cell_num = float(cell_str)
                    match = (cell_num == value_num)
                except ValueError:
                    match = False
            if not match:
                # fallback: confronto stringhe
                match = (cell_str == value_str)

            if match:
                out_rows.append(row)
                if len(out_rows) >= limit:
                    break

    return {"columns": reader.fieldnames or [], "rows": out_rows, "count_returned": len(out_rows)}

# Diagnostica utile
@mcp.tool()
def debug_paths() -> Dict[str, Any]:
    return {
        "data_dir": str(DATA_DIR),
        "exists": DATA_DIR.exists(),
        "csv_found": sorted(p.name for p in DATA_DIR.glob("*.csv")),
    }

def _validate_path(path: Path) -> None:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"File non trovato: {path}")
    if DATA_DIR not in path.parents:
        raise PermissionError("Accesso negato: file fuori da DATA_DIR")

# -------------------------- Prompts --------------------------

# Accetta sia lista JSON (["col1", "col2"]) che stringa "col1,col2"
@mcp.prompt("explain_columns", description="Spiega le colonne di un CSV e suggerisci analisi.")
def prompt_explain_columns(filename: str, columns: list[str] | str) -> str:
    if isinstance(columns, str):
        try:
            parsed = json.loads(columns)
            columns = parsed if isinstance(parsed, list) else [str(parsed)]
        except Exception:
            columns = [c.strip() for c in columns.split(",") if c.strip()]
    return (
        f'Hai un file CSV chiamato "{filename}" con queste colonne:\n'
        f"{columns}\n\n"
        "Spiega in linguaggio semplice cosa significa ciascuna colonna, cosa rappresenta, "
        "e suggerisci almeno due tipi di analisi/visualizzazioni utili."
    )

# Evitiamo 'Any' per compat massima: usiamo 'object'
@mcp.prompt("detect_anomalies", description="Individua possibili anomalie/outlier a partire dal riepilogo.")
def prompt_detect_anomalies(filename: str, summary: dict[str, object] | str) -> str:
    if isinstance(summary, str):
        try:
            summary = json.loads(summary)
        except Exception:
            return (
                "Il campo 'summary' deve essere JSON valido. "
                'Esempio: {"price":{"type":"numeric","nulls":0,"min":0,"max":59.99}}'
            )
    return (
        f'Il file "{filename}" ha queste statistiche:\n{summary}\n\n'
        "- Indica colonne con possibili valori anomali e perché.\n"
        "- Suggerisci controlli aggiuntivi per verificarle.\n"
        "- Proponi una strategia/visualizzazione per approfondire gli outlier."
    )

@mcp.prompt("generate_query", description="Genera una query in linguaggio naturale per estrarre un subset dal CSV.")
def prompt_generate_query(filename: str, objective: str) -> str:
    return (
        f'File: "{filename}"\nObiettivo: {objective}\n\n'
        "Genera una query in linguaggio naturale che:\n"
        "- filtra il dataset in linea con l’obiettivo;\n"
        "- indica colonne per filtro/raggruppamento/ordinamento;\n"
        "- descrive come implementarla in pandas o col tool filter_equals."
    )

# --------------------------- Runner --------------------------

if __name__ == "__main__":
    # Avvia il server MCP in HTTP (streamable)
    print("Avvio MCP server su http://0.0.0.0:8000/mcp ...")
    mcp.run_http(port=8000)
