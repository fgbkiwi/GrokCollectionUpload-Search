"""
Testes do log de execução e do script de auditoria.
"""

import json

import pytest

import auditoria_execucao as auditoria
import log_execucao
from log_execucao import API, COLLECTION, FASE, etapa


def _eventos_do_log():
    linhas = log_execucao._arquivo_jsonl.read_text(encoding="utf-8").splitlines()
    return [json.loads(linha) for linha in linhas]


def test_etapas_aninhadas_registram_inicio_fim_e_pai():
    with etapa("fase_teste_aninhada", categoria=FASE) as fase:
        with etapa("chamada_teste", categoria=API, modelo="grok-x") as api:
            api.registrar_uso({
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 50,
                    "completion_tokens_details": {"reasoning_tokens": 30},
                }
            })

    eventos = [e for e in _eventos_do_log() if e["id"] in (fase.id, api.id)]
    assert [e["evento"] for e in eventos] == ["inicio", "inicio", "fim", "fim"]

    fim_api = next(e for e in eventos if e["id"] == api.id and e["evento"] == "fim")
    assert fim_api["pai"] == fase.id
    assert fim_api["status"] == "ok"
    assert fim_api["duracao_s"] >= 0
    assert fim_api["dados"]["tokens_reasoning"] == 30
    assert fim_api["dados"]["modelo"] == "grok-x"


def test_etapa_registra_excecao_como_erro():
    with pytest.raises(ValueError):
        with etapa("etapa_que_falha") as reg:
            raise ValueError("falhou")

    fim = next(
        e for e in _eventos_do_log() if e["id"] == reg.id and e["evento"] == "fim"
    )
    assert fim["status"] == "erro"
    assert "ValueError: falhou" in fim["erro"]


def _evento(evento, id_, nome, categoria, ts, pai=None, duracao=None, dados=None, inicio=None):
    ev = {
        "ts": ts, "evento": evento, "sessao": "S1", "id": id_, "pai": pai,
        "categoria": categoria, "nome": nome, "dados": dados or {},
    }
    if evento == "fim":
        ev.update({"duracao_s": duracao, "status": "ok", "erro": None, "inicio": inicio})
    return ev


def test_auditoria_gera_relatorio_com_tempo_api_e_etapa_incompleta(tmp_path):
    t = "2026-10-12T11:{:02d}:00.000000-03:00"
    eventos = [
        _evento("inicio", "F1", "minuta", FASE, t.format(0)),
        _evento("inicio", "T1", "minuta.topico", "tarefa", t.format(0), pai="F1",
                dados={"topico": "Relatório"}),
        _evento("inicio", "A1", "minuta.previa.chat_completions", API, t.format(0), pai="T1",
                dados={"modelo": "grok-4.6", "reasoning": "high", "timeout_s": 480}),
        _evento("fim", "A1", "minuta.previa.chat_completions", API, t.format(4), pai="T1",
                duracao=240.0, inicio=t.format(0),
                dados={"tokens_saida": 200, "tokens_reasoning": 800}),
        _evento("inicio", "C1", "collection.busca", COLLECTION, t.format(4), pai="T1"),
        _evento("fim", "C1", "collection.busca", COLLECTION, t.format(5), pai="T1",
                duracao=60.0, inicio=t.format(4)),
        _evento("fim", "T1", "minuta.topico", "tarefa", t.format(5), pai="F1",
                duracao=300.0, inicio=t.format(0)),
        _evento("inicio", "T2", "minuta.topico", "tarefa", t.format(5), pai="F1"),
    ]
    arquivo = tmp_path / "execucao_20261012.jsonl"
    arquivo.write_text("\n".join(json.dumps(e) for e in eventos), encoding="utf-8")

    eventos_lidos, invalidas = auditoria.ler_eventos([arquivo])
    etapas = auditoria.filtrar(auditoria.montar_etapas(eventos_lidos), None, False, None)
    fase = next(e for e in etapas if e.id == "F1")

    assert invalidas == 0
    assert not fase.completa
    assert fase.duracao_s == pytest.approx(300.0)
    assert auditoria.tempo_por_categoria(fase) == {"api": 240.0, "collection": 60.0}

    relatorio = auditoria.gerar_relatorio(etapas, [arquivo], invalidas, top=5)
    assert "não terminou" in relatorio
    assert "minuta.previa.chat_completions" in relatorio
    assert "80% dos tokens gerados são de reasoning" in relatorio

    saida = tmp_path / "rel.md"
    csv_saida = tmp_path / "etapas.csv"
    codigo = auditoria.main([str(tmp_path), "--saida", str(saida), "--csv", str(csv_saida)])
    assert codigo == 0
    assert saida.exists() and csv_saida.exists()


def test_percentil_nearest_rank():
    assert auditoria.percentil([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], 90) == 9
    assert auditoria.percentil([5.0], 90) == 5.0
