#!/usr/bin/env python3
"""
RobustCollectionUploader.py
Enhanced xAI Collections uploader with Cloudflare header workarounds.

Features:
- Multiple upload strategies with automatic fallback
- Cloudflare header bypass attempts
- Detailed error diagnostics
- Retry logic with exponential backoff
- VPN/proxy detection recommendations

Usage:
    python RobustCollectionUploader.py --config config.json --input sentences.json
"""
import requests
import json
import time
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple


class CloudflareWorkaroundUploader:
    """
    xAI Collections uploader with multiple strategies to work around
    Cloudflare cf-ipcity non-ASCII header issues.
    """
    
    def __init__(self, management_key: str, collection_id: str, verbose: bool = False):
        self.management_key = management_key
        self.collection_id = collection_id
        self.verbose = verbose
        self.base_url = "https://api.x.ai/v1"
        
        # Strategy statistics
        self.strategy_stats = {
            "default": {"attempts": 0, "success": 0, "failures": 0},
            "cf_bypass": {"attempts": 0, "success": 0, "failures": 0},
            "minimal": {"attempts": 0, "success": 0, "failures": 0},
            "aggressive": {"attempts": 0, "success": 0, "failures": 0},
        }
        
        self.successful_strategy = None
    
    def _get_headers(self, strategy: str) -> Dict[str, str]:
        """
        Get request headers for different upload strategies.
        
        Strategies:
        - default: Standard headers only
        - cf_bypass: Attempt to override CF geolocation headers
        - minimal: Bare minimum headers
        - aggressive: Multiple override attempts
        """
        base_headers = {
            "Authorization": f"Bearer {self.management_key}",
            "Content-Type": "application/json",
        }
        
        if strategy == "cf_bypass":
            base_headers.update({
                "X-Forwarded-For": "8.8.8.8",  # Google DNS (US)
                "X-Real-IP": "8.8.8.8",
                "Accept-Encoding": "identity",
                "User-Agent": "xai-python-sdk/1.0",
            })
        
        elif strategy == "minimal":
            # Only auth and content-type
            pass
        
        elif strategy == "aggressive":
            base_headers.update({
                "X-Forwarded-For": "1.1.1.1",  # Cloudflare DNS
                "X-Real-IP": "1.1.1.1",
                "CF-Connecting-IP": "1.1.1.1",
                "Accept-Encoding": "gzip, identity",
                "User-Agent": "xai-collections-client/2.0",
                "Cache-Control": "no-cache",
            })
        
        return base_headers
    
    def upload_document(
        self,
        content: str,
        metadata: Dict[str, Any],
        document_id: Optional[str] = None,
        max_retries_per_strategy: int = 2
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Upload document with multiple fallback strategies.
        
        Args:
            content: Document text content
            metadata: Document metadata
            document_id: Optional unique document ID
            max_retries_per_strategy: Retry attempts per strategy
            
        Returns:
            Tuple of (success, response_data, error_message)
        """
        payload = {
            "collection_id": self.collection_id,
            "content": content,
            "metadata": metadata
        }
        
        if document_id:
            payload["document_id"] = document_id
        
        # Try strategies in order of likelihood
        strategies = ["default", "cf_bypass", "aggressive", "minimal"]
        
        # If we already know a working strategy, try it first
        if self.successful_strategy:
            strategies.remove(self.successful_strategy)
            strategies.insert(0, self.successful_strategy)
        
        for strategy in strategies:
            headers = self._get_headers(strategy)
            
            for attempt in range(max_retries_per_strategy):
                self.strategy_stats[strategy]["attempts"] += 1
                
                try:
                    if self.verbose:
                        print(f"      [Strategy: {strategy}, Attempt: {attempt+1}]")
                    
                    response = requests.post(
                        f"{self.base_url}/collections/documents",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    
                    # Success!
                    if response.status_code == 200:
                        self.strategy_stats[strategy]["success"] += 1
                        
                        # Remember this working strategy
                        if not self.successful_strategy:
                            self.successful_strategy = strategy
                            if self.verbose:
                                print(f"      ✅ Found working strategy: {strategy}")
                        
                        return True, response.json(), None
                    
                    # Check for specific Cloudflare errors
                    elif response.status_code == 500:
                        error_text = response.text.lower()
                        
                        if "cf-ipcity" in error_text or "non-printable" in error_text:
                            # Cloudflare header issue - try next strategy
                            self.strategy_stats[strategy]["failures"] += 1
                            if self.verbose:
                                print(f"      ⚠️ CF header issue with {strategy}")
                            break  # Don't retry same strategy
                        else:
                            # Other 500 error - might be transient, retry
                            if attempt < max_retries_per_strategy - 1:
                                time.sleep(2 ** attempt)
                                continue
                    
                    # Other HTTP errors
                    else:
                        self.strategy_stats[strategy]["failures"] += 1
                        error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                        
                        # Don't retry client errors (4xx)
                        if 400 <= response.status_code < 500:
                            return False, None, error_msg
                        
                        # Retry server errors (5xx)
                        if attempt < max_retries_per_strategy - 1:
                            time.sleep(2 ** attempt)
                            continue
                
                except requests.exceptions.Timeout:
                    self.strategy_stats[strategy]["failures"] += 1
                    if attempt < max_retries_per_strategy - 1:
                        if self.verbose:
                            print(f"      ⏱️ Timeout, retrying...")
                        time.sleep(2 ** attempt)
                        continue
                    error_msg = "Request timeout"
                
                except requests.exceptions.RequestException as e:
                    self.strategy_stats[strategy]["failures"] += 1
                    error_msg = f"Request error: {str(e)}"
                    if attempt < max_retries_per_strategy - 1:
                        time.sleep(2 ** attempt)
                        continue
        
        # All strategies failed
        return False, None, "All upload strategies failed (likely Cloudflare issue)"
    
    def print_strategy_stats(self):
        """Print statistics about which strategies worked."""
        print("\n📊 Upload Strategy Statistics:")
        print("=" * 60)
        
        for strategy, stats in self.strategy_stats.items():
            if stats["attempts"] > 0:
                success_rate = (stats["success"] / stats["attempts"]) * 100
                print(f"  {strategy:12s}: {stats['success']:3d}/{stats['attempts']:3d} "
                      f"success ({success_rate:5.1f}%)")
        
        if self.successful_strategy:
            print(f"\n✅ Primary working strategy: {self.successful_strategy}")
        else:
            print("\n❌ No working strategy found")


class RobustSentencaProcessor:
    """
    Sentence processor using robust uploader with CF workarounds.
    """
    
    def __init__(
        self,
        management_key: str,
        collection_id: str,
        grok_api_key: Optional[str] = None,
        grok_model: str = "grok-beta",
        use_llm_keywords: bool = False,
        verbose: bool = False
    ):
        self.uploader = CloudflareWorkaroundUploader(
            management_key,
            collection_id,
            verbose=verbose
        )
        self.verbose = verbose
        self.use_llm_keywords = use_llm_keywords
        
        # Optional: LLM keyword generation
        if use_llm_keywords and grok_api_key:
            from CollectionUploaderV2 import GrokKeywordGenerator
            self.keyword_generator = GrokKeywordGenerator(grok_api_key, grok_model)
        else:
            self.keyword_generator = None
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "total_uploaded": 0,
            "upload_errors": 0,
            "chunks_created": 0,
        }
    
    def sanitize_filename(self, text: str) -> str:
        """Sanitize text for safe filename."""
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
            
            # Try to break at sentence boundary
            if end < len(text):
                last_period = text.rfind('.', start, end)
                if last_period > start + chunk_size // 2:
                    end = last_period + 1
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            start = end - overlap if end < len(text) else end
        
        return chunks
    
    def process_sentenca(self, item: Dict[str, Any], index: int) -> bool:
        """
        Process and upload a single sentence.
        
        Returns:
            True if upload successful, False otherwise
        """
        conteudo = item['conteudo'].strip()
        categoria = item['categoria']
        
        print(f"\n📄 [{index}] {categoria[:60]}...")
        
        # Generate keywords
        keywords = [categoria]
        if self.keyword_generator:
            try:
                print("   🤖 Generating keywords with LLM...")
                keywords = self.keyword_generator.generate_keywords(conteudo, categoria)
                print(f"   ✅ Keywords: {', '.join(keywords[:5])}...")
            except Exception as e:
                print(f"   ⚠️ Keyword generation failed: {e}")
                print("   ⚠️ Using category only")
        
        # Chunk content
        chunks = self.chunk_text(conteudo)
        print(f"   📊 Chunks: {len(chunks)}")
        
        all_success = True
        
        # Upload each chunk
        for chunk_idx, chunk in enumerate(chunks):
            # Prepare metadata
            metadata = {
                "categoria": categoria,
                "reclamada": item.get('reclamada', 'Não especificada'),
                "numero_processo": item['numero_processo'],
                "data_publicacao": item.get('data_publicacao', 'Não informada'),
                "tipo_acao": item.get('tipo_acao', 'Não informado'),
                "keywords": keywords
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
            
            # Upload
            print(f"   📤 Uploading chunk {chunk_idx + 1}/{len(chunks)}...")
            success, response, error = self.uploader.upload_document(
                content=chunk,
                metadata=metadata,
                document_id=doc_id
            )
            
            if success:
                print(f"   ✅ Uploaded: {doc_id}")
                self.stats['total_uploaded'] += 1
            else:
                print(f"   ❌ Upload failed: {error}")
                self.stats['upload_errors'] += 1
                all_success = False
            
            self.stats['chunks_created'] += 1
            
            # Rate limiting
            time.sleep(0.3)
        
        self.stats['total_processed'] += 1
        return all_success
    
    def process_json_file(self, json_file: str) -> bool:
        """
        Process entire JSON file.
        
        Returns:
            True if all uploads successful, False if any failed
        """
        print(f"\n{'='*70}")
        print(f"📄 ROBUST UPLOADER - Processing: {json_file}")
        print(f"{'='*70}\n")
        
        # Load JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"✅ {len(data)} sentences loaded\n")
        
        # Process each sentence
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
        
        # Print strategy statistics
        self.uploader.print_strategy_stats()
        
        # Recommendations if failures occurred
        if self.stats['upload_errors'] > 0:
            print(f"\n⚠️ RECOMMENDATIONS:")
            print(f"   - {self.stats['upload_errors']} uploads failed")
            
            if not self.uploader.successful_strategy:
                print("   - All strategies failed (likely Cloudflare issue)")
                print("   - Try using VPN from US/UK location")
                print("   - Or run: python diagnose_xai_upload.py <key> <collection_id>")
                print("   - Contact xAI support about cf-ipcity header issue")
        
        return all_success


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Robust xAI Collections Uploader with CF workarounds",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example config.json:
{
  "management_key": "xai-mgmt-xxx",
  "collection_id": "col_xxx",
  "grok_api_key": "xai-xxx",  # Optional for LLM keywords
  "grok_model": "grok-beta",
  "use_llm_keywords": false
}

Usage:
  python RobustCollectionUploader.py --config config.json --input sentences.json
  python RobustCollectionUploader.py --config config.json --input sentences.json -v
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
    processor = RobustSentencaProcessor(
        management_key=config['management_key'],
        collection_id=config['collection_id'],
        grok_api_key=config.get('grok_api_key'),
        grok_model=config.get('grok_model', 'grok-beta'),
        use_llm_keywords=config.get('use_llm_keywords', False),
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
