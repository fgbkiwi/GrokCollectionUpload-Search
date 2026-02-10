# Strategy for Processing 50 Million Token Knowledge Base

## 🎯 Your Dataset

**Size:** ~50 million tokens  
**Estimated:** ~100,000 sentences → ~111,607 chunks  
**Your test:** 25 sentences → 64 chunks (took 30-60 min)

---

## ⏱️ **Processing Time Estimate**

### By the Numbers:

| Metric | Estimate |
|--------|----------|
| **Total Processing Time** | **~3 days (72 hours)** |
| Minimum (best case) | 2.1 days |
| Expected (realistic) | 3.0 days |
| Maximum (worst case) | 4.6 days |
| **Chunks to process** | 111,607 |
| **Processing rate** | ~1,525 chunks/hour |

### Why So Long?

**Embedding generation is the bottleneck:**
- 111,607 chunks × 1.5 seconds each = 167,410 seconds
- ÷ 60 = 2,790 minutes = **46.5 hours of pure embedding time**
- Plus upload, indexing, batch overhead = **~72 hours total**

---

## 🚨 **CRITICAL: Do NOT Upload All At Once**

### Why Not?

1. ❌ **Timeout Risk:** 72-hour processing may exceed xAI's timeout limits
2. ❌ **Failure Recovery:** If it fails at 90%, you lose 2.5 days of processing
3. ❌ **Resource Monopolization:** May impact xAI's system and other users
4. ❌ **No Progress Visibility:** Can't tell if it's stuck or still working
5. ❌ **API Rate Limits:** May hit undocumented rate limits

### What Could Go Wrong?

- Processing gets stuck after 24-48 hours
- xAI backend times out the job
- Network interruption during upload
- You can't tell which documents processed vs. failed
- Need to restart from scratch

---

## ✅ **RECOMMENDED STRATEGY: Batch Processing**

### Strategy A: 10 Batches (Conservative - RECOMMENDED)

**Split into 10 batches of 5M tokens each (~11,160 chunks per batch)**

| Batch | Tokens | Chunks | Processing Time | When to Upload |
|-------|--------|--------|-----------------|----------------|
| 1 | 5M | ~11,160 | ~7-8 hours | Day 1, 10pm |
| 2 | 5M | ~11,160 | ~7-8 hours | Day 2, 10pm |
| 3 | 5M | ~11,160 | ~7-8 hours | Day 3, 10pm |
| 4 | 5M | ~11,160 | ~7-8 hours | Day 4, 10pm |
| 5 | 5M | ~11,160 | ~7-8 hours | Day 5, 10pm |
| 6 | 5M | ~11,160 | ~7-8 hours | Day 6, 10pm |
| 7 | 5M | ~11,160 | ~7-8 hours | Day 7, 10pm |
| 8 | 5M | ~11,160 | ~7-8 hours | Day 8, 10pm |
| 9 | 5M | ~11,160 | ~7-8 hours | Day 9, 10pm |
| 10 | 5M | ~11,160 | ~7-8 hours | Day 10, 10pm |

**Total time:** 10 days (1 batch per day)  
**Advantages:**
- ✅ Each batch completes overnight (7-8 hours)
- ✅ Easy to monitor and verify
- ✅ Low risk of timeout/failure
- ✅ Can resume if one batch fails
- ✅ Start at 10pm, complete by 6am next day

### Strategy B: 20 Batches (Most Conservative)

**Split into 20 batches of 2.5M tokens each (~5,580 chunks per batch)**

- Processing time per batch: **3-4 hours**
- Upload 2 batches per day (morning + evening)
- Total time: **10 days**
- Lowest risk, highest control

### Strategy C: 5 Batches (Aggressive - Not Recommended)

**Split into 5 batches of 10M tokens each (~22,321 chunks per batch)**

- Processing time per batch: **14-16 hours**
- Upload 1 batch per day
- Total time: **5 days**
- ⚠️ Higher risk of timeout per batch
- ⚠️ Harder to recover from failures

---

## 📦 **How to Split the JSON File**

### Option 1: Python Script (Recommended)

Create `split_json_batches.py`:

