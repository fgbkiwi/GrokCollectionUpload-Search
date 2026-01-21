#!/usr/bin/env python3
"""
CollectionUploader.py
Script para processar arquivo JSON de sentenças trabalhistas e criar arquivos Markdown
para upload em xAI Collections com metadados estruturados.

Uso:
    python CollectionUploader.py <arquivo_json> [--output-dir <diretorio>]
    
Exemplo:
    python CollectionUploader.py "Sentenças Indexadas Revisado (excerto).json.txt" --output-dir ./sentencas_md
"""

import json
import os
import re
import argparse
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime


class SentencaProcessor:
    """Processador de sentenças trabalhistas para xAI Collections."""
    
    def __init__(self, output_dir: str = "./sentencas_md"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Estatísticas de processamento
        self.stats = {
            "total_processed": 0,
            "chunks_created": 0,
            "categorias": set(),
            "tipos_acao": set(),
        }
    
    def extract_keywords(self, conteudo: str, categoria: str) -> List[str]:
        """
        Extrai palavras-chave jurídicas do conteúdo para metadados.
        
        Args:
            conteudo: Texto da fundamentação
            categoria: Categoria da sentença
            
        Returns:
            Lista de palavras-chave relevantes
        """
        keywords = []
        
        # Adiciona a categoria como keyword principal
        keywords.append(categoria.lower())
        
        # Padrões jurídicos comuns
        legal_patterns = {
            # Leis e normas
            r'art\.?\s*\d+': 'artigo_clt',
            r'CLT': 'clt',
            r'Lei\s+\d+': 'legislacao',
            r'Súmula\s+\d+': 'sumula',
            r'TST': 'jurisprudencia_tst',
            r'STF': 'jurisprudencia_stf',
            r'Constituição': 'constitucional',
            
            # Conceitos trabalhistas
            r'horas?\s+extraordinárias?': 'horas_extras',
            r'adicional\s+noturno': 'adicional_noturno',
            r'adicional\s+de\s+insalubridade': 'insalubridade',
            r'adicional\s+de\s+periculosidade': 'periculosidade',
            r'FGTS': 'fgts',
            r'férias': 'ferias',
            r'13º\s+salário|gratificação\s+natalina': 'decimo_terceiro',
            r'rescisão': 'rescisao_contratual',
            r'justa\s+causa': 'justa_causa',
            r'reintegração': 'reintegracao',
            r'equiparação\s+salarial': 'equiparacao_salarial',
            r'prescrição': 'prescricao',
            r'honorários\s+advocatícios': 'honorarios',
            r'justiça\s+gratuita': 'justica_gratuita',
            r'dano\s+moral': 'dano_moral',
            r'dano\s+material': 'dano_material',
            r'intervalo\s+intrajornada': 'intervalo',
            r'repousos?\s+semanais?': 'repouso_semanal',
            r'categoria\s+profissional': 'categoria_profissional',
            r'sindicato|sindical': 'direito_sindical',
            r'convenção\s+coletiva|acordo\s+coletivo': 'norma_coletiva',
        }
        
        # Busca padrões no conteúdo
        conteudo_lower = conteudo.lower()
        for pattern, keyword in legal_patterns.items():
            if re.search(pattern, conteudo_lower, re.IGNORECASE):
                if keyword not in keywords:
                    keywords.append(keyword)
        
        # Limita a 15 keywords para evitar poluição
        return keywords[:15]
    
    def create_metadata_header(self, item: Dict[str, Any], keywords: List[str]) -> str:
        """
        Cria o cabeçalho de metadados para o arquivo Markdown.
        
        Args:
            item: Objeto JSON da sentença
            keywords: Palavras-chave extraídas
            
        Returns:
            String formatada com metadados
        """
        metadata_lines = [
            "---",
            f"categoria: {item['categoria']}",
            f"reclamada: {item['reclamada'] if item['reclamada'] else 'Não especificada'}",
            f"numero_processo: {item['numero_processo']}",
            f"data_publicacao: {item['data_publicacao'] if item['data_publicacao'] else 'Não informada'}",
            f"tipo_acao: {item['tipo_acao']}",
            f"keywords: {', '.join(keywords)}",
            "---",
            ""
        ]
        
        return "\n".join(metadata_lines)
    
    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        """
        Divide texto em chunks com overlap para preservar contexto.
        
        Args:
            text: Texto a ser dividido
            chunk_size: Tamanho do chunk em caracteres
            overlap: Sobreposição entre chunks
            
        Returns:
            Lista de chunks de texto
        """
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Tenta quebrar em ponto final para não cortar frases
            if end < len(text):
                # Procura último ponto antes do limite
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:  # Se encontrou ponto razoável
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move para próximo chunk com overlap
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def sanitize_filename(self, text: str) -> str:
        """
        Sanitiza texto para nome de arquivo seguro.
        
        Args:
            text: Texto a ser sanitizado
            
        Returns:
            String segura para nome de arquivo
        """
        # Remove caracteres inválidos
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        # Substitui espaços e caracteres especiais por underscore
        text = re.sub(r'[\s\-—]+', '_', text)
        # Limita tamanho
        return text[:100]
    
    def process_sentenca(self, item: Dict[str, Any], index: int) -> int:
        """
        Processa uma sentença individual e cria arquivo(s) MD.
        
        Args:
            item: Objeto JSON da sentença
            index: Índice sequencial
            
        Returns:
            Número de chunks criados
        """
        conteudo = item['conteudo'].strip()
        
        # Extrai keywords
        keywords = self.extract_keywords(conteudo, item['categoria'])
        
        # Atualiza estatísticas
        self.stats['categorias'].add(item['categoria'])
        self.stats['tipos_acao'].add(item['tipo_acao'])
        
        # Divide em chunks se necessário
        chunks = self.chunk_text(conteudo)
        
        for chunk_idx, chunk in enumerate(chunks):
            # Cria nome de arquivo único
            categoria_safe = self.sanitize_filename(item['categoria'])
            processo_safe = item['numero_processo'].replace('.', '_').replace('-', '_')
            
            if len(chunks) > 1:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}_part{chunk_idx+1:02d}.md"
            else:
                filename = f"{index:04d}_{processo_safe}_{categoria_safe}.md"
            
            filepath = self.output_dir / filename
            
            # Cria cabeçalho de metadados
            metadata = self.create_metadata_header(item, keywords)
            
            # Adiciona indicador de chunk se aplicável
            if len(chunks) > 1:
                chunk_info = f"\n**[Parte {chunk_idx+1} de {len(chunks)}]**\n\n"
            else:
                chunk_info = ""
            
            # Escreve arquivo MD
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(metadata)
                f.write(f"# {item['categoria']}\n\n")
                if chunk_info:
                    f.write(chunk_info)
                f.write(chunk)
            
            self.stats['chunks_created'] += 1
        
        return len(chunks)
    
    def process_json_file(self, json_file: str) -> None:
        """
        Processa arquivo JSON completo.
        
        Args:
            json_file: Caminho para arquivo JSON
        """
        print(f"\n📄 Processando arquivo: {json_file}")
        print(f"📁 Diretório de saída: {self.output_dir}\n")
        
        # Carrega JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ {len(data)} sentenças encontradas no arquivo\n")
        
        # Processa cada sentença
        for idx, item in enumerate(data, start=1):
            chunks_count = self.process_sentenca(item, idx)
            self.stats['total_processed'] += 1
            
            if idx % 10 == 0:
                print(f"⏳ Processadas: {idx}/{len(data)} sentenças...")
        
        print(f"\n✅ Processamento concluído!\n")
        self.print_statistics()
    
    def print_statistics(self) -> None:
        """Imprime estatísticas do processamento."""
        print("=" * 70)
        print("📊 ESTATÍSTICAS DO PROCESSAMENTO")
        print("=" * 70)
        print(f"Total de sentenças processadas:     {self.stats['total_processed']}")
        print(f"Total de arquivos MD criados:       {self.stats['chunks_created']}")
        print(f"Categorias únicas:                  {len(self.stats['categorias'])}")
        print(f"Tipos de ação únicos:               {len(self.stats['tipos_acao'])}")
        print(f"Tamanho médio por arquivo:          ~{2048 // 1} caracteres")
        print("=" * 70)
        
        print("\n📋 CATEGORIAS ENCONTRADAS:")
        for cat in sorted(self.stats['categorias']):
            print(f"  • {cat}")
        
        print("\n📋 TIPOS DE AÇÃO ENCONTRADOS:")
        for tipo in sorted(self.stats['tipos_acao']):
            print(f"  • {tipo}")
        
        print("\n" + "=" * 70)
        print("📝 PRÓXIMOS PASSOS:")
        print("=" * 70)
        print("1. Acesse o console do xAI: https://console.x.ai/")
        print("2. Crie uma nova Collection com as seguintes configurações:")
        print("   • Chunk Size: 2048 caracteres (~512 tokens)")
        print("   • Chunk Overlap: 256 caracteres (~64 tokens)")
        print("   • Embedding Model: Padrão xAI")
        print("3. Gere uma Management Key para a Collection")
        print("4. Faça upload dos arquivos MD do diretório:")
        print(f"   {self.output_dir.absolute()}")
        print("5. Configure os campos de metadados na Collection:")
        print("   • categoria (filtro)")
        print("   • reclamada (filtro)")
        print("   • numero_processo (filtro)")
        print("   • data_publicacao (filtro)")
        print("   • tipo_acao (filtro)")
        print("   • keywords (busca)")
        print("=" * 70 + "\n")


def main():
    """Função principal do script."""
    parser = argparse.ArgumentParser(
        description='Processa sentenças trabalhistas para xAI Collections',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos de uso:
  python CollectionUploader.py "Sentenças Indexadas Revisado (excerto).json.txt"
  python CollectionUploader.py input.json --output-dir ./minhas_sentencas
        """
    )
    
    parser.add_argument(
        'json_file',
        help='Arquivo JSON com as sentenças'
    )
    
    parser.add_argument(
        '--output-dir',
        default='./sentencas_md',
        help='Diretório de saída para arquivos MD (padrão: ./sentencas_md)'
    )
    
    args = parser.parse_args()
    
    # Valida arquivo de entrada
    if not os.path.exists(args.json_file):
        print(f"❌ Erro: Arquivo não encontrado: {args.json_file}")
        return 1
    
    # Processa
    processor = SentencaProcessor(args.output_dir)
    try:
        processor.process_json_file(args.json_file)
        return 0
    except Exception as e:
        print(f"\n❌ Erro durante processamento: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
