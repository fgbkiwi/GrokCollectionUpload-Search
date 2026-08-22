"""
test_extractor.py
Testes unitários para o módulo extractor.

Testa extração de tópicos, detecção de PF/PJ, parsing de metadados, etc.
Usa fixtures sintéticas (sem sentenças reais).
"""

import unittest
from pathlib import Path
import tempfile
import zipfile
import xml.etree.ElementTree as ET
import sys

# Adiciona diretório pai ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from indexador.extractor import ExtratorSentenca


class TestExtratorSentenca(unittest.TestCase):
    """Testes do ExtratorSentenca."""
    
    def setUp(self):
        """Setup para cada teste."""
        self.extrator = ExtratorSentenca()
    
    def test_deve_ignorar_despacho(self):
        """Testa que arquivos com 'dsp' são ignorados."""
        deve_ignorar, motivo = self.extrator.deve_ignorar_arquivo(
            "0000123-45.2023.5.10.0009_dsp_despacho.docx"
        )
        self.assertTrue(deve_ignorar)
        self.assertIn("dsp", motivo.lower())
    
    def test_deve_ignorar_sem_cnj(self):
        """Testa que arquivos sem número CNJ são ignorados."""
        deve_ignorar, motivo = self.extrator.deve_ignorar_arquivo(
            "sentenca_sem_numero.docx"
        )
        self.assertTrue(deve_ignorar)
        self.assertIn("cnj", motivo.lower())
    
    def test_nao_deve_ignorar_valido(self):
        """Testa que arquivo válido não é ignorado."""
        deve_ignorar, _ = self.extrator.deve_ignorar_arquivo(
            "0000123-45.2023.5.10.0009_sentenca.docx"
        )
        self.assertFalse(deve_ignorar)
    
    def test_extrair_tipo_acao_ms(self):
        """Testa extração de tipo de ação - Mandado de Segurança."""
        tipo = self.extrator.extrair_tipo_acao("0000123-45.2023.5.10.0009.ms.docx")
        self.assertEqual(tipo, "Mandado de Segurança")
    
    def test_extrair_tipo_acao_padrao(self):
        """Testa tipo de ação padrão quando não há sigla."""
        tipo = self.extrator.extrair_tipo_acao("0000123-45.2023.5.10.0009.docx")
        self.assertEqual(tipo, "Reclamação Trabalhista")
    
    def test_eh_titulo_topico_numerado(self):
        """Testa detecção de título numerado."""
        self.assertTrue(self.extrator.eh_titulo_topico("1. FUNDAMENTAÇÃO"))
        self.assertTrue(self.extrator.eh_titulo_topico("2.1 HORAS EXTRAORDINÁRIAS"))
        self.assertTrue(self.extrator.eh_titulo_topico("A) PRESCRIÇÃO"))
        self.assertTrue(self.extrator.eh_titulo_topico("A. MÉRITO"))
    
    def test_eh_titulo_topico_maiusculas(self):
        """Testa detecção de título em maiúsculas."""
        self.assertTrue(self.extrator.eh_titulo_topico("HORAS EXTRAORDINÁRIAS"))
        self.assertTrue(self.extrator.eh_titulo_topico("ADICIONAL DE INSALUBRIDADE"))
    
    def test_nao_eh_titulo_topico_artigos(self):
        """Testa que linhas começando com artigos não são títulos."""
        self.assertFalse(self.extrator.eh_titulo_topico("DOS PEDIDOS"))
        self.assertFalse(self.extrator.eh_titulo_topico("DAS PROVAS"))
    
    def test_nao_eh_titulo_topico_tabela(self):
        """Testa que linhas de tabela não são títulos."""
        self.assertFalse(self.extrator.eh_titulo_topico("TOTAL 1.234,56"))
        self.assertFalse(self.extrator.eh_titulo_topico("JAN/23 123,45"))
        self.assertFalse(self.extrator.eh_titulo_topico("VALOR 0,00"))
    
    def test_nao_eh_titulo_topico_formatted(self):
        """Testa que linhas formatadas não são títulos."""
        self.assertFalse(self.extrator.eh_titulo_topico("[FORMATTED: Texto formatado]"))
    
    def test_detectar_pj_ltda(self):
        """Testa detecção de pessoa jurídica - LTDA."""
        self.assertTrue(self.extrator.detectar_eh_pessoa_juridica("Empresa XYZ LTDA"))
        self.assertTrue(self.extrator.detectar_eh_pessoa_juridica("ABC S.A."))
        self.assertTrue(self.extrator.detectar_eh_pessoa_juridica("Hospital Municipal"))
    
    def test_detectar_pf(self):
        """Testa que nome de pessoa física não é detectado como PJ."""
        self.assertFalse(self.extrator.detectar_eh_pessoa_juridica("João da Silva"))
        self.assertFalse(self.extrator.detectar_eh_pessoa_juridica("Maria Santos"))
    
    def test_determinar_reclamada_pf_pf(self):
        """Testa que PF vs PF não grava reclamada."""
        reclamada = self.extrator.determinar_reclamada_para_metadados(
            reclamante="João da Silva",
            reclamada="Maria Santos"
        )
        self.assertEqual(reclamada, "")
    
    def test_determinar_reclamada_pf_pj(self):
        """Testa que PF vs PJ grava reclamada."""
        reclamada = self.extrator.determinar_reclamada_para_metadados(
            reclamante="João da Silva",
            reclamada="Empresa XYZ LTDA"
        )
        self.assertEqual(reclamada, "Empresa XYZ LTDA")
    
    def test_determinar_reclamada_pj_pf(self):
        """Testa que PJ vs PF grava reclamada."""
        reclamada = self.extrator.determinar_reclamada_para_metadados(
            reclamante="Sindicato ABC",
            reclamada="José Oliveira"
        )
        self.assertEqual(reclamada, "José Oliveira")
    
    def test_quebrar_em_topicos_simples(self):
        """Testa quebra em tópicos com títulos numerados."""
        fundamentacao = """
1. PRELIMINARES

Texto das preliminares aqui.

2. MÉRITO

Texto do mérito aqui.

3. CONCLUSÃO

Texto da conclusão.
        """.strip()
        
        topicos = self.extrator.quebrar_em_topicos(fundamentacao)
        
        self.assertEqual(len(topicos), 3)
        self.assertEqual(topicos[0][0], "1. PRELIMINARES")
        self.assertEqual(topicos[1][0], "2. MÉRITO")
        self.assertEqual(topicos[2][0], "3. CONCLUSÃO")
    
    def test_quebrar_em_topicos_sem_titulo(self):
        """Testa que fundamentação sem título vira um tópico 'FUNDAMENTOS'."""
        fundamentacao = "Texto corrido sem título de tópico."
        
        topicos = self.extrator.quebrar_em_topicos(fundamentacao)
        
        self.assertEqual(len(topicos), 1)
        self.assertEqual(topicos[0][0], "FUNDAMENTOS")
    
    def test_extrair_numero_processo_texto(self):
        """Testa extração de número de processo do texto."""
        texto = "Processo nº 0001234-56.2023.5.10.0009 trata de..."
        numero = self.extrator.extrair_numero_processo(texto, "arquivo.docx")
        self.assertEqual(numero, "0001234-56.2023.5.10.0009")
    
    def test_extrair_numero_processo_filename(self):
        """Testa extração de número de processo do nome do arquivo."""
        texto = "Sem número aqui"
        numero = self.extrator.extrair_numero_processo(
            texto,
            "0001234-56.2023.5.10.0009_sentenca.docx"
        )
        self.assertEqual(numero, "0001234-56.2023.5.10.0009")
    
    def test_extrair_data_publicacao(self):
        """Testa extração de data de publicação."""
        texto = "Aos 15 dias do mês de junho de 2023, proferi a seguinte sentença..."
        data = self.extrator.extrair_data_publicacao(texto, Path("dummy.docx"))
        self.assertEqual(data, "2023-06-15")
    
    def test_extrair_partes(self):
        """Testa extração de reclamante e reclamada."""
        texto = """
RECLAMANTE: João da Silva
RECLAMADA: Empresa ABC LTDA
        """
        
        reclamante, reclamada = self.extrator.extrair_partes(texto)
        self.assertEqual(reclamante, "João da Silva")
        self.assertEqual(reclamada, "Empresa ABC LTDA")
    
    def test_extrair_fundamentacao(self):
        """Testa extração da seção de fundamentação."""
        paragrafos = [
            ("RELATÓRIO", False),
            ("Trata-se de...", False),
            ("FUNDAMENTAÇÃO", False),
            ("1. PRELIMINARES", False),
            ("Rejeito as preliminares.", False),
            ("2. MÉRITO", False),
            ("O pedido é procedente.", False),
            ("DISPOSITIVO", False),
            ("Julgo procedente.", False),
        ]
        
        fundamentacao, idx = self.extrator.extrair_fundamentacao(paragrafos)
        
        self.assertIsNotNone(fundamentacao)
        self.assertIn("PRELIMINARES", fundamentacao)
        self.assertIn("MÉRITO", fundamentacao)
        self.assertNotIn("DISPOSITIVO", fundamentacao)
        self.assertNotIn("Julgo procedente", fundamentacao)
    
    def test_calcular_hash_conteudo(self):
        """Testa cálculo de hash normalizado."""
        conteudo1 = "Este   é   um    texto."
        conteudo2 = "este é um texto."
        
        hash1 = self.extrator.calcular_hash_conteudo(conteudo1)
        hash2 = self.extrator.calcular_hash_conteudo(conteudo2)
        
        # Hashes devem ser iguais (normalização)
        self.assertEqual(hash1, hash2)
        
        # Hash diferente para conteúdo diferente
        hash3 = self.extrator.calcular_hash_conteudo("Outro texto")
        self.assertNotEqual(hash1, hash3)


