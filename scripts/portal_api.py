"""API local do site do curso: progresso por aula e estado dos serviços.

[Complemento da plataforma] Roda no container `curso`, ao lado do site, e só usa a biblioteca
padrão. Junta duas fontes, sem inventar nada:

- `progress/historico.jsonl`: resultado REAL dos checks (gravado pelo labcheck/conftest.py);
- `progress/estudo.json`: o que você marcou nas páginas (critérios de conclusão e aula concluída).

Rotas:
    GET  /api/progresso   progresso de todas as aulas + URLs e estado dos serviços
    POST /api/estudo      {"aula": 7, "criterio": "texto do item", "marcado": true}
                          {"aula": 7, "concluida": true}
    POST /api/sessao      login automático nas ferramentas embutidas: devolve o token do
                          JupyterLab e entrega o cookie de sessão do console do MinIO (feito
                          com o usuário da aplicação, nunca com o root). Só aceita o próprio site.

Uso: python -m scripts.portal_api   (porta 8001; PORTAL_PORTA muda)
"""
import json
import os
import threading
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from scripts.gerar_curso import META, arquivo_de_checks, checks

PROGRESSO = Path(os.getenv("PORTAL_PROGRESSO", "progress"))
HISTORICO = PROGRESSO / "historico.jsonl"
ESTUDO = PROGRESSO / "estudo.json"
ORIGENS = {"http://localhost:8000", "http://127.0.0.1:8000"}
TRAVA = threading.Lock()

# URLs que o NAVEGADOR usa (porta no host) e endereços internos para checar se o serviço está no ar
SERVICOS = {
    "jupyter": (os.getenv("CURSO_JUPYTER_URL", "http://localhost:8888"), "http://spark:8888/api"),
    "minio": (os.getenv("CURSO_MINIO_URL", "http://localhost:9001"),
              "http://minio:9000/minio/health/live"),
    "sparkui": (os.getenv("CURSO_SPARKUI_URL", "http://localhost:4040"), "http://spark:4040"),
}


def checks_declarados() -> dict[int, list[str]]:
    """{aula: [ids dos checks]} lidos dos arquivos de teste, como o site faz."""
    import yaml

    aulas = yaml.safe_load(META.read_text(encoding="utf-8"))["aulas"]
    saida = {}
    for a in aulas:
        arq = arquivo_de_checks(a["aula"])
        saida[a["aula"]] = [c for c, _ in checks(arq)] if arq else []
    return saida


def ultimos_resultados(linhas: list[str]) -> dict[int, dict[str, dict]]:
    """{aula: {check: registro mais recente}} a partir das linhas do histórico."""
    ultimo: dict[int, dict[str, dict]] = {}
    for linha in linhas:
        if not linha.strip():
            continue
        r = json.loads(linha)
        ultimo.setdefault(r["aula"], {})[r["check"]] = r  # a execução mais recente vence
    return ultimo


def resumo(declarados: dict[int, list[str]], resultados: dict, estudo: dict) -> dict:
    aulas = {}
    for aula, ids in declarados.items():
        rs = resultados.get(aula, {})
        e = estudo.get(str(aula), {})
        aulas[str(aula)] = {
            "checks": {
                "declarados": len(ids),
                "passou": sum(rs.get(c, {}).get("status") == "passou" for c in ids),
                "falhou": sum(rs.get(c, {}).get("status") == "falhou" for c in ids),
                "ultima": max((r["ts"] for r in rs.values()), default=None),
                "itens": {c: rs[c]["status"] for c in ids if c in rs},
            },
            "criterios": e.get("criterios", {}),
            "concluida_em": e.get("concluida_em"),
        }
    return aulas


def no_ar(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=1.5):
            return True
    except urllib.error.HTTPError:
        return True  # respondeu, mesmo que com 403/404: o serviço está de pé
    except OSError:
        return False


