# CSV Analyst — MCP Server

Un piccolo server MCP (Model Context Protocol) scritto in Python, progettato per esplorare e analizzare file CSV.  
Permette di elencare, visualizzare, filtrare e descrivere dataset tramite strumenti (`@mcp.tool`) e prompt interattivi.

## Requisiti

- Python **3.10+**

---

## Installazione

Clona il repository:

```bash
git clone https://github.com/Shore99/MCP_Test.git
```

Installa le dipendenze:

```
pip install -r requirements.txt
```
Inserire nella cartella "data" i CSV da analizzare

##Avvio del server MCP (CLI MCP)

Aprire due terminali diversi, assicurandosi di essere nel path src.

Eseguire nel primo (MCP Inspector):
```
mcp dev main.py  
```
Mentre nel secondo (Avvio Server):
```
mcp run src/main.py --transport=streamable-http
```

Struttura del progetto
```
.
├── src/
│   └── main.py              # Logica MCP server (tools, resources, prompts)
├── data                     # Cartella per i CSV locali (non versionati)
├── requirements.txt         # Dipendenze (mcp[cli], uvicorn)
├── .gitignore
├── README.md
```
Esempi di utilizzo (tools MCP)
```
Tool	                                Descrizione
list_csvs()	                        #Elenca i file CSV nella cartella data/
preview_csv(filename, n)	        #Mostra le prime n righe del file
describe_csv(filename)	                #Calcola statistiche di base sulle colonne
filter_equals(filename, column, value)	#Filtra le righe dove column == value
```
Esempio mcp.json
```
{
  "name": "CSV Analyst",
  "version": "0.1.0",
  "transport": {
    "type": "http",
    "url": "http://127.0.0.1:8000/mcp"
  },
  "metadata": {
    "description": "Simple MCP server to inspect CSV files under ./data"
  }
}
```
