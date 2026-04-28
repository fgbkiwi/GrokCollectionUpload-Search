#!/usr/bin/env python3
"""
Check xAI Collection Schema
Shows which metadata fields are defined in your Collection.
"""
import requests
import json
import sys
import argparse


def check_collection_schema(management_key: str, collection_id: str):
    """Fetch and display Collection schema."""
    
    print("🔍 Checking xAI Collection Schema")
    print("=" * 70)
    
    try:
        response = requests.get(
            f"https://api.x.ai/v1/collections/{collection_id}",
            headers={"Authorization": f"Bearer {management_key}"},
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        
        print(f"\n✅ Collection found!")
        print(f"   Name: {data.get('name', 'N/A')}")
        print(f"   ID: {collection_id}")
        print(f"   Created: {data.get('created_at', 'N/A')}")
        
        # Check for field definitions
        field_defs = data.get('field_definitions', {})
        
        if field_defs:
            print(f"\n📋 Defined Metadata Fields ({len(field_defs)}):")
            print("-" * 70)
            for field_name, field_info in field_defs.items():
                field_type = field_info if isinstance(field_info, str) else field_info.get('type', 'unknown')
                print(f"   ✅ {field_name:30s} ({field_type})")
        else:
            print("\n⚠️  No metadata fields defined yet")
            print("   You can use the Collection without metadata, or add fields in xAI Console")
        
        # Check what's missing
        recommended_fields = {
            'categoria', 'reclamada', 'numero_processo', 
            'data_publicacao', 'tipo_acao', 'keywords', 'original_filename'
        }
        
        defined_fields = set(field_defs.keys())
        missing_fields = recommended_fields - defined_fields
        
        if missing_fields:
            print(f"\n⚠️  Recommended Fields Missing:")
            print("-" * 70)
            for field in sorted(missing_fields):
                if field == 'keywords':
                    print(f"   ❌ {field:30s} (array or text) - For hybrid search")
                elif field == 'original_filename':
                    print(f"   ❌ {field:30s} (string) - Track source files")
                else:
                    print(f"   ❌ {field:30s} (string) - Basic metadata")
        
        # Check Collection settings
        print(f"\n⚙️  Collection Settings:")
        print("-" * 70)
        print(f"   Chunk Size: {data.get('chunk_size', 'N/A')}")
        print(f"   Chunk Overlap: {data.get('chunk_overlap', 'N/A')}")
        print(f"   Embedding Model: {data.get('embedding_model', 'N/A')}")
        
        # Provide recommendations
        print(f"\n💡 Recommendations:")
        print("=" * 70)
        
        if missing_fields:
            print("\n1. Add Missing Fields in xAI Console:")
            print("   → Go to: https://console.x.ai/")
            print(f"   → Open Collection: {data.get('name')}")
            print("   → Settings → Metadata Fields → Add New Field")
            print("\n   Add these fields:")
            
            for field in sorted(missing_fields):
                if field == 'keywords':
                    print(f"      • {field} (type: array or text, searchable: yes)")
                elif field == 'original_filename':
                    print(f"      • {field} (type: string, searchable: no)")
                else:
                    print(f"      • {field} (type: string, searchable: optional)")
        else:
            print("✅ All recommended fields are defined!")
            print("   Your Collection is properly configured for uploads")
        
        print("\n2. Or modify your uploader to only use defined fields")
        print("   → Remove 'keywords' and 'original_filename' from metadata")
        
        print("\n" + "=" * 70)
        
        # Return status
        return len(missing_fields) == 0
    
    except requests.exceptions.HTTPError as e:
        print(f"\n❌ HTTP Error: {e}")
        if e.response.status_code == 401:
            print("   → Check your Management Key")
        elif e.response.status_code == 404:
            print("   → Check your Collection ID")
        return False
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Check xAI Collection metadata field definitions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python check_collection_schema.py <management_key> <collection_id>
    python check_collection_schema.py xai-mgmt-abc123 col_xyz789
        """
    )
    
    parser.add_argument("management_key", help="Your xAI Management Key")
    parser.add_argument("collection_id", help="Collection ID to check")
    
    args = parser.parse_args()
    
    success = check_collection_schema(args.management_key, args.collection_id)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
