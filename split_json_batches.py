#!/usr/bin/env python3
"""
Split large JSON file into manageable batches for xAI Collections upload.
Supports splitting by count, by year, or by topic.
"""
import json
import math
import argparse
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict


class JSONBatchSplitter:
    """Split large JSON files into batches."""
    
    def __init__(self, input_file: str, output_dir: str):
        self.input_file = input_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.data = None
    
    def load_data(self):
        """Load JSON data."""
        print(f"📂 Loading {self.input_file}...")
        with open(self.input_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        print(f"✅ Loaded {len(self.data)} sentences")
        return self.data
    
    def split_by_count(self, batch_size: int):
        """Split by number of sentences per batch."""
        if not self.data:
            self.load_data()
        
        total_sentences = len(self.data)
        num_batches = math.ceil(total_sentences / batch_size)
        
        print(f"\n📊 Splitting into {num_batches} batches of {batch_size} sentences each")
        print("=" * 70)
        
        batches_created = []
        
        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, total_sentences)
            
            batch_data = self.data[start_idx:end_idx]
            batch_filename = f"batch_{batch_num+1:02d}_of_{num_batches:02d}.json"
            batch_path = self.output_dir / batch_filename
            
            # Save batch
            with open(batch_path, 'w', encoding='utf-8') as f:
                json.dump(batch_data, f, ensure_ascii=False, indent=2)
            
            batches_created.append({
                'filename': batch_filename,
                'path': str(batch_path),
                'sentences': len(batch_data),
                'start': start_idx,
                'end': end_idx
            })
            
            print(f"✅ {batch_filename}: {len(batch_data)} sentences (indices {start_idx}-{end_idx-1})")
        
        self.print_summary(batches_created)
        self.create_upload_script(batches_created)
    
    def split_by_year(self):
        """Split by publication year."""
        if not self.data:
            self.load_data()
        
        print(f"\n📊 Splitting by publication year")
        print("=" * 70)
        
        # Group by year
        by_year = defaultdict(list)
        no_date_count = 0
        
        for sentence in self.data:
            date_str = sentence.get('data_publicacao', '')
            if date_str and len(date_str) >= 4:
                year = date_str[:4]
                by_year[year].append(sentence)
            else:
                no_date_count += 1
        
        # Sort years
        sorted_years = sorted(by_year.keys())
        
        print(f"Found {len(sorted_years)} years: {', '.join(sorted_years)}")
        if no_date_count > 0:
            print(f"⚠️  {no_date_count} sentences without date")
        print()
        
        batches_created = []
        
        for year in sorted_years:
            sentences = by_year[year]
            batch_filename = f"batch_year_{year}.json"
            batch_path = self.output_dir / batch_filename
            
            # Save batch
            with open(batch_path, 'w', encoding='utf-8') as f:
                json.dump(sentences, f, ensure_ascii=False, indent=2)
            
            batches_created.append({
                'filename': batch_filename,
                'path': str(batch_path),
                'sentences': len(sentences),
                'year': year
            })
            
            print(f"✅ {batch_filename}: {len(sentences)} sentences")
        
        self.print_summary(batches_created)
        self.create_upload_script(batches_created)
    
    def split_by_category(self, max_per_batch: int = 10000):
        """Split by category (with size limits)."""
        if not self.data:
            self.load_data()
        
        print(f"\n📊 Splitting by category (max {max_per_batch} per batch)")
        print("=" * 70)
        
        # Group by category
        by_category = defaultdict(list)
        
        for sentence in self.data:
            category = sentence.get('categoria', 'SEM_CATEGORIA')
            by_category[category].append(sentence)
        
        # Sort categories by count
        sorted_categories = sorted(by_category.keys(), key=lambda c: len(by_category[c]), reverse=True)
        
        print(f"Found {len(sorted_categories)} categories")
        print()
        
        batches_created = []
        
        for category in sorted_categories:
            sentences = by_category[category]
            
            # If category is too large, split it
            if len(sentences) > max_per_batch:
                num_sub_batches = math.ceil(len(sentences) / max_per_batch)
                for i in range(num_sub_batches):
                    start = i * max_per_batch
                    end = min((i + 1) * max_per_batch, len(sentences))
                    sub_batch = sentences[start:end]
                    
                    batch_filename = f"batch_cat_{category[:30]}_part{i+1:02d}.json"
                    batch_path = self.output_dir / batch_filename
                    
                    with open(batch_path, 'w', encoding='utf-8') as f:
                        json.dump(sub_batch, f, ensure_ascii=False, indent=2)
                    
                    batches_created.append({
                        'filename': batch_filename,
                        'path': str(batch_path),
                        'sentences': len(sub_batch),
                        'category': category
                    })
                    
                    print(f"✅ {batch_filename}: {len(sub_batch)} sentences")
            else:
                batch_filename = f"batch_cat_{category[:30]}.json"
                batch_path = self.output_dir / batch_filename
                
                with open(batch_path, 'w', encoding='utf-8') as f:
                    json.dump(sentences, f, ensure_ascii=False, indent=2)
                
                batches_created.append({
                    'filename': batch_filename,
                    'path': str(batch_path),
                    'sentences': len(sentences),
                    'category': category
                })
                
                print(f"✅ {batch_filename}: {len(sentences)} sentences")
        
        self.print_summary(batches_created)
        self.create_upload_script(batches_created)
    
    def print_summary(self, batches: List[Dict]):
        """Print summary of created batches."""
        print()
        print("=" * 70)
        print("📊 BATCH SUMMARY")
        print("=" * 70)
        print(f"Total batches created: {len(batches)}")
        print(f"Output directory: {self.output_dir.absolute()}")
        
        total_sentences = sum(b['sentences'] for b in batches)
        print(f"Total sentences: {total_sentences}")
        
        if batches:
            avg_sentences = total_sentences / len(batches)
            min_sentences = min(b['sentences'] for b in batches)
            max_sentences = max(b['sentences'] for b in batches)
            
            print(f"Average per batch: {avg_sentences:.0f}")
            print(f"Min per batch: {min_sentences}")
            print(f"Max per batch: {max_sentences}")
        
        print()
        print("💡 Next steps:")
        print("   1. Review batch files in output directory")
        print("   2. Run upload script: bash upload_batches.sh")
        print("   3. Or upload manually:")
        print(f"      python SmartCollectionUploader.py --config config.json --input {self.output_dir}/batch_XX.json")
        print()
    
    def create_upload_script(self, batches: List[Dict]):
        """Create bash script to upload all batches."""
        script_path = self.output_dir / "upload_batches.sh"
        
        with open(script_path, 'w') as f:
            f.write("#!/bin/bash\n")
            f.write("# Batch upload script\n")
            f.write("# Upload batches one by one with VPN and monitoring\n\n")
            
            f.write("# Configuration\n")
            f.write("CONFIG_FILE=\"config.json\"\n")
            f.write("UPLOADER=\"SmartCollectionUploader.py\"\n")
            f.write("STATUS_CHECKER=\"check_processing_status.py\"\n\n")
            
            f.write("# Check if config exists\n")
            f.write("if [ ! -f \"$CONFIG_FILE\" ]; then\n")
            f.write("    echo \"❌ config.json not found\"\n")
            f.write("    exit 1\n")
            f.write("fi\n\n")
            
            f.write("# Upload each batch\n")
            for i, batch in enumerate(batches, 1):
                batch_file = batch['filename']
                f.write(f"\necho \"\"\n")
                f.write(f"echo \"{'='*70}\"\n")
                f.write(f"echo \"📦 BATCH {i}/{len(batches)}: {batch_file}\"\n")
                f.write(f"echo \"{'='*70}\"\n")
                f.write(f"echo \"\"\n\n")
                
                f.write(f"# Upload batch {i}\n")
                f.write(f"python \"$UPLOADER\" --config \"$CONFIG_FILE\" --input \"{self.output_dir}/{batch_file}\"\n\n")
                
                f.write(f"if [ $? -eq 0 ]; then\n")
                f.write(f"    echo \"✅ Batch {i} upload completed\"\n")
                f.write(f"else\n")
                f.write(f"    echo \"❌ Batch {i} upload failed\"\n")
                f.write(f"    read -p \"Continue with next batch? (y/n) \" -n 1 -r\n")
                f.write(f"    echo\n")
                f.write(f"    if [[ ! $REPLY =~ ^[Yy]$ ]]; then\n")
                f.write(f"        exit 1\n")
                f.write(f"    fi\n")
                f.write(f"fi\n\n")
                
                f.write(f"# Wait before next batch\n")
                if i < len(batches):
                    f.write(f"echo \"⏸️  Waiting 10 seconds before next batch...\"\n")
                    f.write(f"sleep 10\n")
            
            f.write(f"\necho \"\"\n")
            f.write(f"echo \"{'='*70}\"\n")
            f.write(f"echo \"✅ ALL BATCHES UPLOADED\"\n")
            f.write(f"echo \"{'='*70}\"\n")
            f.write(f"echo \"\"\n")
        
        # Make executable
        script_path.chmod(0o755)
        
        print(f"✅ Created upload script: {script_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Split large JSON file into batches for xAI Collections",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Split into 10k sentence batches
    python split_json_batches.py input.json --output ./batches --size 10000
    
    # Split by year
    python split_json_batches.py input.json --output ./batches --by-year
    
    # Split by category
    python split_json_batches.py input.json --output ./batches --by-category
        """
    )
    
    parser.add_argument("input", help="Input JSON file")
    parser.add_argument("-o", "--output", default="./batches", help="Output directory")
    parser.add_argument("-s", "--size", type=int, help="Sentences per batch (for count-based split)")
    parser.add_argument("--by-year", action="store_true", help="Split by publication year")
    parser.add_argument("--by-category", action="store_true", help="Split by category")
    parser.add_argument("--max-per-category", type=int, default=10000, 
                       help="Max sentences per category batch (default: 10000)")
    
    args = parser.parse_args()
    
    splitter = JSONBatchSplitter(args.input, args.output)
    
    if args.by_year:
        splitter.split_by_year()
    elif args.by_category:
        splitter.split_by_category(args.max_per_category)
    elif args.size:
        splitter.split_by_count(args.size)
    else:
        print("❌ Please specify split method:")
        print("   --size N           (split into N-sentence batches)")
        print("   --by-year          (split by publication year)")
        print("   --by-category      (split by category)")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
