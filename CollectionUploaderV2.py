#!/usr/bin/env python3
"""
CollectionUploaderV2.py
Versão avançada com geração de keywords via LLM e upload direto para xAI Collections.

Melhorias:
- Keywords geradas por Grok (contextualmente relevantes)
- Upload automático via xAI Collections API
- Metadados separados do conteúdo (não incluídos nos arquivos MD)
- Melhor aproveitamento do chunk size

Uso:
    python CollectionUploaderV2.py --config config.json
"""

import json
import os
import re
import argparse
import requests
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class GrokKeywordGenerator:
    """Gerador de keywords usando modelo Grok."""
    
    def __init__(self, api_key: str, model: str = "grok-beta"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_keywords(self, conteudo: str, categoria: str, max_retries: int = 3) -> List[str]:
        """
        Gera keywords contextuais usando Grok.
        
        Args:
            conteudo: Texto da fundamentação
            categoria: Categoria da sentença
            max_retries: Número máximo de tentativas
            
        Returns:
            Lista de keywords relevantes
        """
        prompt = f"""Analise esta fundamentação jurídica trabalhista e extraia as palavras-chave mais relevantes para busca e recuperação de informação.

CATEGORIA: {categoria}

FUNDAMENTAÇÃO:
{conteudo[:3000]}  # Limita para não exceder contexto

INSTRUÇÕES:
1. Identifique os aspectos fundamentais da controvérsia jurídica
2. Extraia dispositivos legais ESPECÍFICOS citados (com artigos, parágrafos, incisos)
   - Formato: "art. 317 CLT", "arts. 461 a 467 CLT", "art. 7º, XIII CF"
   - Inclua nome completo de leis: "Lei 9.394/1996 (LDB)", "Lei 8.112/1990"
3. Identifique conceitos jurídicos relevantes (não genéricos)
   - BOM: "instrutor técnico", "equiparação salarial entre professores", "adicional de insalubridade grau médio"
   - EVITE: "legislação", "direito", "CLT" (sem especificar artigo)
4. Inclua termos técnicos específicos da área
5. Mencione súmulas/jurisprudência citadas: "Súmula 374 TST", "OJ 387 SDI-1"
6. Cláusulas de normas coletivas mencionadas
7. Limite: 10-15 keywords

FORMATO DE RESPOSTA (JSON):
{{
  "keywords": [
    "keyword1",
    "keyword2",
    ...
  ]
}}

Responda APENAS com o JSON, sem explicações adicionais."""

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "Você é um especialista em Direito do Trabalho brasileiro. Sua tarefa é extrair keywords precisas e relevantes de fundamentações jurídicas. Seja específico e evite termos genéricos."
                            },
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,  # Mais conservador para consistência
                        "max_tokens": 500
                    },
                    timeout=60
                )
                response.raise_for_status()
                
                # Extrai resposta
                content = response.json()["choices"][0]["message"]["content"]
                
                # Parse JSON
                # Remove markdown code blocks se presentes
                content = re.sub(r'```json\s*', '', content)
                content = re.sub(r'```\s*', '', content)
                
                data = json.loads(content.strip())
                keywords = data.get("keywords", [])
                
                # Adiciona categoria como primeira keyword
                if categoria not in keywords:
                    keywords.insert(0, categoria)
                
                return keywords[:15]  # Limita a 15
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Erro ao parsear JSON do Grok (tentativa {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                # Fallback: retorna apenas categoria
                return [categoria]
                
            except Exception as e:
                print(f"⚠️ Erro ao gerar keywords com Grok (tentativa {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                # Fallback: retorna apenas categoria
                return [categoria]
        
        # Se todas as tentativas falharam
        return [categoria]


class XAICollectionsUploader:
    """Cliente para upload direto em xAI Collections via API."""
    
    def __init__(self, management_key: str, collection_id: str):
        self.management_key = management_key
        self.collection_id = collection_id
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json"
        }
    
    def upload_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Faz upload de um documento para a Collection.
        
        Args:
            content: Conteúdo do documento (texto puro)
            metadata: Metadados estruturados
            document_id: ID único do documento (opcional)
            
        Returns:
            Resposta da API
        """
        payload = {
            "collection_id": self.collection_id,
            "content": content,
            "metadata": metadata
        }
        
        if document_id:
            payload["document_id"] = document_id
        
        try:
            response = requests.post(
                f"{self.base_url}/collections/documents",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Erro no upload: {str(e)}")
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Obtém informações da Collection."""
        try:
            response = requests.get(
                f"{self.base_url}/collections/{self.collection_id}",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Erro ao obter info da Collection: {str(e)}")


class SentencaProcessorV2:
    """Processador avançado de sentenças com LLM keywords e upload API."""
    
    def __init__(
        self,
        grok_api_key: str,
        management_key: str,
        collection_id: str,
        output_dir: str = "./sentencas_md",
        grok_model: str = "grok-beta",
        save_local_md: bool = True
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.keyword_generator = GrokKeywordGenerator(grok_api_key, grok_model)
        self.uploader = XAICollectionsUploader(management_key, collection_id)
        self.save_local_md = save_local_md
        
        # Estatísticas
        self.stats = {
            "total_processed": 0,
            "total_uploaded": 0,
            "chunks_created": 0,
            "keywords_generated": 0,
            "upload_errors": 0,
            "categorias": set(),
            "tipos_acao": set(),
        }
    
    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        """Divide texto em chunks com overlap."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            # Tenta quebrar em ponto final
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def sanitize_filename(self, text: str) -> str:
        """Sanitiza texto para nome de arquivo."""
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'[\s\-—]+', '_', text)
        return text[:100]
    
    def process_sentenca(self, item: Dict[str, Any], index: int) -> int:
        """
        Processa uma sentença: gera keywords com LLM e faz upload.
        
        Args:
            item: Objeto JSON da sentença
            index: Índice sequencial
            
        Returns:
            Número de chunks criados
        """
        conteudo = item['conteudo'].strip()
        categoria = item['categoria']
        
        print(f"\n📄 Processando sentença {index}: {categoria[:50]}...")
        
        # Gera keywords com LLM
        print("   🤖 Gerando keywords com Grok...")
        keywords = self.keyword_generator.generate_keywords(conteudo, categoria)
        self.stats['keywords_generated'] += len(keywords)
        print(f"   ✅ Keywords geradas: {', '.join(keywords[:5])}{'...' if len(keywords) > 5 else ''}")
        
        # Atualiza estatísticas
        self.stats['categorias'].add(categoria)
        self.stats['tipos_acao'].add(item['tipo_acao'])
        
        # Divide em chunks
        chunks = self.chunk_text(conteudo)
        
        # Processa cada chunk
        for chunk_idx, chunk in enumerate(chunks):
            # Cria metadados
            metadata = {
                "categoria": categoria,
                "reclamada": item['reclamada'] if item['reclamada'] else "Não especificada",
                "numero_processo": item['numero_processo'],
                "data_publicacao": item['data_publicacao'] if item['data_publicacao'] else "Não informada",
                "tipo_acao": item['tipo_acao'],
                "keywords": keywords  # Lista de keywords geradas pelo LLM
            }
            
            # Adiciona indicador de chunk se houver múltiplos
            if len(chunks) > 1:
                metadata["chunk_info"] = f"Parte {chunk_idx + 1} de {len(chunks)}"
            
            # ID único do documento
            categoria_safe = self.sanitize_filename(categoria)
            processo_safe = item['numero_processo'].replace('.', '_').replace('-', '_')
            
            if len(chunks) > 1:
                doc_id = f"{index:04d}_{processo_safe}_{categoria_safe}_part{chunk_idx+1:02d}"
            else:
                doc_id = f"{index:04d}_{processo_safe}_{categoria_safe}"
            
            # Conteúdo puro (SEM metadados YAML)
            content = chunk
            
            # Upload para xAI Collections
            try:
                print(f"   📤 Uploading chunk {chunk_idx + 1}/{len(chunks)} para xAI Collections...")
                self.uploader.upload_document(
                    content=content,
                    metadata=metadata,
                    document_id=doc_id
                )
                self.stats['total_uploaded'] += 1
                print(f"   ✅ Upload concluído: {doc_id}")
            except Exception as e:
                print(f"   ❌ Erro no upload: {e}")
                self.stats['upload_errors'] += 1
            
            # Salva arquivo MD local (opcional, para backup)
            if self.save_local_md:
                filename = f"{doc_id}.md"
                filepath = self.output_dir / filename
                
                # Cabeçalho do arquivo
                md_content = f"# {categoria}\n\n"
                if len(chunks) > 1:
                    md_content += f"**[Parte {chunk_idx+1} de {len(chunks)}]**\n\n"
                md_content += content
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(md_content)
            
            self.stats['chunks_created'] += 1
            
            # Rate limiting (para não sobrecarregar API)
            time.sleep(0.5)
        
        return len(chunks)
    
    def process_json_file(self, json_file: str) -> None:
        """Processa arquivo JSON completo."""
        print(f"\n{'='*70}")
        print(f"📄 PROCESSANDO ARQUIVO: {json_file}")
        print(f"📁 Diretório MD local: {self.output_dir}")
        print(f"{'='*70}\n")
        
        # Carrega JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ {len(data)} sentenças encontradas\n")
        
        # Verifica Collection
        try:
            collection_info = self.uploader.get_collection_info()
            print(f"✅ Collection conectada: {collection_info.get('name', 'N/A')}")
            print(f"   ID: {self.uploader.collection_id}\n")
        except Exception as e:
            print(f"❌ Erro ao conectar Collection: {e}")
            print("   Verifique Management Key e Collection ID\n")
            return
        
        # Processa cada sentença
        start_time = time.time()
        
        for idx, item in enumerate(data, start=1):
            try:
                chunks_count = self.process_sentenca(item, idx)
                self.stats['total_processed'] += 1
            except Exception as e:
                print(f"❌ Erro ao processar sentença {idx}: {e}")
                continue
        
        elapsed_time = time.time() - start_time
        
        print(f"\n{'='*70}")
        print(f"✅ PROCESSAMENTO CONCLUÍDO!")
        print(f"{'='*70}\n")
        self.print_statistics(elapsed_time)
    
    def print_statistics(self, elapsed_time: float) -> None:
        """Imprime estatísticas do processamento."""
        print("📊 ESTATÍSTICAS DO PROCESSAMENTO")
        print("="*70)
        print(f"Sentenças processadas:          {self.stats['total_processed']}")
        print(f"Documentos uploaded (xAI):      {self.stats['total_uploaded']}")
        print(f"Chunks criados:                 {self.stats['chunks_created']}")
        print(f"Keywords geradas (total):       {self.stats['keywords_generated']}")
        print(f"Erros de upload:                {self.stats['upload_errors']}")
        print(f"Categorias únicas:              {len(self.stats['categorias'])}")
        print(f"Tipos de ação únicos:           {len(self.stats['tipos_acao'])}")
        print(f"Tempo total:                    {elapsed_time:.2f}s")
        print(f"Tempo médio por sentença:       {elapsed_time / max(self.stats['total_processed'], 1):.2f}s")
        print("="*70)
        
        if self.save_local_md:
            print(f"\n📁 Arquivos MD salvos em: {self.output_dir.absolute()}")
        
        print("\n✅ Upload concluído! Documentos disponíveis na Collection para busca.")


def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description='CollectionUploaderV2 - Upload inteligente com keywords geradas por LLM',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplo de config.json:
{
  "grok_api_key": "xai-xxx",
  "management_key": "xai-mgmt-xxx",
  "collection_id": "col_xxx",
  "grok_model": "grok-beta",
  "output_dir": "./sentencas_md",
  "save_local_md": true
}

Uso:
  python CollectionUploaderV2.py --config config.json --input "Sentenças.json"
        """
    )
    
    parser.add_argument(
        '--config',
        required=True,
        help='Arquivo JSON com configurações (API keys, Collection ID, etc.)'
    )
    
    parser.add_argument(
        '--input',
        required=True,
        help='Arquivo JSON com as sentenças'
    )
    
    args = parser.parse_args()
    
    # Carrega configurações
    if not os.path.exists(args.config):
        print(f"❌ Arquivo de config não encontrado: {args.config}")
        return 1
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Valida configurações
    required_keys = ['grok_api_key', 'management_key', 'collection_id']
    missing_keys = [k for k in required_keys if k not in config]
    if missing_keys:
        print(f"❌ Configurações faltando: {', '.join(missing_keys)}")
        return 1
    
    # Valida arquivo de entrada
    if not os.path.exists(args.input):
        print(f"❌ Arquivo de entrada não encontrado: {args.input}")
        return 1
    
    # Processa
    processor = SentencaProcessorV2(
        grok_api_key=config['grok_api_key'],
        management_key=config['management_key'],
        collection_id=config['collection_id'],
        output_dir=config.get('output_dir', './sentencas_md'),
        grok_model=config.get('grok_model', 'grok-beta'),
        save_local_md=config.get('save_local_md', True)
    )
    
    try:
        processor.process_json_file(args.input)
        return 0
    except Exception as e:
        print(f"\n❌ Erro durante processamento: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