```python
#!/usr/bin/env python3
"""Split large JSON file into batches."""
import json
import math
from pathlib import Path

def split_json_into_batches(input_file: str, batch_size: int, output_dir: str):
    """
    Split JSON file into batches.
    
    Args:
        input_file: Path to large JSON file
        batch_size: Number of sentences per batch
        output_dir: Directory to save batch files
    """
    # Load full JSON
    print(f"Loading {input_file}...")
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    total_sentences = len(data)
    num_batches = math.ceil(total_sentences / batch_size)
    
    print(f"Total sentences: {total_sentences}")
    print(f"Batch size: {batch_size}")
    print(f"Number of batches: {num_batches}")
    print()
    
    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    # Split into batches
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, total_sentences)
        
        batch_data = data[start_idx:end_idx]
        batch_filename = f"batch_{batch_num+1:02d}_of_{num_batches:02d}.json"
        batch_path = Path(output_dir) / batch_filename
        
        # Save batch
        with open(batch_path, 'w', encoding='utf-8') as f:
            json.dump(batch_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Created {batch_filename}: {len(batch_data)} sentences")
    
    print(f"\n✅ All batches created in: {output_dir}")

if __name__ == "__main__":
    # Configuration
    INPUT_FILE = "Sentenças Indexadas Revisado.json"  # Your full file
    BATCH_SIZE = 10000  # 10k sentences per batch (for 10 batches)
    OUTPUT_DIR = "./batches"
    
    split_json_into_batches(INPUT_FILE, BATCH_SIZE, OUTPUT_DIR)
```

**Usage:**
```bash
python split_json_batches.py
```

### Option 2: Manual Split (By Topic/Year)

If your sentences have dates or topics, split logically:

```python
# Example: Split by year
batches_by_year = {}
for sentence in data:
    year = sentence.get('data_publicacao', '')[:4]  # Extract year
    if year not in batches_by_year:
        batches_by_year[year] = []
    batches_by_year[year].append(sentence)

# Save each year as separate batch
for year, sentences in batches_by_year.items():
    filename = f"batch_year_{year}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(sentences, f, ensure_ascii=False, indent=2)
```

**Advantages:**
- ✅ Logical organization
- ✅ Easier to search by year later
- ✅ Can prioritize recent years first

---

## 🚀 **Batch Upload Workflow**

### Day 1-10: Upload One Batch Per Night

**Each evening (10pm):**

```bash
# 1. Connect VPN (to avoid Cloudflare issues)
# Connect to US/UK server

# 2. Upload batch
python SmartCollectionUploader.py \
    --config config.json \
    --input ./batches/batch_01_of_10.json

# 3. Start monitoring (optional - run in background)
python check_processing_status.py YOUR_KEY YOUR_COLLECTION_ID --monitor &

# 4. Go to sleep - processing happens overnight
```

**Next morning (6am-8am):**

```bash
# Check if completed
python check_processing_status.py YOUR_KEY YOUR_COLLECTION_ID

# If completed:
# ✅ Mark batch as done
# ✅ Prepare next batch for evening upload

# If still processing:
# ⏰ Wait a few more hours
# ⏰ Check again at noon
```

### Tracking Progress

Create a simple tracker:

```
# progress.txt
Batch 01: ✅ COMPLETED (Day 1, 10pm -> Day 2, 6am)
Batch 02: ✅ COMPLETED (Day 2, 10pm -> Day 3, 6am)
Batch 03: ⏳ PROCESSING (started Day 3, 10pm)
Batch 04: ⏸️  PENDING
Batch 05: ⏸️  PENDING
...
```

---

## 🎯 **Alternative Approach: Multiple Collections**

### Instead of One Giant Collection:

Create **multiple smaller Collections** organized by:

1. **By Year:**
   - Collection: "Precedentes 2020"
   - Collection: "Precedentes 2021"
   - Collection: "Precedentes 2022"
   - Collection: "Precedentes 2023"

2. **By Topic:**
   - Collection: "Horas Extras e Jornada"
   - Collection: "Verbas Rescisórias"
   - Collection: "Saúde e Segurança"
   - Collection: "Processo e Competência"

3. **By Court/Region:**
   - Collection: "TRT-10 (DF/TO)"
   - Collection: "TRT-1 (RJ)"

### Advantages:

