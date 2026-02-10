#!/usr/bin/env python3
"""
Calculate xAI Collections Processing Time Estimates
For large knowledge bases with token-based estimation.
"""
import argparse
from typing import Dict, Tuple


class ProcessingTimeEstimator:
    """Estimate processing time for xAI Collections uploads."""
    
    # Based on observed processing times and industry standards
    EMBEDDING_TIME_PER_CHUNK = 1.5  # seconds (conservative estimate)
    CHUNK_SIZE_CHARS = 2048  # characters per chunk
    CHUNK_OVERLAP = 256  # character overlap
    CHARS_PER_TOKEN = 4  # average for Portuguese/English
    
    # API rate limits and batch processing
    UPLOAD_RATE_LIMIT = 10  # uploads per second (estimated)
    BATCH_OVERHEAD = 1.2  # 20% overhead for batching
    
    # Processing stages
    UPLOAD_TIME_PER_DOC = 0.5  # seconds
    INDEX_BUILDING_OVERHEAD = 1.05  # 5% additional time
    
    def __init__(self):
        pass
    
    def tokens_to_chunks(self, tokens: int) -> int:
        """Convert tokens to estimated number of chunks."""
        chars = tokens * self.CHARS_PER_TOKEN
        
        # Calculate chunks with overlap
        effective_chunk_size = self.CHUNK_SIZE_CHARS - self.CHUNK_OVERLAP
        chunks = max(1, int(chars / effective_chunk_size))
        
        return chunks
    
    def estimate_processing_time(
        self, 
        total_tokens: int,
        sentences: int = None
    ) -> Dict[str, any]:
        """
        Estimate total processing time.
        
        Args:
            total_tokens: Total tokens in dataset
            sentences: Number of individual sentences/documents (optional)
            
        Returns:
            Dictionary with detailed time estimates
        """
        # Calculate chunks
        total_chunks = self.tokens_to_chunks(total_tokens)
        
        # Estimate documents if not provided
        if sentences is None:
            # Assume average 500 tokens per sentence
            sentences = max(1, int(total_tokens / 500))
        
        # Calculate processing times
        
        # 1. Upload time
        upload_time_min = (sentences * self.UPLOAD_TIME_PER_DOC) / 60
        
        # 2. Embedding generation time (the bottleneck)
        embedding_time_min = (total_chunks * self.EMBEDDING_TIME_PER_CHUNK) / 60
        
        # 3. Apply batch overhead
        embedding_time_min *= self.BATCH_OVERHEAD
        
        # 4. Index building overhead
        total_time_min = (upload_time_min + embedding_time_min) * self.INDEX_BUILDING_OVERHEAD
        
        # Convert to hours/days
        total_time_hours = total_time_min / 60
        total_time_days = total_time_hours / 24
        
        # Calculate rates
        tokens_per_hour = total_tokens / total_time_hours if total_time_hours > 0 else 0
        chunks_per_hour = total_chunks / total_time_hours if total_time_hours > 0 else 0
        
        return {
            'total_tokens': total_tokens,
            'total_sentences': sentences,
            'total_chunks': total_chunks,
            'chunks_per_sentence': total_chunks / sentences if sentences > 0 else 0,
            'upload_time_min': upload_time_min,
            'embedding_time_min': embedding_time_min,
            'total_time_min': total_time_min,
            'total_time_hours': total_time_hours,
            'total_time_days': total_time_days,
            'tokens_per_hour': tokens_per_hour,
            'chunks_per_hour': chunks_per_hour,
        }
    
    def format_time(self, minutes: float) -> str:
        """Format time in human-readable format."""
        if minutes < 60:
            return f"{minutes:.1f} minutes"
        elif minutes < 1440:  # Less than 24 hours
            hours = minutes / 60
            return f"{hours:.1f} hours ({minutes:.0f} minutes)"
        else:
            days = minutes / 1440
            hours = (minutes % 1440) / 60
            return f"{days:.1f} days ({hours:.1f} hours)"
    
    def print_estimate(self, total_tokens: int, sentences: int = None):
        """Print detailed processing time estimate."""
        
        print("=" * 80)
        print("xAI COLLECTIONS PROCESSING TIME ESTIMATE")
        print("=" * 80)
        print()
        
        # Calculate estimates
        est = self.estimate_processing_time(total_tokens, sentences)
        
        # Input summary
        print("📊 INPUT SUMMARY")
        print("-" * 80)
        print(f"   Total tokens:            {est['total_tokens']:,}")
        print(f"   Estimated sentences:     {est['total_sentences']:,}")
        print(f"   Estimated chunks:        {est['total_chunks']:,}")
        print(f"   Avg chunks per sentence: {est['chunks_per_sentence']:.1f}")
        print()
        
        # Processing breakdown
        print("⏱️  PROCESSING TIME BREAKDOWN")
        print("-" * 80)
        print(f"   Upload time:             {self.format_time(est['upload_time_min'])}")
        print(f"   Embedding generation:    {self.format_time(est['embedding_time_min'])}")
        print(f"   Index building overhead: +5%")
        print(f"   Batch overhead:          +20%")
        print()
        
        # Total estimate
        print("🎯 TOTAL ESTIMATED TIME")
        print("-" * 80)
        print(f"   Minimum:  {self.format_time(est['total_time_min'] * 0.7)}")
        print(f"   Expected: {self.format_time(est['total_time_min'])}")
        print(f"   Maximum:  {self.format_time(est['total_time_min'] * 1.5)}")
        print()
        
        # More readable format
        if est['total_time_hours'] < 24:
            print(f"   ⏰ Expect completion in: ~{est['total_time_hours']:.1f} hours")
        else:
            print(f"   ⏰ Expect completion in: ~{est['total_time_days']:.1f} days")
        print()
        
        # Processing rates
        print("📈 PROCESSING RATES")
        print("-" * 80)
        print(f"   Tokens per hour:         {est['tokens_per_hour']:,.0f}")
        print(f"   Chunks per hour:         {est['chunks_per_hour']:,.0f}")
        print(f"   Sentences per hour:      {est['total_sentences'] / est['total_time_hours']:,.0f}")
        print()
        
        # Recommendations
        self.print_recommendations(est)
        
        # Cost estimate (if applicable)
        self.print_cost_estimate(est)
        
        print("=" * 80)
    
    def print_recommendations(self, est: Dict):
        """Print recommendations based on estimate."""
        
        print("💡 RECOMMENDATIONS")
        print("-" * 80)
        
        total_hours = est['total_time_hours']
        
        if total_hours < 1:
            print("   ✅ Small dataset - single upload session recommended")
            print("   ✅ Upload all at once")
            print("   ✅ Monitor progress with check_processing_status.py")
        
        elif total_hours < 6:
            print("   ✅ Medium dataset - can complete in single session")
            print("   ✅ Upload all at once")
            print("   ✅ Use monitor mode to track progress")
            print("   ✅ Plan for ~6 hour processing window")
        
        elif total_hours < 24:
            print("   ⚠️  Large dataset - will take most of a day")
            print("   💡 Strategy 1: Upload all at once, check next day")
            print("   💡 Strategy 2: Split into 2-3 batches")
            print("   ⏰ Start upload in evening, complete by next morning")
        
        elif total_hours < 72:
            print("   ⚠️  Very large dataset - multi-day processing")
            print("   💡 STRONGLY RECOMMEND: Split into batches")
            print("   📦 Suggested batch size: 10M tokens (~250k chunks)")
            print("   ⏰ Upload batches sequentially (one per day)")
            print("   ✅ Reduces risk of timeouts/failures")
            print(f"   📊 Recommended batches: {int(est['total_tokens'] / 10_000_000) + 1}")
        
        else:  # > 3 days
            print("   🔴 EXTREMELY LARGE DATASET - requires careful planning")
            print("   💡 MANDATORY: Split into multiple batches")
            print("   📦 Suggested batch size: 5M tokens (~125k chunks)")
            print("   ⏰ Upload 1-2 batches per day")
            print(f"   📊 Recommended batches: {int(est['total_tokens'] / 5_000_000) + 1}")
            print("   ⚠️  Consider creating multiple Collections by topic/year")
            print("   📧 Contact xAI support for enterprise processing options")
        
        print()
        
        # General tips
        print("   📋 General Tips:")
        print("   • Upload during off-peak hours (late night/early morning)")
        print("   • Use SmartCollectionUploader.py with VPN")
        print("   • Monitor progress with check_processing_status.py --monitor")
        print("   • Keep backup of original JSON file")
        print("   • Test with small subset first (already done ✅)")
        print()
    
    def print_cost_estimate(self, est: Dict):
        """Print cost estimate (if known)."""
        
        print("💰 COST ESTIMATE (Approximate)")
        print("-" * 80)
        
        # Note: xAI pricing not fully public yet
        print("   ℹ️  xAI Collections pricing not fully public")
        print("   📊 Estimated factors:")
        print(f"      • Storage: {est['total_chunks']:,} chunks")
        print(f"      • Embedding: {est['total_chunks']:,} embeddings")
        print("   💡 Contact xAI sales for enterprise pricing")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Estimate xAI Collections processing time for large datasets",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # 50 million tokens
    python estimate_processing_time.py 50000000
    
    # 50 million tokens with known sentence count
    python estimate_processing_time.py 50000000 --sentences 100000
    
    # 1 million tokens (test dataset)
    python estimate_processing_time.py 1000000
        """
    )
    
    parser.add_argument("tokens", type=int, help="Total tokens in dataset")
    parser.add_argument("-s", "--sentences", type=int, help="Number of sentences/documents")
    
    args = parser.parse_args()
    
    estimator = ProcessingTimeEstimator()
    estimator.print_estimate(args.tokens, args.sentences)


if __name__ == "__main__":
    main()
