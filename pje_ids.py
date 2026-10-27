"""
Extração determinística de IDs do PJe.

O ID é uma string alfanumérica de 7 caracteres. Nos autos, ele aparece só na
última página de cada peça, como os 7 caracteres finais da linha de assinatura:

- "Documento assinado eletronicamente por NOME, em DD/MM/AAAA, às HH:MM:SS - c7dbfbc"
- "ID c7dbfbc", "ID. c7dbfbc", "(ID b9283dd)"

Todo o texto desde o fim da peça anterior até essa linha pertence ao mesmo ID.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Set

# Na assinatura, o ID é o token final da linha: 7 caracteres alfanuméricos,
# mesmo quando o OCR troca um dígito por letra (ex.: bfaaldf).
_ID_ASSINATURA = r"[0-9A-Za-z]{7}"
# Em citação ("ID xxxxxxx"), exige dígito para não capturar palavra comum.
_ID_TOKEN = r"(?=[0-9A-Za-z]*\d)[0-9A-Za-z]{7}"

# O hífen antes do ID é o formato do PJe; o espaço cobre OCR que omite o hífen.
# O ID tem de ser o token final da linha — não um trecho no meio do nome.
RE_ASSINATURA = re.compile(
    r"Documento\s+assinado\s+eletronicamente[^\n]*?(?:-\s*|\s+)("
    + _ID_ASSINATURA
    + r")\s*$",
    re.IGNORECASE | re.MULTILINE,
)
RE_ID_EXPLICITO = re.compile(
    r"\bID[.\s:]+(" + _ID_TOKEN + r")\b",
    re.IGNORECASE,
)
RE_ID_PARENTESES = re.compile(
    r"\(\s*ID\s+(" + _ID_TOKEN + r")\b",
    re.IGNORECASE,
)
# Aceita também IDs numéricos longos legados (8+ dígitos) em citações "(ID 12345678".
RE_ID_NUMERICO = re.compile(
    r"\(\s*ID\s+(\d{6,})\b",
    re.IGNORECASE,
)

INSTRUCAO_IDS_PJE = (
    "ID do PJe: string alfanumérica de 7 caracteres (ex.: c7dbfbc, 4ac9a65, bfaa1df). "
    "Aparece somente na última página de cada peça, como os 7 caracteres finais da linha "
    "'Documento assinado eletronicamente por ..., em DD/MM/AAAA, às HH:MM:SS - XXXXXXX'. "
    "Todo o texto desde a assinatura da peça anterior até essa linha pertence a esse ID. "
    "Também pode aparecer como 'ID XXXXXXX', 'ID. XXXXXXX' ou '(ID XXXXXXX)'. "
    "Nunca invente ID; se não encontrar, use null (não escreva 'não informado')."
)


@dataclass(frozen=True)
class PecaPJe:
    """Trecho contínuo de uma peça, fechado pela assinatura da última página."""

    texto: str
    id_pje: Optional[str]
    inicio: int
    fim: int


def dividir_em_pecas(texto: str) -> List[PecaPJe]:
    """
    Divide os autos em peças.

    Cada peça vai até a linha de assinatura eletrônica (inclusive). O ID dessa
    linha identifica a peça inteira, inclusive as páginas anteriores, em que o
    ID não se repete.
    """
    if not texto:
        return []

    pecas: List[PecaPJe] = []
    inicio = 0
    for match in RE_ASSINATURA.finditer(texto):
        fim = match.end()
        if fim < len(texto) and texto[fim] == "\n":
            fim += 1
        if fim <= inicio:
            continue
        pecas.append(
            PecaPJe(
                texto=texto[inicio:fim],
                id_pje=normalizar_id_pje(match.group(1)),
                inicio=inicio,
                fim=fim,
            )
        )
        inicio = fim

    resto = texto[inicio:]
    if resto.strip() or not pecas:
        pecas.append(PecaPJe(texto=resto, id_pje=None, inicio=inicio, fim=len(texto)))
    return pecas


def _rodape_id(texto: str, id_pje: Optional[str]) -> str:
    """Repete a linha de assinatura quando a peça precisa ser fatiada."""
    if not id_pje:
        return ""
    match = RE_ASSINATURA.search(texto)
    linha = ""
    if match:
        inicio_linha = texto.rfind("\n", 0, match.start()) + 1
        linha = texto[inicio_linha:match.end()].strip()
    return (
        f"\n\n[Mesma peça, ID {id_pje}, presente só na última página, "
        f"nos 7 caracteres finais da assinatura: {linha}]\n"
    )


def fatiar_preservando_id(
    texto: str,
    max_chars: int,
    id_pje: Optional[str] = None,
) -> List[str]:
    """
    Fraciona um único texto longo sem descartar caracteres.

    Os cortes preferem o início de uma página. Cada fatia que não é a última
    repete o ID da peça, porque ele só existe na página final.
    """
    if max_chars <= 0:
        raise ValueError("max_chars deve ser positivo")
    if len(texto) <= max_chars:
        return [texto] if texto else []

    rodape = _rodape_id(texto, id_pje)
    orcamento = max_chars - len(rodape)
    if orcamento < 1_000:
        orcamento = max_chars
        rodape = ""

    fatias: List[str] = []
    inicio = 0
    while inicio < len(texto):
        fim = min(inicio + orcamento, len(texto))
        if fim < len(texto):
            corte = texto.rfind("\n## Página ", inicio + 1, fim)
            if corte <= inicio:
                corte = texto.rfind("\n", inicio + 1, fim)
            if corte > inicio:
                fim = corte + 1
        bloco = texto[inicio:fim]
        if fim < len(texto) and rodape:
            bloco += rodape
        fatias.append(bloco)
        inicio = fim
    return fatias


def agrupar_pecas_em_lotes(pecas: Sequence[PecaPJe], max_chars: int) -> List[str]:
    """
    Empacota peças inteiras em lotes de até max_chars.

    Nenhuma peça é omitida. Uma peça maior que o lote é fatiada por páginas,
    com o ID da última página repetido em cada fatia.
    """
    if max_chars <= 0:
        raise ValueError("max_chars deve ser positivo")

    lotes: List[str] = []
    buffer: List[str] = []
    tamanho = 0

    def fechar() -> None:
        nonlocal buffer, tamanho
        if buffer:
            lotes.append("".join(buffer))
            buffer = []
            tamanho = 0

    for peca in pecas:
        blocos = fatiar_preservando_id(peca.texto, max_chars, peca.id_pje)
        for bloco in blocos:
            if not bloco:
                continue
            if tamanho and tamanho + len(bloco) > max_chars:
                fechar()
            if not buffer and len(bloco) > max_chars:
                lotes.append(bloco)
                continue
            buffer.append(bloco)
            tamanho += len(bloco)
    fechar()
    return lotes


def _id_da_peca_na_posicao(pecas: Sequence[PecaPJe], pos: int) -> Optional[str]:
    """ID da peça que contém a posição. O ID fica na última página da peça."""
    for peca in pecas:
        if peca.inicio <= pos < peca.fim and peca.id_pje:
            return peca.id_pje
    return None


def normalizar_id_pje(valor: Optional[str]) -> Optional[str]:
    """Normaliza ID removendo prefixo 'ID' e espaços; retorna None se vazio."""
    if not valor:
        return None
    texto = str(valor).strip()
    texto = re.sub(r"^ID[.\s:]+", "", texto, flags=re.IGNORECASE).strip()
    if not texto or texto.lower() in {"null", "none", "não informado", "nao informado"}:
        return None
    return texto


def extrair_ids_pje_do_texto(texto: str) -> List[str]:
    """Extrai IDs únicos preservando a ordem de aparição."""
    if not texto:
        return []
    vistos: Set[str] = set()
    ordenados: List[str] = []
    for padrao in (RE_ASSINATURA, RE_ID_EXPLICITO, RE_ID_PARENTESES, RE_ID_NUMERICO):
        for match in padrao.finditer(texto):
            id_norm = normalizar_id_pje(match.group(1))
            if id_norm and id_norm.lower() not in vistos:
                vistos.add(id_norm.lower())
                ordenados.append(id_norm)
    return ordenados


def inferir_id_proximo_ao_trecho(
    texto_completo: str,
    trecho: str,
    janela: int = 1200,
    pecas: Optional[Sequence[PecaPJe]] = None,
) -> Optional[str]:
    """
    Atribui o ID da peça que contém o trecho.

    A assinatura fica só na última página, muitas vezes milhares de caracteres
    depois do trecho. A peça inteira, e não uma janela curta, é a unidade do ID.
    """
    if not texto_completo or not trecho:
        return None

    trecho_limpo = trecho.strip()
    if len(trecho_limpo) < 20:
        ancora = trecho_limpo
    else:
        ancora = trecho_limpo[:80]

    pos = texto_completo.find(ancora)
    if pos < 0:
        pos = texto_completo.casefold().find(ancora.casefold())

    if pos >= 0:
        pecas_resolvidas = list(pecas) if pecas is not None else dividir_em_pecas(texto_completo)
        id_peca = _id_da_peca_na_posicao(pecas_resolvidas, pos)
        if id_peca:
            return id_peca

        inicio = max(0, pos - 200)
        fim = min(len(texto_completo), pos + len(ancora) + janela)
        vizinhanca = texto_completo[inicio:fim]
        depois = texto_completo[pos:fim]
        match = RE_ASSINATURA.search(depois)
        if match:
            return normalizar_id_pje(match.group(1))
        ids = extrair_ids_pje_do_texto(vizinhanca)
        if ids:
            return ids[-1]

    ids_no_trecho = extrair_ids_pje_do_texto(trecho)
    return ids_no_trecho[0] if ids_no_trecho else None


def enriquecer_id_em_objetos(
    objetos: Iterable[object],
    texto_fonte: str,
    attr_trecho: str = "trecho",
    attr_id: str = "id_pje",
) -> int:
    """
    Preenche id_pje ausente em objetos com atributo trecho.
    Retorna quantidade de IDs preenchidos.
    """
    pecas = dividir_em_pecas(texto_fonte)
    preenchidos = 0
    for obj in objetos:
        atual = normalizar_id_pje(getattr(obj, attr_id, None))
        if atual:
            if getattr(obj, attr_id, None) != atual:
                setattr(obj, attr_id, atual)
            continue
        trecho = getattr(obj, attr_trecho, None) or ""
        inferido = inferir_id_proximo_ao_trecho(texto_fonte, trecho, pecas=pecas)
        if inferido:
            setattr(obj, attr_id, inferido)
            preenchidos += 1
    return preenchidos


def enriquecer_fontes_dict(
    fontes: List[dict],
    texto_fonte: str,
    pecas: Optional[Sequence[PecaPJe]] = None,
) -> int:
    """Preenche id_pje em listas de fontes no formato dict (cartão)."""
    pecas_resolvidas = list(pecas) if pecas is not None else dividir_em_pecas(texto_fonte)
    preenchidos = 0
    for fonte in fontes or []:
        if not isinstance(fonte, dict):
            continue
        atual = normalizar_id_pje(fonte.get("id_pje"))
        if atual:
            fonte["id_pje"] = atual
            continue
        trecho = fonte.get("trecho") or ""
        inferido = inferir_id_proximo_ao_trecho(
            texto_fonte, trecho, pecas=pecas_resolvidas
        )
        if inferido:
            fonte["id_pje"] = inferido
            preenchidos += 1
    return preenchidos