def login_minio() -> str | None:
    """Entra no console do MinIO como rais-app e devolve o cookie de sessão (ou None)."""
    chave, segredo = os.getenv("APP_ACCESS_KEY"), os.getenv("APP_SECRET_KEY")
    if not (chave and segredo):
        return None
    pedido = urllib.request.Request(
        os.getenv("MINIO_CONSOLE_INTERNO", "http://minio:9001") + "/api/v1/login",
        data=json.dumps({"accessKey": chave, "secretKey": segredo}).encode(),
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(pedido, timeout=5) as resp:
            for valor in resp.headers.get_all("Set-Cookie") or []:
                if valor.startswith("token="):
                    return valor.split(";", 1)[0].removeprefix("token=")
    except OSError:
        pass
    return None


def ler_estudo() -> dict:
    return json.loads(ESTUDO.read_text(encoding="utf-8")) if ESTUDO.exists() else {}


def gravar_estudo(dados: dict) -> None:
    PROGRESSO.mkdir(exist_ok=True)
    tmp = ESTUDO.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(ESTUDO)  # troca atômica: nunca deixa o arquivo pela metade


def aplicar(estudo: dict, pedido: dict) -> dict:
    """Aplica um POST /api/estudo ao estado e devolve o novo estado da aula."""
    aula = str(int(pedido["aula"]))
    e = estudo.setdefault(aula, {"criterios": {}, "concluida_em": None})
    if "criterio" in pedido:
        chave = str(pedido["criterio"]).strip()[:300]
        if pedido.get("marcado"):
            e["criterios"][chave] = True
        else:
            e["criterios"].pop(chave, None)
    if "concluida" in pedido:
        agora = datetime.now().astimezone().isoformat(timespec="seconds")
        e["concluida_em"] = agora if pedido["concluida"] else None
    return e


class Handler(BaseHTTPRequestHandler):
    def _responder(self, status: int, corpo: dict | None = None, cookies=()) -> None:
        dados = json.dumps(corpo or {}, ensure_ascii=False).encode()
        self.send_response(status)
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        origem = self.headers.get("Origin")
        if origem in ORIGENS:
            self.send_header("Access-Control-Allow-Origin", origem)
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Allow-Credentials", "true")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_OPTIONS(self):  # noqa: N802 (nome exigido pelo http.server)
        self._responder(204)

    def do_GET(self):  # noqa: N802
        if self.path != "/api/progresso":
            return self._responder(404, {"erro": "rota inexistente"})
        linhas = HISTORICO.read_text(encoding="utf-8").splitlines() if HISTORICO.exists() else []
        self._responder(200, {
            "aulas": resumo(checks_declarados(), ultimos_resultados(linhas), ler_estudo()),
            "servicos": {nome: {"url": url, "no_ar": no_ar(interno)}
                         for nome, (url, interno) in SERVICOS.items()},
        })

    def do_POST(self):  # noqa: N802
        # Só aceita pedidos vindos do próprio site (bloqueia outras páginas abertas no navegador)
        if self.headers.get("Origin") not in ORIGENS:
            return self._responder(403, {"erro": "origem não permitida"})
        if self.path == "/api/sessao":
            # Cookies valem por host, não por porta: o cookie gravado aqui (localhost) também
            # vai para o console do MinIO em localhost:<porta>, que abre já logado.
            token = login_minio()
            cookie = f"token={token}; Path=/; Max-Age=43200; HttpOnly; SameSite=Lax"
            cookies = [cookie] if token else []
            return self._responder(200, {"jupyter_token": os.getenv("JUPYTER_TOKEN", ""),
                                         "minio": bool(token)}, cookies)
        if self.path != "/api/estudo":
            return self._responder(404, {"erro": "rota inexistente"})
        try:
            tamanho = min(int(self.headers.get("Content-Length", 0)), 10_000)
            pedido = json.loads(self.rfile.read(tamanho))
            with TRAVA:
                estudo = ler_estudo()
                aula = aplicar(estudo, pedido)
                gravar_estudo(estudo)
        except (ValueError, KeyError, TypeError) as erro:
            return self._responder(400, {"erro": str(erro)})
        self._responder(200, aula)

    def log_message(self, formato, *args):  # silencia o log de cada GET
        pass


def main() -> None:
    porta = int(os.getenv("PORTAL_PORTA", "8001"))
    print(f"[portal] API em http://0.0.0.0:{porta}/api/progresso")
    ThreadingHTTPServer(("0.0.0.0", porta), Handler).serve_forever()


if __name__ == "__main__":
    main()
