"""
Log detalhado de execução (fases, tarefas, chamadas de API e consultas à Collection).

Cada etapa gera dois eventos — "inicio" e "fim" — com horário local em
microssegundos, duração medida por relógio monotônico e a etapa-pai, formando
uma árvore: fase > tarefa > chamada de API / consulta à Collection.

Saídas (diretório ``logs/`` do projeto, ou ``SARAH_LOG_DIR``):
- ``execucao_AAAAMMDD.jsonl``: um evento JSON por linha (lido pela auditoria)
- ``execucao_AAAAMMDD.log``: mesma informação em texto legível

Variáveis de ambiente:
- ``SARAH_LOG_DIR``: diretório dos logs
- ``SARAH_LOG_CONSOLE=0``: não ecoa os eventos no terminal

Uso:
    with etapa("cartao", categoria=FASE, arquivo="autos.md"):
        with etapa("chat.completions", categoria=API, modelo="grok-4.6") as reg:
            resposta = requests.post(...)
            reg.registrar_http(resposta)
"""

from __future__ import annotations

import contextvars
import json
import logging
import os
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

FASE = "fase"
TAREFA = "tarefa"
API = "api"
COLLECTION = "collection"

SESSAO_ID = f"{datetime.now():%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"

_etapa_atual: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "sarah_etapa_atual", default=None
)
_lock = threading.Lock()
_logger_texto: Optional[logging.Logger] = None
_arquivo_jsonl: Optional[Path] = None
_configurado = False


def diretorio_logs() -> Path:
    personalizado = os.environ.get("SARAH_LOG_DIR")
    if personalizado:
        return Path(personalizado)
    return Path(__file__).resolve().parent / "logs"


def _configurar() -> None:
    global _logger_texto, _arquivo_jsonl, _configurado
    with _lock:
        if _configurado:
            return
        _configurado = True

        logger = logging.getLogger("sarah.execucao")
        logger.setLevel(logging.INFO)
        logger.propagate = False

        try:
            pasta = diretorio_logs()
            pasta.mkdir(parents=True, exist_ok=True)
            dia = f"{datetime.now():%Y%m%d}"
            _arquivo_jsonl = pasta / f"execucao_{dia}.jsonl"
            handler_arquivo = logging.FileHandler(
                pasta / f"execucao_{dia}.log", encoding="utf-8"
            )
            handler_arquivo.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler_arquivo)
        except OSError:
            _arquivo_jsonl = None

        if os.environ.get("SARAH_LOG_CONSOLE", "1") != "0":
            handler_console = logging.StreamHandler()
            handler_console.setFormatter(logging.Formatter("[sarah] %(message)s"))
            logger.addHandler(handler_console)

        _logger_texto = logger


def _agora_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="microseconds")


def _formatar_dados(dados: Dict[str, Any]) -> str:
    partes = []
    for chave, valor in dados.items():
        if valor is None or valor == "":
            continue
        texto = str(valor).replace("\n", " ")
        if len(texto) > 120:
            texto = texto[:117] + "..."
        partes.append(f"{chave}={texto}")
    return " ".join(partes)


def _emitir(evento: Dict[str, Any]) -> None:
    _configurar()
    linha_json = json.dumps(evento, ensure_ascii=False, default=str)
    with _lock:
        if _arquivo_jsonl is not None:
            try:
                with open(_arquivo_jsonl, "a", encoding="utf-8") as f:
                    f.write(linha_json + "\n")
            except OSError:
                pass

    if _logger_texto is None:
        return
    hora = evento["ts"][11:26]
    tipo = evento["evento"].upper()
    cabecalho = (
        f"{hora} | {tipo:<6} | {evento['categoria']:<10} | {evento['nome']}"
        f" | id={evento['id']}"
    )
    if evento.get("pai"):
        cabecalho += f" pai={evento['pai']}"
    if evento["evento"] == "fim":
        cabecalho += f" | {evento['duracao_s']:.3f}s {evento['status']}"
        if evento.get("erro"):
            cabecalho += f" erro={evento['erro']}"
    extras = _formatar_dados(evento.get("dados") or {})
    if extras:
        cabecalho += f" | {extras}"
    _logger_texto.info(cabecalho)


class RegistroEtapa:
    """Etapa em andamento; permite anexar dados que serão gravados no evento de fim."""

    def __init__(self, nome: str, categoria: str, pai: Optional[str], dados: Dict[str, Any]):
        self.id = uuid.uuid4().hex[:10]
        self.nome = nome
        self.categoria = categoria
        self.pai = pai
        self.dados_inicio = dados
        self.dados: Dict[str, Any] = {}
        self.status = "ok"
        self.erro: Optional[str] = None

    def atualizar(self, **dados: Any) -> None:
        self.dados.update(dados)

    def marcar_erro(self, mensagem: str) -> None:
        """Registra falha tratada pelo chamador (sem exceção propagada)."""
        self.status = "erro"
        self.erro = str(mensagem)[:500]

    def registrar_http(self, response: Any) -> None:
        self.atualizar(http_status=getattr(response, "status_code", None))

    def registrar_uso(self, resultado: Any) -> None:
        """Extrai contagem de tokens do JSON de chat/completions."""
        if not isinstance(resultado, dict):
            return
        uso = resultado.get("usage") or {}
        if not isinstance(uso, dict):
            return
        detalhes_saida = uso.get("completion_tokens_details") or {}
        detalhes_entrada = uso.get("prompt_tokens_details") or {}
        self.atualizar(
            tokens_entrada=uso.get("prompt_tokens"),
            tokens_saida=uso.get("completion_tokens"),
            tokens_reasoning=detalhes_saida.get("reasoning_tokens"),
            tokens_cache=detalhes_entrada.get("cached_tokens"),
            tokens_total=uso.get("total_tokens"),
        )


@contextmanager
def etapa(nome: str, categoria: str = TAREFA, **dados: Any) -> Iterator[RegistroEtapa]:
    """Registra início e fim de uma etapa, aninhando-a na etapa corrente."""
    registro = RegistroEtapa(nome, categoria, _etapa_atual.get(), dados)
    inicio_ts = _agora_iso()
    _emitir({
        "ts": inicio_ts,
        "evento": "inicio",
        "sessao": SESSAO_ID,
        "id": registro.id,
        "pai": registro.pai,
        "categoria": categoria,
        "nome": nome,
        "thread": threading.current_thread().name,
        "dados": dados,
    })

    token = _etapa_atual.set(registro.id)
    inicio = time.perf_counter()
    try:
        yield registro
    except BaseException as exc:
        registro.status = "erro"
        registro.erro = f"{type(exc).__name__}: {exc}"[:500]
        raise
    finally:
        duracao = time.perf_counter() - inicio
        _etapa_atual.reset(token)
        _emitir({
            "ts": _agora_iso(),
            "evento": "fim",
            "sessao": SESSAO_ID,
            "id": registro.id,
            "pai": registro.pai,
            "categoria": categoria,
            "nome": nome,
            "thread": threading.current_thread().name,
            "inicio": inicio_ts,
            "duracao_s": round(duracao, 6),
            "status": registro.status,
            "erro": registro.erro,
            "dados": {**dados, **registro.dados},
        })
