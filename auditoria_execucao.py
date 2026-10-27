#!/usr/bin/env python3
"""
Auditoria de execução do AppSarah.

Lê os eventos gravados por ``log_execucao`` (arquivos ``logs/execucao_*.jsonl``)
e gera um relatório em Markdown com a duração de cada fase, tarefa, chamada
de API e consulta à Collection.

Exemplos:
    python auditoria_execucao.py                       # todos os logs em logs/
    python auditoria_execucao.py --ultima              # só a sessão mais recente
    python auditoria_execucao.py --data 20261012       # só o arquivo do dia
    python auditoria_execucao.py --fase minuta --saida relatorio.md --csv etapas.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

PASTA_LOGS_PADRAO = Path(__file__).resolve().parent / "logs"
CATEGORIAS_REMOTAS = ("api", "collection")

# US$ por 1 milhão de tokens (https://docs.x.ai/developers/pricing, consultado em 12/10/2026).
# A partir de LIMIAR_CONTEXTO_LONGO tokens de prompt, a tarifa "longo" vale para a chamada inteira.
LIMIAR_CONTEXTO_LONGO = 200_000
PRECOS_PADRAO: Dict[str, Dict[str, float]] = {
    "grok-4.7": {"entrada": 2.00, "cache": 0.50, "saida": 6.00,
                 "entrada_longo": 4.00, "cache_longo": 1.00, "saida_longo": 12.00},
    "grok-4.6": {"entrada": 2.00, "cache": 0.50, "saida": 6.00,
                 "entrada_longo": 4.00, "cache_longo": 1.00, "saida_longo": 12.00},
    "grok-4.5": {"entrada": 2.00, "cache": 0.30, "saida": 6.00,
                 "entrada_longo": 4.00, "cache_longo": 0.60, "saida_longo": 12.00},
}


@dataclass
class Etapa:
    id: str
    sessao: str
    nome: str
    categoria: str
    pai: Optional[str]
    inicio: datetime
    fim: Optional[datetime] = None
    duracao_s: float = 0.0
    status: str = "incompleta"
    erro: Optional[str] = None
    dados: Dict[str, Any] = field(default_factory=dict)
    filhos: List["Etapa"] = field(default_factory=list)

    @property
    def completa(self) -> bool:
        return self.fim is not None


# --------------------------------------------------------------------------- #
# Leitura
# --------------------------------------------------------------------------- #

def localizar_arquivos(caminhos: List[str], data: Optional[str]) -> List[Path]:
    alvos = [Path(c) for c in caminhos] if caminhos else [PASTA_LOGS_PADRAO]
    arquivos: List[Path] = []
    for alvo in alvos:
        if alvo.is_dir():
            padrao = f"execucao_{data}.jsonl" if data else "execucao_*.jsonl"
            arquivos.extend(sorted(alvo.glob(padrao)))
        elif alvo.is_file():
            arquivos.append(alvo)
    return arquivos


def ler_eventos(arquivos: Iterable[Path]) -> tuple[List[Dict[str, Any]], int]:
    eventos: List[Dict[str, Any]] = []
    invalidas = 0
    for arquivo in arquivos:
        with open(arquivo, encoding="utf-8") as f:
            for linha in f:
                linha = linha.strip()
                if not linha:
                    continue
                try:
                    eventos.append(json.loads(linha))
                except json.JSONDecodeError:
                    invalidas += 1
    return eventos, invalidas


def montar_etapas(eventos: List[Dict[str, Any]]) -> Dict[str, Etapa]:
    """Casa eventos de início e fim por id; etapas sem fim ficam 'incompletas'."""
    etapas: Dict[str, Etapa] = {}
    ultimo_ts_sessao: Dict[str, datetime] = {}

    for ev in eventos:
        try:
            ts = datetime.fromisoformat(ev["ts"])
        except (KeyError, ValueError):
            continue
        sessao = ev.get("sessao", "?")
        if sessao not in ultimo_ts_sessao or ts > ultimo_ts_sessao[sessao]:
            ultimo_ts_sessao[sessao] = ts

        etapa_id = ev.get("id")
        if not etapa_id:
            continue
        etapa = etapas.get(etapa_id)
        if etapa is None:
            inicio = ts
            if ev.get("evento") == "fim" and ev.get("inicio"):
                inicio = datetime.fromisoformat(ev["inicio"])
            etapa = Etapa(
                id=etapa_id,
                sessao=sessao,
                nome=ev.get("nome", "?"),
                categoria=ev.get("categoria", "?"),
                pai=ev.get("pai"),
                inicio=inicio,
                dados=dict(ev.get("dados") or {}),
            )
            etapas[etapa_id] = etapa

        if ev.get("evento") == "fim":
            etapa.fim = ts
            etapa.duracao_s = float(ev.get("duracao_s") or 0.0)
            etapa.status = ev.get("status", "ok")
            etapa.erro = ev.get("erro")
            etapa.dados.update(ev.get("dados") or {})

    for etapa in etapas.values():
        if not etapa.completa:
            limite = ultimo_ts_sessao.get(etapa.sessao, etapa.inicio)
            etapa.duracao_s = max(0.0, (limite - etapa.inicio).total_seconds())

    for etapa in etapas.values():
        if etapa.pai and etapa.pai in etapas:
            etapas[etapa.pai].filhos.append(etapa)
    for etapa in etapas.values():
        etapa.filhos.sort(key=lambda e: e.inicio)
    return etapas


def filtrar(
    etapas: Dict[str, Etapa],
    sessao: Optional[str],
    ultima: bool,
    fase: Optional[str],
) -> List[Etapa]:
    lista = list(etapas.values())
    if ultima and lista:
        sessao = max(lista, key=lambda e: e.inicio).sessao
    if sessao:
        lista = [e for e in lista if e.sessao == sessao]
    if fase:
        raizes = [e for e in lista if e.categoria == "fase" and e.nome == fase]
        selecionadas: List[Etapa] = []
        for raiz in raizes:
            selecionadas.extend(descendentes(raiz, incluir_raiz=True))
        lista = selecionadas
    return sorted(lista, key=lambda e: e.inicio)


def descendentes(etapa: Etapa, incluir_raiz: bool = False) -> List[Etapa]:
    resultado = [etapa] if incluir_raiz else []
    for filho in etapa.filhos:
        resultado.extend(descendentes(filho, incluir_raiz=True))
    return resultado


# --------------------------------------------------------------------------- #
# Formatação
# --------------------------------------------------------------------------- #

def fmt_dur(segundos: float) -> str:
    if segundos < 1:
        return f"{segundos * 1000:.0f} ms"
    if segundos < 60:
        return f"{segundos:.1f} s"
    minutos, seg = divmod(segundos, 60)
    if minutos < 60:
        return f"{int(minutos)} min {seg:04.1f} s"
    horas, minutos = divmod(int(minutos), 60)
    return f"{horas} h {minutos:02d} min {int(seg):02d} s"


def fmt_hora(dt: Optional[datetime]) -> str:
    return dt.strftime("%d/%m %H:%M:%S.%f")[:-3] if dt else "—"


def fmt_pct(parte: float, todo: float) -> str:
    return f"{100 * parte / todo:.0f}%" if todo > 0 else "—"


def fmt_int(valor: Any) -> str:
    return f"{int(valor):,}".replace(",", ".") if isinstance(valor, (int, float)) else "—"


def percentil(valores: List[float], p: float) -> float:
    ordenados = sorted(valores)
    if not ordenados:
        return 0.0
    k = max(0, min(len(ordenados) - 1, math.ceil(p / 100 * len(ordenados)) - 1))
    return ordenados[k]


def tabela(cabecalho: List[str], linhas: List[List[str]]) -> str:
    saida = ["| " + " | ".join(cabecalho) + " |", "|" + "|".join("---" for _ in cabecalho) + "|"]
    for linha in linhas:
        saida.append("| " + " | ".join(str(c).replace("|", "/") for c in linha) + " |")
    return "\n".join(saida)


def rotulo(etapa: Etapa) -> str:
    detalhes = []
    for chave in ("topico", "questao_id", "indice", "lote", "tentativa", "modelo", "reasoning", "consulta"):
        valor = etapa.dados.get(chave)
        if valor not in (None, ""):
            texto = str(valor)
            detalhes.append(f"{chave}={texto[:60]}")
    return f"{etapa.nome} ({', '.join(detalhes)})" if detalhes else etapa.nome


def tempo_por_categoria(etapa: Etapa) -> Dict[str, float]:
    """Soma o tempo das etapas remotas descendentes (sem dupla contagem)."""
    totais: Dict[str, float] = defaultdict(float)

    def visitar(e: Etapa) -> None:
        for filho in e.filhos:
            if filho.categoria in CATEGORIAS_REMOTAS:
                totais[filho.categoria] += filho.duracao_s
            else:
                visitar(filho)

    visitar(etapa)
    return totais


def tokens_descendentes(etapa: Etapa) -> Dict[str, int]:
    totais: Dict[str, int] = defaultdict(int)
    for e in descendentes(etapa, incluir_raiz=True):
        if e.categoria != "api":
            continue
        for chave in ("tokens_entrada", "tokens_cache", "tokens_saida", "tokens_reasoning"):
            valor = e.dados.get(chave)
            if isinstance(valor, (int, float)):
                totais[chave] += int(valor)
    return totais


def _num(valor: Any) -> int:
    return int(valor) if isinstance(valor, (int, float)) else 0


def precos_do_modelo(modelo: Optional[str], precos: Dict[str, Dict[str, float]]) -> Optional[Dict[str, float]]:
    nome = (modelo or "").strip().lower()
    candidatos = [p for p in precos if nome.startswith(p.lower())]
    return precos[max(candidatos, key=len)] if candidatos else None


def custo_chamada(etapa: Etapa, precos: Dict[str, Dict[str, float]]) -> Optional[float]:
    """Custo estimado (US$) de uma chamada de API; None se faltar preço ou uso."""
    if etapa.categoria != "api" or etapa.dados.get("tokens_entrada") is None:
        return None
    tabela_precos = precos_do_modelo(etapa.dados.get("modelo"), precos)
    if not tabela_precos:
        return None
    entrada = _num(etapa.dados.get("tokens_entrada"))
    cache = min(entrada, _num(etapa.dados.get("tokens_cache")))
    saida = _num(etapa.dados.get("tokens_saida")) + _num(etapa.dados.get("tokens_reasoning"))
    sufixo = "_longo" if entrada >= LIMIAR_CONTEXTO_LONGO else ""
    return (
        (entrada - cache) * tabela_precos[f"entrada{sufixo}"]
        + cache * tabela_precos[f"cache{sufixo}"]
        + saida * tabela_precos[f"saida{sufixo}"]
    ) / 1_000_000


def custo_descendentes(etapa: Etapa, precos: Dict[str, Dict[str, float]]) -> tuple[float, int]:
    """Soma do custo estimado e nº de chamadas sem preço conhecido."""
    total, sem_preco = 0.0, 0
    for e in descendentes(etapa, incluir_raiz=True):
        if e.categoria != "api" or e.dados.get("tokens_entrada") is None:
            continue
        custo = custo_chamada(e, precos)
        if custo is None:
            sem_preco += 1
        else:
            total += custo
    return total, sem_preco


def fmt_usd(valor: float, sem_preco: int = 0) -> str:
    texto = f"US$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return texto + (f" (+{sem_preco} sem preço)" if sem_preco else "")


# --------------------------------------------------------------------------- #
# Seções do relatório
# --------------------------------------------------------------------------- #

def secao_fases(fases: List[Etapa], precos: Dict[str, Dict[str, float]]) -> str:
    if not fases:
        return "_Nenhuma fase registrada no período._"
    linhas = []
    for f in fases:
        custo, sem_preco = custo_descendentes(f, precos)
        remotos = tempo_por_categoria(f)
        api = remotos.get("api", 0.0)
        col = remotos.get("collection", 0.0)
        local = max(0.0, f.duracao_s - api - col)
        n_api = sum(1 for e in descendentes(f) if e.categoria == "api")
        tokens = tokens_descendentes(f)
        linhas.append([
            f.nome,
            fmt_hora(f.inicio),
            fmt_hora(f.fim) if f.completa else "**não terminou**",
            fmt_dur(f.duracao_s),
            f.status,
            f"{n_api} ({fmt_dur(api)}, {fmt_pct(api, f.duracao_s)})",
            f"{fmt_dur(col)} ({fmt_pct(col, f.duracao_s)})",
            f"{fmt_dur(local)} ({fmt_pct(local, f.duracao_s)})",
            f"{fmt_int(tokens.get('tokens_entrada'))} ({fmt_int(tokens.get('tokens_cache'))})"
            f" / {fmt_int(tokens.get('tokens_saida'))} / {fmt_int(tokens.get('tokens_reasoning'))}",
            fmt_usd(custo, sem_preco),
        ])
    return tabela(
        ["Fase", "Início", "Término", "Duração", "Status", "Chamadas API (tempo, %)",
         "Collection", "Local/UI", "Tokens entrada (cache) / saída / reasoning",
         "Custo estimado"],
        linhas,
    )


def arvore(etapa: Etapa, total_fase: float, nivel: int = 0) -> List[str]:
    marca = "" if etapa.status == "ok" else f"  [{etapa.status.upper()}]"
    erro = f" — {etapa.erro[:120]}" if etapa.erro else ""
    tokens = ""
    if etapa.categoria == "api" and etapa.dados.get("tokens_saida") is not None:
        tokens = (
            f"  tokens {fmt_int(etapa.dados.get('tokens_entrada'))}→"
            f"{fmt_int(etapa.dados.get('tokens_saida'))}"
        )
        if etapa.dados.get("tokens_reasoning"):
            tokens += f" (reasoning {fmt_int(etapa.dados.get('tokens_reasoning'))})"
    linha = (
        f"{fmt_hora(etapa.inicio)[6:]}  {fmt_dur(etapa.duracao_s):>14}  "
        f"{fmt_pct(etapa.duracao_s, total_fase):>4}  "
        f"{'   ' * (nivel - 1)}{'└─ ' if nivel else ''}[{etapa.categoria}] {rotulo(etapa)}"
        f"{tokens}{marca}{erro}"
    )
    linhas = [linha]
    for filho in etapa.filhos:
        linhas.extend(arvore(filho, total_fase, nivel + 1))
    return linhas


def secao_detalhe_fases(fases: List[Etapa]) -> str:
    blocos = []
    for f in fases:
        blocos.append(
            f"### {f.nome} — {fmt_hora(f.inicio)} ({fmt_dur(f.duracao_s)}, {f.status})\n\n"
            "Colunas: horário de início, duração, % da fase, categoria e etapa.\n\n"
            "```text\n" + "\n".join(arvore(f, f.duracao_s)) + "\n```"
        )
    return "\n\n".join(blocos) if blocos else "_Sem fases para detalhar._"


def secao_estatisticas(etapas: List[Etapa]) -> str:
    grupos: Dict[tuple, List[Etapa]] = defaultdict(list)
    for e in etapas:
        if e.completa:
            grupos[(e.categoria, e.nome)].append(e)
    linhas = []
    for (categoria, nome), itens in sorted(
        grupos.items(), key=lambda kv: -sum(e.duracao_s for e in kv[1])
    ):
        duracoes = [e.duracao_s for e in itens]
        erros = sum(1 for e in itens if e.status != "ok")
        linhas.append([
            categoria, nome, str(len(itens)), fmt_dur(sum(duracoes)),
            fmt_dur(statistics.mean(duracoes)), fmt_dur(statistics.median(duracoes)),
            fmt_dur(percentil(duracoes, 90)), fmt_dur(min(duracoes)), fmt_dur(max(duracoes)),
            str(erros),
        ])
    if not linhas:
        return "_Sem etapas concluídas._"
    return tabela(
        ["Categoria", "Etapa", "Qtde", "Total", "Média", "Mediana", "P90", "Mín", "Máx", "Erros"],
        linhas,
    )


def secao_modelos(etapas: List[Etapa], precos: Dict[str, Dict[str, float]]) -> str:
    grupos: Dict[tuple, List[Etapa]] = defaultdict(list)
    for e in etapas:
        if e.categoria == "api" and e.completa:
            grupos[(e.dados.get("modelo") or "—", e.dados.get("reasoning") or "padrão")].append(e)
    if not grupos:
        return "_Nenhuma chamada de API concluída._"
    linhas = []
    for (modelo, reasoning), itens in sorted(grupos.items()):
        duracoes = [e.duracao_s for e in itens]

        def media(chave: str) -> str:
            valores = [e.dados[chave] for e in itens if isinstance(e.dados.get(chave), (int, float))]
            return fmt_int(statistics.mean(valores)) if valores else "—"

        vazao = [
            e.dados["tokens_saida"] / e.duracao_s
            for e in itens
            if isinstance(e.dados.get("tokens_saida"), (int, float)) and e.duracao_s > 0
        ]
        custos = [custo_chamada(e, precos) for e in itens]
        custos_validos = [c for c in custos if c is not None]
        sem_preco = sum(
            1 for e, c in zip(itens, custos)
            if c is None and e.dados.get("tokens_entrada") is not None
        )
        linhas.append([
            modelo, reasoning, str(len(itens)), fmt_dur(sum(duracoes)),
            fmt_dur(statistics.mean(duracoes)), fmt_dur(max(duracoes)),
            media("tokens_entrada"), media("tokens_cache"), media("tokens_saida"),
            media("tokens_reasoning"),
            f"{statistics.mean(vazao):.1f}" if vazao else "—",
            fmt_usd(sum(custos_validos), sem_preco),
        ])
    return tabela(
        ["Modelo", "Reasoning", "Chamadas", "Total", "Média", "Máx",
         "Tokens entrada (média)", "Tokens cache (média)", "Tokens saída (média)",
         "Tokens reasoning (média)", "Tokens saída/s", "Custo estimado"],
        linhas,
    )


def secao_mais_lentas(etapas: List[Etapa], top: int) -> str:
    remotas = [e for e in etapas if e.categoria in CATEGORIAS_REMOTAS]
    remotas.sort(key=lambda e: -e.duracao_s)
    if not remotas:
        return "_Nenhuma chamada remota registrada._"
    linhas = []
    for e in remotas[:top]:
        timeout = e.dados.get("timeout_s")
        uso_timeout = fmt_pct(e.duracao_s, float(timeout)) if timeout else "—"
        linhas.append([
            fmt_hora(e.inicio), fmt_dur(e.duracao_s), e.categoria, rotulo(e),
            uso_timeout, e.status if e.completa else "incompleta",
        ])
    return tabela(["Início", "Duração", "Categoria", "Etapa", "% do timeout", "Status"], linhas)


def secao_erros(etapas: List[Etapa]) -> str:
    problemas = [e for e in etapas if e.status not in ("ok",)]
    retentativas = [
        e for e in etapas
        if e.categoria == "api" and str(e.dados.get("tentativa", "1/")).split("/")[0] not in ("1", "")
    ]
    partes = []
    if problemas:
        partes.append(tabela(
            ["Início", "Duração", "Categoria", "Etapa", "Status", "Erro"],
            [[fmt_hora(e.inicio), fmt_dur(e.duracao_s), e.categoria, rotulo(e), e.status,
              (e.erro or ("etapa sem evento de término (app fechado ou ainda em execução)"
                          if not e.completa else ""))[:160]]
             for e in problemas],
        ))
    else:
        partes.append("_Nenhum erro ou etapa incompleta._")
    if retentativas:
        partes.append(
            f"\n**Retentativas de API:** {len(retentativas)} "
            f"(tempo gasto: {fmt_dur(sum(e.duracao_s for e in retentativas))})."
        )
    return "\n".join(partes)


def diagnostico(
    fases: List[Etapa], etapas: List[Etapa], precos: Dict[str, Dict[str, float]]
) -> str:
    achados: List[str] = []

    custos_fase = [(f, custo_descendentes(f, precos)[0]) for f in fases]
    custo_total = sum(c for _, c in custos_fase)
    if custo_total > 0:
        cara, custo_cara = max(custos_fase, key=lambda fc: fc[1])
        achados.append(
            f"Custo estimado do período: {fmt_usd(custo_total)}; a fase mais cara foi "
            f"**{cara.nome}** ({fmt_hora(cara.inicio)}) com {fmt_usd(custo_cara)} "
            f"({fmt_pct(custo_cara, custo_total)})."
        )
    apis_uso = [
        e for e in etapas
        if e.categoria == "api" and isinstance(e.dados.get("tokens_entrada"), (int, float))
    ]
    longas = [e for e in apis_uso if e.dados["tokens_entrada"] >= LIMIAR_CONTEXTO_LONGO]
    if longas:
        achados.append(
            f"{len(longas)} chamada(s) com prompt ≥ {fmt_int(LIMIAR_CONTEXTO_LONGO)} tokens — "
            "nessas a xAI cobra a tarifa de contexto longo (o dobro) sobre a chamada inteira."
        )
    entrada_total = sum(_num(e.dados.get("tokens_entrada")) for e in apis_uso)
    cache_total = sum(_num(e.dados.get("tokens_cache")) for e in apis_uso)
    if entrada_total >= 500_000 and cache_total / entrada_total < 0.2:
        achados.append(
            f"Somente {fmt_pct(cache_total, entrada_total)} dos tokens de entrada vieram do "
            "cache; prompts que repetem o mesmo prefixo longo deveriam reaproveitá-lo."
        )

    for f in fases:
        remotos = tempo_por_categoria(f)
        api = remotos.get("api", 0.0)
        if f.duracao_s >= 60 and api / max(f.duracao_s, 1e-9) >= 0.8:
            achados.append(
                f"Fase **{f.nome}** ({fmt_hora(f.inicio)}): {fmt_pct(api, f.duracao_s)} do tempo "
                f"foi espera pela API xAI. O gargalo é o modelo, não o processamento local."
            )
        local = f.duracao_s - api - remotos.get("collection", 0.0)
        if local >= 30 and local / max(f.duracao_s, 1e-9) >= 0.3:
            achados.append(
                f"Fase **{f.nome}** ({fmt_hora(f.inicio)}): {fmt_dur(local)} de processamento "
                "local/UI fora das chamadas remotas — vale investigar o código local."
            )

    apis = [e for e in etapas if e.categoria == "api" and e.completa]
    perto_timeout = [
        e for e in apis
        if e.dados.get("timeout_s") and e.duracao_s >= 0.8 * float(e.dados["timeout_s"])
    ]
    if perto_timeout:
        achados.append(
            f"{len(perto_timeout)} chamada(s) de API usaram ≥ 80% do timeout configurado "
            "(risco de falha por timeout e retentativa)."
        )

    por_reasoning: Dict[str, List[float]] = defaultdict(list)
    for e in apis:
        por_reasoning[str(e.dados.get("reasoning") or "padrão")].append(e.duracao_s)
    if len(por_reasoning) > 1:
        medias = {k: statistics.mean(v) for k, v in por_reasoning.items()}
        resumo = ", ".join(f"{k}: {fmt_dur(v)}" for k, v in sorted(medias.items(), key=lambda kv: kv[1]))
        achados.append(f"Duração média por nível de reasoning — {resumo}.")

    com_reasoning = [
        e for e in apis
        if isinstance(e.dados.get("tokens_reasoning"), (int, float))
        and isinstance(e.dados.get("tokens_saida"), (int, float))
        and e.dados["tokens_saida"] + e.dados["tokens_reasoning"] > 0
    ]
    if com_reasoning:
        proporcao = statistics.mean(
            e.dados["tokens_reasoning"] / (e.dados["tokens_saida"] + e.dados["tokens_reasoning"])
            for e in com_reasoning
        )
        if proporcao >= 0.5:
            achados.append(
                f"Em média {proporcao:.0%} dos tokens gerados são de reasoning (pensamento "
                "interno, cobrado como saída). Reduzir o nível de reasoning tende a encurtar "
                "e baratear bastante essas chamadas."
            )

    topicos = [e for e in etapas if e.nome == "minuta.topico" and e.completa]
    if topicos:
        mais_lento = max(topicos, key=lambda e: e.duracao_s)
        achados.append(
            f"Minuta: {len(topicos)} tópico(s), média de {fmt_dur(statistics.mean(e.duracao_s for e in topicos))} "
            f"por tópico; o mais lento foi '{mais_lento.dados.get('topico', mais_lento.id)}' "
            f"({fmt_dur(mais_lento.duracao_s)}). Os tópicos são gerados em sequência, "
            "então o total cresce linearmente com o número de tópicos."
        )

    incompletas = [e for e in etapas if not e.completa]
    if incompletas:
        achados.append(
            f"{len(incompletas)} etapa(s) sem evento de término — o app foi fechado/travou "
            "durante a etapa ou ela ainda está em execução."
        )

    return "\n".join(f"- {a}" for a in achados) if achados else "_Nenhum achado relevante._"


# --------------------------------------------------------------------------- #
# Montagem
# --------------------------------------------------------------------------- #

def carregar_precos(caminho: Optional[str]) -> Dict[str, Dict[str, float]]:
    """Tabela padrão, sobrescrita/estendida por um JSON {"modelo": {"entrada": ..., ...}}."""
    precos = {k: dict(v) for k, v in PRECOS_PADRAO.items()}
    if caminho:
        extras = json.loads(Path(caminho).read_text(encoding="utf-8"))
        for modelo, valores in extras.items():
            base = precos.get(modelo, {})
            base.update({k: float(v) for k, v in valores.items()})
            for chave in ("entrada", "cache", "saida"):
                base.setdefault(f"{chave}_longo", base[chave])
            precos[modelo] = base
    return precos


def gerar_relatorio(
    etapas: List[Etapa],
    arquivos: List[Path],
    invalidas: int,
    top: int,
    precos: Optional[Dict[str, Dict[str, float]]] = None,
) -> str:
    precos = precos or PRECOS_PADRAO
    fases = [e for e in etapas if e.categoria == "fase"]
    sessoes = sorted({e.sessao for e in etapas})
    inicio = min((e.inicio for e in etapas), default=None)
    fim = max((e.fim or e.inicio for e in etapas), default=None)

    cabecalho = [
        "# Auditoria de execução — AppSarah",
        "",
        f"- Gerado em: {datetime.now():%d/%m/%Y %H:%M:%S}",
        f"- Arquivos: {', '.join(a.name for a in arquivos) or '—'}",
        f"- Período: {fmt_hora(inicio)} → {fmt_hora(fim)}",
        f"- Sessões do app: {len(sessoes)} | Fases: {len(fases)} | Etapas: {len(etapas)}",
    ]
    if invalidas:
        cabecalho.append(f"- Linhas inválidas ignoradas: {invalidas}")

    secoes = [
        "\n".join(cabecalho),
        "## Diagnóstico\n\n" + diagnostico(fases, etapas, precos),
        "## Resumo por fase\n\n"
        "\"Local/UI\" é o tempo da fase fora das chamadas remotas "
        "(preparo de prompts, validação, atualização da interface). O custo é uma "
        "estimativa a partir dos tokens registrados e da tabela de preços "
        f"({', '.join(sorted(precos))}); confira sempre com o painel de faturamento da xAI.\n\n"
        + secao_fases(fases, precos),
        "## Detalhamento das fases\n\n" + secao_detalhe_fases(fases),
        "## Estatísticas por etapa\n\n" + secao_estatisticas(etapas),
        "## Chamadas de API por modelo e reasoning\n\n" + secao_modelos(etapas, precos),
        f"## {top} chamadas remotas mais lentas\n\n" + secao_mais_lentas(etapas, top),
        "## Erros, etapas incompletas e retentativas\n\n" + secao_erros(etapas),
    ]
    return "\n\n".join(secoes) + "\n"


def exportar_csv(etapas: List[Etapa], destino: Path) -> None:
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f, delimiter=";")
        escritor.writerow([
            "sessao", "id", "pai", "categoria", "nome", "inicio", "fim",
            "duracao_s", "status", "erro", "dados",
        ])
        for e in etapas:
            escritor.writerow([
                e.sessao, e.id, e.pai or "", e.categoria, e.nome,
                e.inicio.isoformat(), e.fim.isoformat() if e.fim else "",
                f"{e.duracao_s:.6f}".replace(".", ","), e.status, e.erro or "",
                json.dumps(e.dados, ensure_ascii=False, default=str),
            ])


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Relatório de duração das fases do AppSarah.")
    parser.add_argument("caminhos", nargs="*", help="Arquivos .jsonl ou pastas (padrão: logs/)")
    parser.add_argument("--data", help="Dia no formato AAAAMMDD (filtra arquivos da pasta)")
    parser.add_argument("--sessao", help="Id da sessão do app a auditar")
    parser.add_argument("--ultima", action="store_true", help="Somente a sessão mais recente")
    parser.add_argument("--fase", choices=["cartao", "dossie", "estrutura", "minuta"],
                        help="Somente esta fase (e suas etapas)")
    parser.add_argument("--top", type=int, default=15, help="Qtde de chamadas mais lentas")
    parser.add_argument("--saida", help="Grava o relatório Markdown neste arquivo")
    parser.add_argument("--csv", help="Exporta todas as etapas para CSV (separador ';')")
    parser.add_argument(
        "--precos",
        help='JSON com preços por 1M tokens, ex.: {"grok-4.7": {"entrada": 2, "cache": 0.5, '
             '"saida": 6, "entrada_longo": 4, "cache_longo": 1, "saida_longo": 12}}',
    )
    args = parser.parse_args(argv)
    precos = carregar_precos(args.precos)

    arquivos = localizar_arquivos(args.caminhos, args.data)
    if not arquivos:
        print("Nenhum arquivo de log encontrado (esperado: logs/execucao_*.jsonl).", file=sys.stderr)
        return 1

    eventos, invalidas = ler_eventos(arquivos)
    etapas = filtrar(montar_etapas(eventos), args.sessao, args.ultima, args.fase)
    if not etapas:
        print("Nenhuma etapa corresponde aos filtros.", file=sys.stderr)
        return 1

    relatorio = gerar_relatorio(etapas, arquivos, invalidas, args.top, precos)
    if args.saida:
        Path(args.saida).write_text(relatorio, encoding="utf-8")
        print(f"Relatório gravado em {args.saida}")
    else:
        sys.stdout.reconfigure(encoding="utf-8")
        print(relatorio)

    if args.csv:
        exportar_csv(etapas, Path(args.csv))
        print(f"CSV gravado em {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