class TestExtratorIntegracao(unittest.TestCase):
    """Testes de integração com arquivos reais (sintéticos)."""
    
    def criar_docx_sintetico(self, conteudo_paragrafos: list) -> Path:
        """Cria um arquivo docx sintético para testes."""
        tmp_dir = Path(tempfile.mkdtemp())
        filepath = tmp_dir / "0001234-56.2023.5.10.0009_teste.docx"
        
        # Cria estrutura ZIP do docx
        with zipfile.ZipFile(filepath, 'w') as docx:
            # document.xml
            root = ET.Element(
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}document'
            )
            body = ET.SubElement(
                root,
                '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body'
            )
            
            for texto in conteudo_paragrafos:
                p = ET.SubElement(
                    body,
                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'
                )
                r = ET.SubElement(
                    p,
                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'
                )
                t = ET.SubElement(
                    r,
                    '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'
                )
                t.text = texto
            
            docx.writestr('word/document.xml', ET.tostring(root, encoding='unicode'))
            
            # core.xml (metadados)
            core_xml = """<?xml version="1.0"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                   xmlns:dcterms="http://purl.org/dc/terms/">
    <dcterms:created>2023-06-15T10:00:00Z</dcterms:created>
</cp:coreProperties>
            """
            docx.writestr('docProps/core.xml', core_xml)
        
        return filepath
    
    def test_processar_arquivo_completo(self):
        """Testa processamento completo de arquivo sintético."""
        paragrafos = [
            "RECLAMANTE: João da Silva",
            "RECLAMADA: Empresa XYZ LTDA",
            "Aos 15 dias do mês de junho de 2023.",
            "FUNDAMENTAÇÃO",
            "1. HORAS EXTRAORDINÁRIAS",
            "O reclamante laborou além da jornada sem o devido pagamento.",
            "2. ADICIONAL DE INSALUBRIDADE",
            "Comprovada a exposição a agentes insalubres.",
            "DISPOSITIVO",
            "Julgo procedente o pedido.",
        ]
        
        filepath = self.criar_docx_sintetico(paragrafos)
        
        try:
            extrator = ExtratorSentenca()
            registros = extrator.processar_arquivo(filepath)
            
            # Deve ter extraído 2 tópicos
            self.assertEqual(len(registros), 2)
            
            # Verifica primeiro registro
            r1 = registros[0]
            self.assertEqual(r1['categoria'], "1. HORAS EXTRAORDINÁRIAS")
            self.assertIn("jornada", r1['conteudo'].lower())
            self.assertEqual(r1['numero_processo'], "0001234-56.2023.5.10.0009")
            self.assertEqual(r1['data_publicacao'], "2023-06-15")
            self.assertEqual(r1['reclamada'], "Empresa XYZ LTDA")
            self.assertEqual(r1['tipo_acao'], "Reclamação Trabalhista")
            
            # Verifica segundo registro
            r2 = registros[1]
            self.assertEqual(r2['categoria'], "2. ADICIONAL DE INSALUBRIDADE")
            
        finally:
            # Limpa
            filepath.unlink()
            filepath.parent.rmdir()


if __name__ == '__main__':
    unittest.main()
