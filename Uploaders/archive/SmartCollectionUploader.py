#!/usr/bin/env python3
"""
SmartCollectionUploader.py
Auto-detects Collection schema and only uses defined fields.
Compatible with any xAI Collection configuration.

Usage:
    python SmartCollectionUploader.py --config config.json --input sentences.json
"""
import requests
import json
import time
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Set


class SmartCollectionUploader:
    """
    Smart uploader that auto-detects Collection schema and filters metadata.
    """
    
    def __init__(self, management_key: str, collection_id: str, verbose: bool = False):
        self.management_key = management_key
        self.collection_id = collection_id
        self.verbose = verbose
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json",
        }
        
        # Cache for allowed fields
        self._allowed_fields = None
    
    def get_allowed_fields(self) -> Set[str]:
        """Get Collection's defined metadata fields (cached)."""
        if self._allowed_fields is not None:
            return self._allowed_fields
        
        try:
            response = requests.get(
                f"{self.base_url}/collections/{self.collection_id}",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            field_defs = data.get('field_definitions', {})
            self._allowed_fields = set(field_defs.keys())
            
            if self.verbose:
                print(f"\n📋 Collection schema detected:")
                print(f"   Allowed fields: {self._allowed_fields}")
            
            return self._allowed_fields
        
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch Collection schema: {e}")
            print(f"   Proceeding without metadata field filtering")
            # Return empty set = allow all fields
            self._allowed_fields = set()
            return self._allowed_fields
    
    def filter_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Filter metadata to only include Collection-defined fields."""
        allowed = self.get_allowed_fields()
        
        # If no fields defined (or fetch failed), allow all
        if not allowed:
            return metadata
        
        # Filter to only allowed fields
        filtered = {k: v for k, v in metadata.items() if k in allowed}
        
        # Log filtered fields if verbose
        if self.verbose:
            removed = set(metadata.keys()) - set(filtered.keys())
            if removed:
                print(f"   ℹ️  Filtered out fields: {removed}")
        
        return filtered
    
    def upload_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Upload document with auto-filtered metadata."""
        
        # Filter metadata
        filtered_metadata = self.filter_metadata(metadata)
        
        payload = {
            "collection_id": self.collection_id,
            "content": content,
            "metadata": filtered_metadata
        }
        
        if document_id:
            payload["document_id"] = document_id
        
        response = requests.post(
            f"{self.base_url}/collections/documents",
            headers=self.headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()


class SmartSentencaProcessor:
    """Process sentences with smart metadata filtering."""
    
    def __init__(
        self,
        management_key: str,
        collection_id: str,
        verbose: bool = False
    ):
        self.uploader = SmartCollectionUploader(
            management_key,
            collection_id,
            verbose=verbose
        )
        self.verbose = verbose
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_uploaded": 0,
            "upload_errors": 0,
            "chunks_created": 0,
        }
    
    def sanitize_filename(self, text: str) -> str:
        """Sanitize text for filename."""
        import re
        text = re.sub(r'[<>:"/\\|?*]', '', text)
        text = re.sub(r'[\s\-—]+', '_', text)
        return text[:100]
    
    def chunk_text(self, text: str, chunk_size: int = 2048, overlap: int = 256) -> List[str]:
        """Split text into chunks with overlap."""
        if len(text) <= chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + chunk_size
            
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def extract_simple_keywords(self, conteudo: str, categoria: str) -> List[str]:
        """Extract simple keywords without LLM."""
        import re
        
        keywords = [categoria]
        
        # Legal terms patterns
        patterns = [
            r'\bart\.\s*\d+',  # art. 123
            r'\bCLT\b',
            r'Lei\s+\d+',
            r'Súmula\s+\d+',
            r'\bTST\b',
            r'\bSTF\b'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, conteudo, re.IGNORECASE)
            keywords.extend(matches[:5])  # Limit matches
        
        # Remove duplicates, keep order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower not in seen:
                seen.add(kw_lower)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # Limit to 10
    
    def process_sentenca(self, item: Dict[str, Any], index: int) -> bool:
        """Process and upload a single sentence."""
        conteudo = item['conteudo'].strip()
        categoria = item['categoria']
        
        print(f"\n📄 [{index}] {categoria[:60]}...")
        
        # Extract simple keywords
        keywords = self.extract_simple_keywords(conteudo, categoria)
        if self.verbose:
            print(f"   🔑 Keywords: {', '.join(keywords[:5])}...")
        
        # Chunk content
        chunks = self.chunk_text(conteudo)
        print(f"   📊 Chunks: {len(chunks)}")
        
        all_success = True
        
        # Upload each chunk
        for chunk_idx, chunk in enumerate(chunks):
            # Prepare ALL possible metadata (will be filtered automatically)
            metadata = {
                "categoria": categoria,
                "reclamada": item.get('reclamada', 'Não especificada') or 'Não especificada',
                "numero_processo": item['numero_processo'],
                "data_publicacao": item.get('data_publicacao', 'Não informada') or 'Não informada',
                "tipo_acao": item.get('tipo_acao', 'Não informado') or 'Não informado',
                "keywords": keywords,  # Will be filtered if not defined
                "original_filename": f"{index:04d}_{categoria[:30]}.md"  # Will be filtered if not defined
            }
            
            if len(chunks) > 1:
                metadata["chunk_info"] = f"Parte {chunk_idx + 1} de {len(chunks)}"
            
            # Generate document ID
            categoria_safe = self.sanitize_filename(categoria)
            processo_safe = item['numero_processo'].replace('.', '_').replace('-', '_')
            
            if len(chunks) > 1:
                doc_id = f"{index:04d}_{processo_safe}_{categoria_safe}_part{chunk_idx+1:02d}"
            else:
                doc_id = f"{index:04d}_{processo_safe}_{categoria_safe}"
            
            # Upload (metadata will be auto-filtered)
            try:
                if self.verbose:
                    print(f"   📤 Uploading chunk {chunk_idx + 1}/{len(chunks)}...")
                
                result = self.uploader.upload_document(
                    content=chunk,
                    metadata=metadata,
                    document_id=doc_id
                )
                
                print(f"   ✅ Uploaded: {doc_id}")
                self.stats['total_uploaded'] += 1
            
            except requests.exceptions.HTTPError as e:
                error_msg = str(e.response.text) if hasattr(e, 'response') else str(e)
                print(f"   ❌ Upload failed: {error_msg[:200]}")
                self.stats['upload_errors'] += 1
                all_success = False
            
            except Exception as e:
                print(f"   ❌ Upload failed: {str(e)[:200]}")
                self.stats['upload_errors'] += 1
                all_success = False
            
            self.stats['chunks_created'] += 1
            time.sleep(0.3)
        
        self.stats['total_processed'] += 1
        return all_success
    
    def process_json_file(self, json_file: str) -> bool:
        """Process entire JSON file."""
        print(f"\n{'='*70}")
        print(f"📄 SMART UPLOADER - Processing: {json_file}")
        print(f"{'='*70}\n")
        
        # Load JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ {len(data)} sentences loaded")
        
        # Detect Collection schema upfront
        print(f"\n🔍 Detecting Collection schema...")
        allowed_fields = self.uploader.get_allowed_fields()
        if allowed_fields:
            print(f"✅ Collection has {len(allowed_fields)} defined fields")
            print(f"   Fields: {', '.join(sorted(allowed_fields))}")
        else:
            print(f"⚠️  Collection schema detection failed or no fields defined")
            print(f"   Proceeding with all metadata fields")
        
        # Process each sentence
        print(f"\n📤 Starting upload...\n")
        start_time = time.time()
        all_success = True
        
        for idx, item in enumerate(data, start=1):
            try:
                success = self.process_sentenca(item, idx)
                if not success:
                    all_success = False
            except Exception as e:
                print(f"❌ Error processing sentence {idx}: {e}")
                self.stats['upload_errors'] += 1
                all_success = False
        
        elapsed_time = time.time() - start_time
        
        # Print final statistics
        print(f"\n{'='*70}")
        print(f"✅ PROCESSING COMPLETE")
        print(f"{'='*70}\n")
        
        print(f"📊 Statistics:")
        print(f"   Sentences processed:  {self.stats['total_processed']}")
        print(f"   Chunks created:       {self.stats['chunks_created']}")
        print(f"   Successful uploads:   {self.stats['total_uploaded']}")
        print(f"   Failed uploads:       {self.stats['upload_errors']}")
        print(f"   Total time:           {elapsed_time:.2f}s")
        print(f"   Avg time/sentence:    {elapsed_time / max(self.stats['total_processed'], 1):.2f}s")
        
        if self.stats['upload_errors'] > 0:
            print(f"\n⚠️  {self.stats['upload_errors']} uploads failed")
            print(f"   Check error messages above for details")
        else:
            print(f"\n🎉 All uploads successful!")
        
        return all_success


def main():
    parser = argparse.ArgumentParser(
        description="Smart xAI Collections Uploader with auto-schema detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example config.json:
{
  "management_key": "xai-mgmt-xxx",
  "collection_id": "col_xxx"
}

Usage:
  python SmartCollectionUploader.py --config config.json --input sentences.json
  python SmartCollectionUploader.py --config config.json --input sentences.json -v
        """
    )
    
    parser.add_argument("--config", required=True, help="JSON config file")
    parser.add_argument("--input", required=True, help="Input JSON file with sentences")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Load config
    if not Path(args.config).exists():
        print(f"❌ Config file not found: {args.config}")
        return 1
    
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    # Validate config
    required = ['management_key', 'collection_id']
    missing = [k for k in required if k not in config]
    if missing:
        print(f"❌ Missing config keys: {', '.join(missing)}")
        return 1
    
    # Validate input file
    if not Path(args.input).exists():
        print(f"❌ Input file not found: {args.input}")
        return 1
    
    # Process
    processor = SmartSentencaProcessor(
        management_key=config['management_key'],
        collection_id=config['collection_id'],
        verbose=args.verbose
    )
    
    try:
        success = processor.process_json_file(args.input)
        return 0 if success else 1
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