✅ **Faster processing:** Each Collection smaller (2-3 hours)  
✅ **Better organization:** Easier to search specific topics  
✅ **Lower risk:** Failure in one Collection doesn't affect others  
✅ **Flexible search:** Can search all Collections or specific ones  
✅ **Incremental updates:** Add new years without reprocessing old data

### How to Search Multiple Collections:

```python
# Search across multiple Collections
collections = [
    "collection_2020_id",
    "collection_2021_id",
    "collection_2022_id"
]

for collection_id in collections:
    response = requests.post(
        "https://api.x.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "grok-2-1212",
            "messages": [{"role": "user", "content": query}],
            "tools": [{
                "type": "collection_search",
                "collection_id": collection_id,
                "search_parameters": {"top_k": 3}
            }]
        }
    )
    # Process results
```

---

## 📊 **Comparison of Strategies**

| Strategy | Total Time | Risk Level | Management Effort | Recommended |
|----------|-----------|------------|-------------------|-------------|
| **All at once** | 3 days | 🔴 HIGH | Low | ❌ NO |
| **10 batches** | 10 days | 🟢 LOW | Medium | ✅ YES |
| **20 batches** | 10 days | 🟢 VERY LOW | High | ✅ If cautious |
| **5 batches** | 5 days | 🟡 MEDIUM | Low | ⚠️ Risky |
| **Multiple Collections (by year)** | 5-10 days | 🟢 LOW | Medium | ✅ BEST |

---

## 💡 **FINAL RECOMMENDATION**

### Option 1: Multiple Collections by Year (BEST)

1. Split data by publication year (2020, 2021, 2022, 2023, 2024)
2. Create 5 separate Collections
3. Upload each Collection's data (10-20k sentences each)
4. Processing time per Collection: 3-8 hours
5. Total time: 5 days (1 Collection per day)

**Why best:**
- ✅ Logical organization
- ✅ Faster per-Collection processing
- ✅ Easy to update with new years
- ✅ Better search performance
- ✅ Lower risk

### Option 2: Single Collection with 10 Batches (Conservative)

1. Split JSON into 10 batches of 10k sentences each
2. Upload 1 batch per night (10pm)
3. Verify completion next morning (6am)
4. Total time: 10 days

**Why good:**
- ✅ Single Collection for all data
- ✅ Easy to manage
- ✅ Low risk of failure
- ✅ Overnight processing

---

## 🛠️ **Tools You'll Need**

All tools already created and in your repo:

1. ✅ `split_json_batches.py` (create with code above)
2. ✅ `SmartCollectionUploader.py` (already have)
3. ✅ `check_processing_status.py` (already have)
4. ✅ `estimate_processing_time.py` (already have)

---

## 📧 **Contact xAI for Enterprise Support**

Given your dataset size, consider contacting xAI:

**Email:** support@x.ai or sales@x.ai

**Subject:** Enterprise Collection Processing - 50M Token Dataset

**Body:**
```
Hello xAI Team,

I'm working with a large legal knowledge base (50M tokens, ~100k documents) 
for judicial precedent search using xAI Collections.

Given the dataset size, I'd like to discuss:
1. Best practices for processing large datasets
2. Any rate limits or batch size recommendations
3. Enterprise processing options or priority queuing
4. Estimated processing times and any optimizations available
5. Cost estimates for this scale

Dataset details:
- Total tokens: 50 million
- Documents: ~100,000 legal precedents
- Estimated chunks: ~111,000
- Use case: Legal precedent search for labor law judges

Thank you,
[Your name]
```

---

## ✅ **Summary**

**Your dataset:** 50M tokens = ~3 days continuous processing

**DO NOT:**
- ❌ Upload all 50M tokens at once
- ❌ Expect overnight completion
- ❌ Process without monitoring

**DO:**
- ✅ Split into 10-20 batches
- ✅ OR create multiple Collections by year/topic
- ✅ Upload 1 batch per day (overnight)
- ✅ Monitor each batch completion
- ✅ Use VPN to avoid Cloudflare issues
- ✅ Contact xAI for enterprise support

**Recommended timeline:** 10 days (1 batch per night)

**Best strategy:** Multiple Collections by year (5 Collections, 1 per day)

---

**Created:** 2026-02-10  
**For:** 50M token legal precedent knowledge base  
**Status:** Ready to begin batch processing
