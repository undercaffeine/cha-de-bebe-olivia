#!/usr/bin/env python3
"""
Script do cron: lê recados da planilha Google e atualiza o index.html estático.
Mostra apenas: Nome, Recado, Timestamp (valor fica oculto).
"""
import json
import os
import re
import time
import urllib.request
import urllib.parse

# Config
INDEX_PATH = os.path.expanduser("~/AI/cha-de-bebe-olivia-static/index.html")
TOKEN_FILE = os.path.expanduser("~/.hermes/mcp-tokens/google-workspace.json")
CLIENT_FILE = os.path.expanduser("~/.hermes/mcp-tokens/google-workspace.client.json")
GATEWAY = "https://ai-agent-gateway.ifoodcorp.com.br/mcp/external/google-workspace"
SPREADSHEET_ID = "1zGw404HCpaFxNhqIJWlSIBPvjwDzHNGc-NFF-TfPM2g"
SHEET_RANGE = "'Form Responses 1'!A:D"


def load_token():
    with open(TOKEN_FILE) as f:
        d = json.load(f)
    if time.time() > d.get("expires_at", 0):
        with open(CLIENT_FILE) as cf:
            client = json.load(cf)
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": d["refresh_token"],
            "client_id": client["client_id"],
        }).encode()
        req = urllib.request.Request(
            GATEWAY + "/token", data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            result["expires_at"] = time.time() + result.get("expires_in", 3599)
            with open(TOKEN_FILE, "w") as f:
                json.dump(result, f, indent=2)
        return result["access_token"]
    return d["access_token"]


def call_gateway(method, params):
    token = load_token()
    payload = json.dumps({
        "jsonrpc": "2.0", "id": 1,
        "method": "tools/call",
        "params": {"name": method, "arguments": params},
    }).encode()
    req = urllib.request.Request(
        GATEWAY, data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode()
        for line in raw.split("\n"):
            if line.startswith("data:"):
                data_str = line[5:].strip()
                if data_str:
                    result = json.loads(data_str)
                    return result["result"]["content"][0]["text"]
    return None


def read_recados():
    """Lê os recados da planilha e retorna lista de dicts."""
    text = call_gateway("read_sheet_values", {
        "spreadsheet_id": SPREADSHEET_ID,
        "range_name": SHEET_RANGE,
    })
    rows = []
    for line in text.split("\n"):
        m = re.search(r"Row\s+\d+:\s*\[(.*)\]", line)
        if m:
            inner = m.group(1)
            parts = []
            current = ""
            in_str = False
            i = 0
            while i < len(inner):
                c = inner[i]
                if c == "'" and (i == 0 or inner[i - 1] != "\\"):
                    if in_str:
                        parts.append(current)
                        current = ""
                        in_str = False
                        i += 1
                        if i < len(inner) and inner[i] == ",":
                            i += 1
                        if i < len(inner) and inner[i] == " ":
                            i += 1
                        continue
                    else:
                        in_str = True
                        i += 1
                        continue
                if in_str:
                    current += c
                i += 1
            # parts: [Timestamp, Nome, Recado, Valor]
            if len(parts) >= 3 and parts[0] != "Timestamp":
                rows.append({
                    "data": parts[0],
                    "nome": parts[1],
                    "recado": parts[2],
                })
    return rows


def esc(s):
    """Escape HTML."""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def build_wall_html(recados):
    """Gera o HTML do mural de recados."""
    count = len(recados)
    count_text = f"{count} {'recado' if count == 1 else 'recados'}"

    if count == 0:
        messages_html = '<div class="no-messages">Nenhum recado ainda. Seja o primeiro! ✨</div>'
    else:
        cards = []
        for r in reversed(recados):
            cards.append(
                '<div class="message-card">'
                f'<div class="msg-name">{esc(r["nome"])}</div>'
                f'<div class="msg-text">{esc(r["recado"])}</div>'
                f'<div class="msg-date">{esc(r["data"])}</div>'
                '</div>'
            )
        messages_html = "\n".join(cards)

    return f"""    <!-- Mural de recados (atualizado automaticamente) -->
    <!-- RECADOS_WALL_START -->
    <div class="card recados-card">
        <div class="msg-count" id="msgCount">{count_text}</div>
        <div class="messages-wall" id="messagesWall">
            {messages_html}
        </div>
    </div>
    <!-- RECADOS_WALL_END -->"""


def update_index(recados):
    """Substitui o bloco RECADOS_WALL no index.html."""
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    new_wall = build_wall_html(recados)
    pattern = r"<!-- RECADOS_WALL_START -->.*?<!-- RECADOS_WALL_END -->"
    content = re.sub(pattern, new_wall, content, flags=re.DOTALL)

    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    return len(recados)


if __name__ == "__main__":
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Lendo recados da planilha...")
    try:
        recados = read_recados()
        count = update_index(recados)
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Site atualizado com {count} recados!")
    except Exception as e:
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] ERRO: {e}")
        raise
