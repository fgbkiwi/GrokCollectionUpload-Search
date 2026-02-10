#!/usr/bin/env python3
"""
Check xAI Collection Processing Status
Monitors document processing status and provides diagnostic information.
"""
import requests
import json
import time
import argparse
from datetime import datetime
from typing import Dict, List, Any


class CollectionStatusChecker:
    """Check and monitor Collection processing status."""
    
    def __init__(self, management_key: str, collection_id: str):
        self.management_key = management_key
        self.collection_id = collection_id
        self.base_url = "https://api.x.ai/v1"
        self.headers = {
            "Authorization": f"Bearer {management_key}",
            "Content-Type": "application/json",
        }
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get Collection information."""
        response = requests.get(
            f"{self.base_url}/collections/{self.collection_id}",
            headers=self.headers,
            timeout=10
        )
        response.raise_for_status()
        return response.json()
    
    def list_documents(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List documents in Collection."""
        try:
            response = requests.get(
                f"{self.base_url}/collections/{self.collection_id}/documents",
                headers=self.headers,
                params={"limit": limit},
                timeout=30
            )
            response.raise_for_status()
            data = response.json()
            return data.get('documents', [])
        except Exception as e:
            print(f"⚠️  Could not list documents: {e}")
            return []
    
    def check_status(self, monitor_mode: bool = False, interval: int = 30):
        """Check Collection and document status."""
        
        print("🔍 Checking xAI Collection Processing Status")
        print("=" * 70)
        print(f"Collection ID: {self.collection_id}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Get Collection info
        try:
            collection = self.get_collection_info()
            print(f"✅ Collection: {collection.get('name', 'N/A')}")
            print(f"   Created: {collection.get('created_at', 'N/A')}")
            print(f"   Updated: {collection.get('updated_at', 'N/A')}")
            
            # Check embedding settings
            embedding_model = collection.get('embedding_model', 'default')
            chunk_size = collection.get('chunk_size', 'N/A')
            print(f"\n⚙️  Embedding Settings:")
            print(f"   Model: {embedding_model}")
            print(f"   Chunk Size: {chunk_size}")
            
        except Exception as e:
            print(f"❌ Could not fetch Collection info: {e}")
            return
        
        # Get documents
        print(f"\n📄 Fetching documents...")
        documents = self.list_documents()
        
        if not documents:
            print("⚠️  No documents found or unable to list documents")
            print("\nℹ️  This might mean:")
            print("   1. Documents are still being processed")
            print("   2. API doesn't support document listing yet")
            print("   3. Management key doesn't have list permissions")
            return
        
        print(f"✅ Found {len(documents)} documents")
        
        # Analyze document statuses
        status_counts = {}
        processing_docs = []
        completed_docs = []
        failed_docs = []
        
        for doc in documents:
            status = doc.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == 'processing':
                processing_docs.append(doc)
            elif status == 'completed':
                completed_docs.append(doc)
            elif status in ['failed', 'error']:
                failed_docs.append(doc)
        
        # Print status summary
        print(f"\n📊 Document Status Summary:")
        print("-" * 70)
        for status, count in sorted(status_counts.items()):
            emoji = {
                'completed': '✅',
                'processing': '⏳',
                'failed': '❌',
                'error': '❌',
                'pending': '⏸️'
            }.get(status, '❓')
            print(f"   {emoji} {status:15s}: {count:3d} documents")
        
        # Processing documents details
        if processing_docs:
            print(f"\n⏳ Processing Documents ({len(processing_docs)}):")
            print("-" * 70)
            for i, doc in enumerate(processing_docs[:10], 1):
                doc_id = doc.get('id', 'N/A')
                created = doc.get('created_at', 'N/A')
                print(f"   {i}. {doc_id}")
                print(f"      Created: {created}")
                if i == 10 and len(processing_docs) > 10:
                    print(f"   ... and {len(processing_docs) - 10} more")
        
        # Failed documents details
        if failed_docs:
            print(f"\n❌ Failed Documents ({len(failed_docs)}):")
            print("-" * 70)
            for i, doc in enumerate(failed_docs[:5], 1):
                doc_id = doc.get('id', 'N/A')
                error = doc.get('error', 'No error message')
                print(f"   {i}. {doc_id}")
                print(f"      Error: {error}")
        
        # Calculate processing time
        if processing_docs:
            oldest_processing = None
            newest_processing = None
            
            for doc in processing_docs:
                created_at = doc.get('created_at')
                if created_at:
                    if oldest_processing is None or created_at < oldest_processing:
                        oldest_processing = created_at
                    if newest_processing is None or created_at > newest_processing:
                        newest_processing = created_at
            
            if oldest_processing:
                print(f"\n⏱️  Processing Time:")
                print(f"   Oldest processing doc: {oldest_processing}")
                print(f"   Newest processing doc: {newest_processing}")
        
        # Provide diagnosis
        self.provide_diagnosis(status_counts, len(documents))
        
        # Monitor mode
        if monitor_mode:
            print(f"\n👀 Monitor mode enabled (checking every {interval}s)")
            print("   Press Ctrl+C to stop")
            try:
                while True:
                    time.sleep(interval)
                    print(f"\n{'='*70}")
                    print(f"🔄 Refresh at {datetime.now().strftime('%H:%M:%S')}")
                    self.check_status(monitor_mode=False)
            except KeyboardInterrupt:
                print("\n\n✅ Monitoring stopped")
    
    def provide_diagnosis(self, status_counts: Dict[str, int], total_docs: int):
        """Provide diagnostic recommendations."""
        
        print(f"\n💡 Diagnosis:")
        print("=" * 70)
        
        processing_count = status_counts.get('processing', 0)
        completed_count = status_counts.get('completed', 0)
        failed_count = status_counts.get('failed', 0) + status_counts.get('error', 0)
        
        processing_pct = (processing_count / total_docs * 100) if total_docs > 0 else 0
        
        if processing_count == 0 and completed_count == total_docs:
            print("✅ ALL DOCUMENTS PROCESSED SUCCESSFULLY!")
            print("   Your Collection is ready to use for search.")
            return
        
        if processing_count > 0:
            print(f"⏳ {processing_count} documents still processing ({processing_pct:.1f}%)")
            print()
            print("❓ Is this normal or a bug?")
            print()
            
            # Normal processing time estimates
            print("📊 Normal Processing Times:")
            print("   • Small docs (<1000 chars): 30 seconds - 2 minutes")
            print("   • Medium docs (1000-5000 chars): 2-5 minutes")
            print("   • Large docs (>5000 chars): 5-15 minutes")
            print("   • Batch processing: Add 1-2 min overhead per batch")
            print()
            
            # When to worry
            print("⚠️  When to Suspect a Bug:")
            print("   • Processing > 30 minutes for small documents")
            print("   • Processing > 1 hour for medium documents")
            print("   • Status stuck at 'processing' for > 2 hours")
            print("   • No progress after multiple checks (30+ min apart)")
            print()
            
            # Possible causes
            print("🔍 Possible Causes of Slow Processing:")
            print("   1. High xAI API load (peak hours)")
            print("   2. Large document size requiring more embedding time")
            print("   3. Complex metadata fields requiring processing")
            print("   4. Embedding model is resource-intensive")
            print("   5. Backend queue is processing many Collections")
            print()
            
            # Recommendations
            print("💡 Recommendations:")
            print("   1. ✅ Wait another 30-60 minutes if < 1 hour has passed")
            print("   2. ✅ Use monitor mode to track progress:")
            print("      python check_processing_status.py <key> <id> --monitor")
            print("   3. ⏰ Check again after 1-2 hours")
            print("   4. 📧 Contact xAI support if stuck > 2 hours:")
            print("      Email: support@x.ai")
            print("      Subject: Collection processing stuck")
            print(f"      Collection ID: {self.collection_id}")
            print()
        
        if failed_count > 0:
            print(f"❌ {failed_count} documents FAILED processing")
            print("   Check error messages above and:")
            print("   • Verify document format is correct")
            print("   • Check document size is within limits")
            print("   • Ensure metadata is valid")
            print("   • Contact xAI support if errors persist")
            print()
        
        # Progress indicator
        if completed_count > 0 and processing_count > 0:
            print(f"📈 Progress: {completed_count}/{total_docs} completed ({completed_count/total_docs*100:.1f}%)")
            if completed_count > 0:
                print("   ✅ GOOD SIGN: Some documents completed successfully")
                print("   → This means processing is working, just taking time")


def main():
    parser = argparse.ArgumentParser(
        description="Check xAI Collection processing status",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Check status once
    python check_processing_status.py <management_key> <collection_id>
    
    # Monitor status every 30 seconds
    python check_processing_status.py <management_key> <collection_id> --monitor
    
    # Monitor with custom interval
    python check_processing_status.py <management_key> <collection_id> --monitor --interval 60
        """
    )
    
    parser.add_argument("management_key", help="Your xAI Management Key")
    parser.add_argument("collection_id", help="Collection ID to check")
    parser.add_argument("-m", "--monitor", action="store_true", 
                       help="Monitor mode (continuous checking)")
    parser.add_argument("-i", "--interval", type=int, default=30,
                       help="Check interval in seconds for monitor mode (default: 30)")
    
    args = parser.parse_args()
    
    checker = CollectionStatusChecker(args.management_key, args.collection_id)
    checker.check_status(monitor_mode=args.monitor, interval=args.interval)


if __name__ == "__main__":
    main()
