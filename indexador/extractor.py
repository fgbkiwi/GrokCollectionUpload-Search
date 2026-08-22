#!/usr/bin/env python3
"""
extractor.py
Módulo para extração de sentenças trabalhistas de arquivos docx/odt.

Funcionalidades:
- Extração de texto de docx e odt (XML interno)
- Detecção de fundamentação e quebra por tópicos
- Extração de metadados (processo, data, reclamada, tipo de ação)
- Detecção de pessoa física vs jurídica
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib


# Namespaces XML
WORD_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
ODT_NS = {
    'text': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0',
    'style': 'urn:oasis:names:tc:opendocument:xmlns:style:1.0',
    'fo': 'urn:oasis:names:tc:opendocument:xmlns:xsl-fo-compatible:1.0'
}

# Padrão número CNJ
CNJ_PATTERN = re.compile(r'\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}')

# Padrão número de processo no texto (mais flexível)
PROCESSO_PATTERN = re.compile(r'(\d{1,7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4})')

# Padrão data de publicação
DATA_PATTERN = re.compile(
    r'Aos?\s+(\d{1,2})\s+dias?\s+do\s+m[eê]s\s+de\s+(\w+)\s+de\s+(\d{4})',
    re.IGNORECASE
)

MESES = {
    'janeiro': 1, 'fevereiro': 2, 'março': 3, 'abril': 4,
    'maio': 5, 'junho': 6, 'julho': 7, 'agosto': 8,
    'setembro': 9, 'outubro': 10, 'novembro': 11, 'dezembro': 12
}

# Tipos de ação por sigla no nome do arquivo
TIPOS_ACAO = {
    'acp': 'Ação Civil Pública',
    'aco': 'Ação Cautelar',
    'cp': 'Cumprimento de Sentença',
    'ed': 'Embargos de Declaração',
    'lim': 'Liminar',
    'tp': 'Tutela Provisória',
    'tu': 'Tutela de Urgência',
    'at': 'Ação Trabalhista',
    'ms': 'Mandado de Segurança',
}

# Tokens que indicam pessoa jurídica
PJ_TOKENS = [
    'ltda', 's.a', 's/a', 'eireli', 'me', 'epp', 'spe', 's.s.',
    'associação', 'associacao', 'município', 'municipio',
    'união', 'uniao', 'estado', 'hospital', 'igreja',
    'cooperativa', 'fundação', 'fundacao', 'instituto',
    'companhia', 'indústria', 'industria', 'comércio', 'comercio',
    'serviços', 'servicos', 'banco', 'condomínio', 'condominio',
    'sociedade', 'empresa', 'organização', 'organizacao',
    'sindicato', 'federação', 'federacao', 'conselho',
    'autarquia', 'fazenda', 'prefeitura', 'defensoria',
    'ministério', 'ministerio', 'secretaria', 'departamento',
    'agência', 'agencia', 'caixa', 'correios', 'petrobrás', 'petrobras'
]


class ExtratorSentenca:
    """Extrator de sentenças trabalhistas de docx/odt."""
    
    def __init__(self):
        self.stats = {
            'processados': 0,
            'ignorados': 0,
            'erros': 0,
            'topicos_extraidos': 0
        }
    
    def deve_ignorar_arquivo(self, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Verifica se o arquivo deve ser ignorado.
        
        Returns:
            (deve_ignorar, motivo)
        """
        filename_lower = filename.lower()
        
        # Ignora despachos
        if 'dsp' in filename_lower:
            return True, "Despacho (contém 'dsp')"
        
        # Valida número CNJ no nome
        if not CNJ_PATTERN.search(filename):
            return True, "Nome não começa com número CNJ"
        
        return False, None
    
    def extrair_tipo_acao(self, filename: str) -> str:
        """Extrai tipo de ação pela sigla no nome do arquivo."""
        filename_lower = filename.lower()
        
        # Procura siglas entre pontos: .acp., .ms., etc
        for sigla, nome in TIPOS_ACAO.items():
            if f'.{sigla}.' in filename_lower or f'_{sigla}_' in filename_lower:
                return nome
        
        return "Reclamação Trabalhista"
    
    def extrair_texto_docx(self, filepath: Path) -> List[Tuple[str, bool]]:
        """
        Extrai texto de arquivo docx.
        
        Returns:
            Lista de (texto_paragrafo, is_formatted)
        """
        paragrafos = []
        
        try:
            with zipfile.ZipFile(filepath, 'r') as docx:
                xml_content = docx.read('word/document.xml')
                root = ET.fromstring(xml_content)
                
                for para in root.findall('.//w:p', WORD_NS):
                    texto_parts = []
                    is_formatted = False
                    
                    # Verifica formatação (itálico, indentação)
                    ppr = para.find('.//w:pPr', WORD_NS)
                    if ppr is not None:
                        # Itálico
                        if ppr.find('.//w:i', WORD_NS) is not None:
                            is_formatted = True
                        # Indentação
                        ind = ppr.find('.//w:ind', WORD_NS)
                        if ind is not None:
                            left = ind.get('{%s}left' % WORD_NS['w'])
                            if left and int(left) > 720:  # ~0.5 inch
                                is_formatted = True
                    
                    # Extrai texto
                    for t in para.findall('.//w:t', WORD_NS):
                        if t.text:
                            texto_parts.append(t.text)
                    
                    texto = ''.join(texto_parts).strip()
                    if texto:
                        paragrafos.append((texto, is_formatted))
        
        except Exception as e:
            raise Exception(f"Erro ao ler docx: {e}")
        
        return paragrafos
    
    def extrair_texto_odt(self, filepath: Path) -> List[Tuple[str, bool]]:
        """
        Extrai texto de arquivo odt.
        
        Returns:
            Lista de (texto_paragrafo, is_formatted)
        """
        paragrafos = []
        
        try:
            with zipfile.ZipFile(filepath, 'r') as odt:
                xml_content = odt.read('content.xml')
                root = ET.fromstring(xml_content)
                
                for para in root.findall('.//text:p', ODT_NS):
                    texto_parts = []
                    is_formatted = False
                    
                    # Verifica estilo (itálico, indentação)
                    style_name = para.get('{%s}style-name' % ODT_NS['text'])
                    if style_name and ('italic' in style_name.lower() or 
                                       'indent' in style_name.lower()):
                        is_formatted = True
                    
                    # Extrai texto
                    texto = ''.join(para.itertext()).strip()
                    if texto:
                        paragrafos.append((texto, is_formatted))
        
        except Exception as e:
            raise Exception(f"Erro ao ler odt: {e}")
        
        return paragrafos
    
    def extrair_numero_processo(self, texto: str, filename: str) -> Optional[str]:
        """Extrai número do processo do texto ou nome do arquivo."""
        # Tenta no texto primeiro
        match = PROCESSO_PATTERN.search(texto)
        if match:
            return match.group(1)
        
        # Fallback: nome do arquivo
        match = CNJ_PATTERN.search(filename)
        if match:
            return match.group(0)
        
        return None
    
    def extrair_data_publicacao(self, texto: str, filepath: Path) -> Optional[str]:
        """
        Extrai data de publicação do texto ou metadados do arquivo.
        
        Returns:
            Data em formato YYYY-MM-DD ou None
        """
        # Tenta extrair do texto
        match = DATA_PATTERN.search(texto[:3000])  # Busca no início
        if match:
            dia = int(match.group(1))
            mes_nome = match.group(2).lower()
            ano = int(match.group(3))
            
            mes = MESES.get(mes_nome)
            if mes:
                return f"{ano:04d}-{mes:02d}-{dia:02d}"
        
        # Fallback: data de criação do arquivo (docx)
        if filepath.suffix == '.docx':
            try:
                with zipfile.ZipFile(filepath, 'r') as docx:
                    core_xml = docx.read('docProps/core.xml')
                    root = ET.fromstring(core_xml)
                    
                    # Procura dcterms:created
                    for elem in root.iter():
                        if 'created' in elem.tag:
                            data_str = elem.text
                            if data_str:
                                # Parseia ISO format
                                dt = datetime.fromisoformat(data_str.replace('Z', '+00:00'))
                                return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
        
        return None
    
    def eh_titulo_topico(self, linha: str) -> bool:
        """Verifica se a linha é um título de tópico."""
        linha = linha.strip()
        
        if not linha:
            return False
        
        # Padrão 1: "1. TÍTULO EM MAIÚSCULAS"
        if re.match(r'^\d+\.\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s.\-—]+$', linha):
            return True
        
        # Padrão 2: "1.1 TÍTULO EM MAIÚSCULAS"
        if re.match(r'^\d+(\.\d+)+\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s.\-—]+$', linha):
            return True
        
        # Padrão 3: "A) TÍTULO EM MAIÚSCULAS" ou "A. TÍTULO"
        if re.match(r'^[A-Z]\.?\d*\)\s+[A-ZÁÀÂÃÉÈÊÍÏÓÔÕÖÚÇÑ\s.\-—]+$', linha):
            return True
        
        # Padrão 4: linha inteira maiúscula (com regras de exclusão)
        if len(linha) > 3 and linha.isupper():
            # Exclui linhas que são só dígitos
            if re.match(r'^\d+$', linha):
                return False
            
            # Exclui linhas com pontuação típica de tabela
            if re.search(r'[!?:;]', linha):
                return False
            
            # Exclui artigos definidos no início
            if re.match(r'^(DOS|DAS|DE|DA|DO|AOS|ÀS|NOS|NAS)\s', linha):
                return False
            
            # Exclui linhas com formato de tabela (valores, datas)
            if re.search(r'\d{1,3}\.\d{3},\d{2}', linha):  # 1.234,56
                return False
            if re.search(r'(JAN|FEV|MAR|ABR|MAI|JUN|JUL|AGO|SET|OUT|NOV|DEZ)/\d{2}', linha):
                return False
            if re.search(r'\b(TOTAL|VALOR|SALDO)\b.*\d', linha):
                return False
            
            # Exclui marcação de formatação
            if linha.startswith('[FORMATTED:'):
                return False
            
            return True
        
        # Padrão 5: bullets "a) texto", "1) texto"
        if re.match(r'^[\da-zA-Z]+\)\s+', linha):
            return True
        
        return False
    
    def extrair_fundamentacao(self, paragrafos: List[Tuple[str, bool]]) -> Tuple[Optional[str], Optional[int]]:
        """
        Extrai texto da fundamentação entre marcadores.
        
        Returns:
            (texto_fundamentacao, indice_inicio) ou (None, None)
        """
        texto_completo = []
        indices = []
        
        for idx, (texto, is_formatted) in enumerate(paragrafos):
            # Marca parágrafos formatados
            if is_formatted:
                texto_completo.append(f"[FORMATTED: {texto}]")
            else:
                texto_completo.append(texto)
            indices.append(idx)
        
        texto_full = '\n'.join(texto_completo)
        
        # Procura início da fundamentação
        inicio_match = re.search(
            r'\b(FUNDAMENTOS|FUNDAMENTAÇÃO|FUNDAMENTACAO)\b',
            texto_full,
            re.IGNORECASE
        )
        
        if not inicio_match:
            return None, None
        
        inicio = inicio_match.end()
        
        # Procura fim da fundamentação
        fim_match = re.search(
            r'\b(DISPOSITIVO|CONCLUSÃO|CONCLUSAO|Por tais fundamentos,)\b',
            texto_full[inicio:],
            re.IGNORECASE
        )
        
        if fim_match:
            fim = inicio + fim_match.start()
        else:
            fim = len(texto_full)
        
        fundamentacao = texto_full[inicio:fim].strip()
        
        # Encontra índice do parágrafo de início
        char_count = 0
        idx_inicio = 0
        for idx, linha in enumerate(texto_completo):
            if char_count >= inicio_match.start():
                idx_inicio = idx
                break
            char_count += len(linha) + 1  # +1 para newline
        
        return fundamentacao, idx_inicio
    
    def quebrar_em_topicos(self, fundamentacao: str) -> List[Tuple[str, str]]:
        """
        Quebra fundamentação em tópicos.
        
        Returns:
            Lista de (categoria, conteudo)
        """
        linhas = fundamentacao.split('\n')
        topicos = []
        categoria_atual = None
        conteudo_atual = []
        
        for linha in linhas:
            linha = linha.strip()
            
            if not linha:
                continue
            
            # Ignora linhas formatadas para detecção de títulos
            if linha.startswith('[FORMATTED:'):
                if categoria_atual:
                    conteudo_atual.append(linha)
                continue
            
            # Verifica se é título
            if self.eh_titulo_topico(linha):
                # Salva tópico anterior
                if categoria_atual and conteudo_atual:
                    topicos.append((categoria_atual, '\n'.join(conteudo_atual)))
                
                # Inicia novo tópico
                categoria_atual = linha
                conteudo_atual = []
            else:
                # Adiciona ao conteúdo do tópico atual
                if categoria_atual:
                    conteudo_atual.append(linha)
        
        # Salva último tópico
        if categoria_atual and conteudo_atual:
            topicos.append((categoria_atual, '\n'.join(conteudo_atual)))
        
        # Se não encontrou nenhum tópico, retorna tudo como "FUNDAMENTOS"
        if not topicos:
            topicos.append(("FUNDAMENTOS", fundamentacao))
        
        return topicos
    
    def detectar_eh_pessoa_juridica(self, nome: str) -> bool:
        """Detecta se o nome é de pessoa jurídica."""
        nome_lower = nome.lower()
        
        for token in PJ_TOKENS:
            if token in nome_lower:
                return True
        
        return False
    
    def extrair_parte(self, texto: str, padroes: List[str]) -> Optional[str]:
        """Extrai nome de parte usando lista de padrões."""
        for padrao in padroes:
            match = re.search(
                rf'{padrao}[\s:]+([^\n]+)',
                texto,
                re.IGNORECASE
            )
            if match:
                nome = match.group(1).strip()
                # Remove pontuação final
                nome = re.sub(r'[,;.:]$', '', nome)
                return nome
        
        return None
    
    def extrair_partes(self, texto: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Extrai reclamante e reclamada do texto.
        
        Returns:
            (reclamante, reclamada)
        """
        # Padrões para reclamante
        padroes_reclamante = [
            r'RECLAMANTE',
            r'AUTOR',
            r'AUTORA',
            r'REQUERENTE',
            r'IMPETRANTE',
            r'EMBARGANTE',
            r'EXEQUENTE',
        ]
        
        # Padrões para reclamada
        padroes_reclamada = [
            r'RECLAMADA',
            r'RECLAMADO',
            r'RÉU',
            r'RÉ',
            r'CONSIGNADO',
            r'CONSIGNADA',
            r'EMBARGADO',
            r'EMBARGADA',
            r'REQUERIDO',
            r'REQUERIDA',
            r'EXCEPTO',
            r'EXCEPTA',
            r'SUSCITADO',
            r'SUSCITADA',
            r'AUTORIDADE COATORA',
            r'EXECUTADO',
            r'EXECUTADA',
        ]
        
        reclamante = self.extrair_parte(texto[:5000], padroes_reclamante)
        reclamada = self.extrair_parte(texto[:5000], padroes_reclamada)
        
        return reclamante, reclamada
    
    def determinar_reclamada_para_metadados(
        self, 
        reclamante: Optional[str], 
        reclamada: Optional[str]
    ) -> str:
        """
        Determina se deve gravar o nome da reclamada nos metadados.
        Regra: só grava se pelo menos uma das partes for PJ.
        
        Returns:
            Nome da reclamada ou string vazia
        """
        if not reclamada:
            return ""
        
        # Se não temos reclamante, assume que pode ser PF e não grava
        if not reclamante:
            # Mas se a reclamada for claramente PJ, grava
            if self.detectar_eh_pessoa_juridica(reclamada):
                return reclamada
            return ""
        
        # Verifica se alguma das partes é PJ
        reclamante_pj = self.detectar_eh_pessoa_juridica(reclamante)
        reclamada_pj = self.detectar_eh_pessoa_juridica(reclamada)
        
        # Se ambas são PF, não grava
        if not reclamante_pj and not reclamada_pj:
            return ""
        
        # Se pelo menos uma é PJ, grava a reclamada
        return reclamada
    
    def calcular_hash_conteudo(self, conteudo: str) -> str:
        """Calcula hash SHA256 do conteúdo normalizado."""
        # Normaliza: remove espaços extras, converte para minúsculas
        conteudo_norm = ' '.join(conteudo.split()).lower()
        return hashlib.sha256(conteudo_norm.encode('utf-8')).hexdigest()
    
    def processar_arquivo(self, filepath: Path) -> List[Dict]:
        """
        Processa um arquivo e retorna lista de registros extraídos.
        
        Returns:
            Lista de dicionários com os campos:
            - categoria
            - conteudo
            - numero_processo
            - data_publicacao
            - tipo_acao
            - reclamada
            - source_path
            - content_hash
        """
        filename = filepath.name
        
        # Verifica se deve ignorar
        deve_ignorar, motivo = self.deve_ignorar_arquivo(filename)
        if deve_ignorar:
            self.stats['ignorados'] += 1
            raise ValueError(f"Arquivo ignorado: {motivo}")
        
        # Extrai tipo de ação
        tipo_acao = self.extrair_tipo_acao(filename)
        
        # Extrai texto
        if filepath.suffix.lower() == '.docx':
            paragrafos = self.extrair_texto_docx(filepath)
        elif filepath.suffix.lower() == '.odt':
            paragrafos = self.extrair_texto_odt(filepath)
        else:
            self.stats['ignorados'] += 1
            raise ValueError(f"Extensão não suportada: {filepath.suffix}")
        
        # Monta texto completo para extração de metadados
        texto_completo = '\n'.join([p[0] for p in paragrafos])
        
        # Extrai metadados gerais
        numero_processo = self.extrair_numero_processo(texto_completo, filename)
        data_publicacao = self.extrair_data_publicacao(texto_completo, filepath)
        
        # Extrai partes
        reclamante, reclamada_raw = self.extrair_partes(texto_completo)
        reclamada = self.determinar_reclamada_para_metadados(reclamante, reclamada_raw)
        
        # Extrai fundamentação
        fundamentacao, _ = self.extrair_fundamentacao(paragrafos)
        
        if not fundamentacao:
            self.stats['erros'] += 1
            raise ValueError("Fundamentação não encontrada")
        
        # Quebra em tópicos
        topicos = self.quebrar_em_topicos(fundamentacao)
        
        # Cria registros
        registros = []
        for categoria, conteudo in topicos:
            registro = {
                'categoria': categoria,
                'conteudo': conteudo,
                'numero_processo': numero_processo or "DESCONHECIDO",
                'data_publicacao': data_publicacao,
                'tipo_acao': tipo_acao,
                'reclamada': reclamada,
                'source_path': str(filepath),
                'content_hash': self.calcular_hash_conteudo(conteudo)
            }
            registros.append(registro)
            self.stats['topicos_extraidos'] += 1
        
        self.stats['processados'] += 1
        return registros


def processar_pasta(
    pasta: Path,
    extensoes: List[str] = ['.docx', '.odt']
) -> Tuple[List[Dict], Dict]:
    """
    Processa todos os arquivos de uma pasta.
    
    Args:
        pasta: Caminho da pasta
        extensoes: Lista de extensões a processar
    
    Returns:
        (lista_registros, relatorio)
    """
    extrator = ExtratorSentenca()
    todos_registros = []
    relatorio = {
        'arquivos_processados': [],
        'arquivos_ignorados': [],
        'arquivos_erro': []
    }
    
    for ext in extensoes:
        for arquivo in pasta.glob(f'*{ext}'):
            try:
                registros = extrator.processar_arquivo(arquivo)
                todos_registros.extend(registros)
                relatorio['arquivos_processados'].append({
                    'arquivo': arquivo.name,
                    'topicos': len(registros)
                })
            except ValueError as e:
                relatorio['arquivos_ignorados'].append({
                    'arquivo': arquivo.name,
                    'motivo': str(e)
                })
            except Exception as e:
                relatorio['arquivos_erro'].append({
                    'arquivo': arquivo.name,
                    'erro': str(e)
                })
                extrator.stats['erros'] += 1
    
    relatorio['stats'] = extrator.stats
    return todos_registros, relatorio
