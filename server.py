#!/usr/bin/env python3
"""
Servidor do Chá de Bebê da Olívia
Serve a landing page + API de recados (salva em JSON)
"""
import json
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECADOS_FILE = os.path.join(BASE_DIR, "recados.json")
HOST = "0.0.0.0"
PORT = 8080


def load_recados():
    if os.path.exists(RECADOS_FILE):
        with open(RECADOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_recados(recados):
    with open(RECADOS_FILE, "w", encoding="utf-8") as f:
        json.dump(recados, f, ensure_ascii=False, indent=2)


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/recados":
            recados = load_recados()
            self._send_json(recados)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/recados":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(body)
                nome = data.get("nome", "").strip()
                recado = data.get("recado", "").strip()

                if not nome or not recado:
                    self._send_json({"error": "Nome e recado são obrigatórios"}, 400)
                    return

                if len(nome) > 60 or len(recado) > 500:
                    self._send_json({"error": "Nome (máx 60) ou recado (máx 500) muito longo"}, 400)
                    return

                recados = load_recados()
                now = datetime.now().strftime("%d/%m/%Y %H:%M")
                recados.append({"nome": nome, "recado": recado, "data": now})
                save_recados(recados)

                self._send_json({"success": True, "total": len(recados)})
            except json.JSONDecodeError:
                self._send_json({"error": "JSON inválido"}, 400)
            return

        self.send_response(404)
        self.end_headers()

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")


if __name__ == "__main__":
    print(f"\n🌸  Chá de Bebê da Olívia — Servidor rodando! 🍼")
    print(f"    Local:   http://localhost:{PORT}")
    print(f"    Rede:    http://<seu-ip>:{PORT}")
    print(f"    Pressione Ctrl+C para parar\n")
    server = HTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Servidor encerrado.")
        server.server_close()
