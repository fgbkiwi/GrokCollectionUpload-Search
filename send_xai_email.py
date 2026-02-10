#!/usr/bin/env python3
"""
Send email to xAI support via Gmail.
Requires Gmail app password (not regular password).
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import argparse
import getpass


def create_email_content():
    """Create the email content for xAI support."""
    
    subject = "Enterprise Support Request - Large-Scale Legal Collections Implementation (50M Tokens)"
    
    body = """Hello xAI Support Team,

I am implementing a legal precedent search system using xAI Collections for labor law judges in Brazil, and I'm seeking guidance on best practices for processing a large-scale dataset.

## Project Overview

Use Case: Semantic search for judicial precedents in labor law

Dataset Size:
- Total tokens: ~50 million
- Documents: ~100,000 legal precedents (court decisions)
- Estimated chunks: ~111,000
- Content: Portuguese legal text with YAML metadata
- Document type: Markdown files with structured metadata

Purpose: Enable judges to search historical precedents using semantic search combined with keyword filtering, powered by xAI Collections and Grok models.

## Current Status

Successful Test Completed:
✓ Test upload: 25 documents → 64 chunks
✓ Upload method: REST API via Python
✓ Issues resolved: Cloudflare cf-ipcity header bug (using VPN workaround)
✓ Metadata fields: Successfully configured and uploading
✓ Processing time: 30-60 minutes for test batch (as expected)

Test Collection: Sentenlas_de_Conhecimiento
Collection ID: collection_91555f79-facc-4ea7-a47b-e787ebd76896

Current Issue:
⏳ Test documents (64 files) have been in "processing" status for over 30 minutes
- Documents visible in Console but not transitioning to "completed" status
- Question: Is this processing duration normal for 64 chunks, or should I be concerned?

## Questions for Enterprise Implementation

Given the dataset size, I have several questions before proceeding with full-scale upload:

### 1. Processing Time & Capacity
- Estimated processing time: ~72 hours for 111K chunks (based on 1.5s/chunk)
- Question: Is this estimate accurate for your infrastructure?
- Question: Are there any optimizations available for large batch processing?
- Question: What is the maximum recommended upload size per batch?

### 2. Batching Strategy
I'm considering two approaches:

Option A: Single Collection with 10 sequential batches
- 10 batches × 10K sentences each × ~7-8 hours per batch = 10 days total

Option B: Multiple Collections organized by year (5 Collections: 2020-2024)
- Better organization for temporal searches
- Faster per-Collection processing (3-8 hours each)

Question: Which approach do you recommend for optimal performance and scalability?

### 3. Rate Limits & Quotas
- Question: Are there rate limits for document uploads or embedding generation?
- Question: Are there quotas for total chunks per Collection?
- Question: Should I implement delays between batch uploads?

### 4. Processing Monitoring & Current Issue
Current Situation:
- Test upload of 64 documents completed successfully via API
- All documents showing "processing" status in Console for 30+ minutes
- No error messages visible
- Cannot yet perform searches on the Collection

Questions:
- Question: What is the normal processing time for 64 chunks (~1KB each)?
- Question: Is there an API endpoint to check document processing status programmatically?
- Question: At what point should I be concerned about processing timeouts?
- Question: For the full 111K chunk dataset, what processing time should I realistically expect?
- Question: If documents remain in "processing" status for extended periods (>2 hours), what should I do?
- Question: Is there a way to monitor processing progress or queue position?

### 5. Known Issues & Workarounds
During testing, I encountered:

✓ Resolved: Cloudflare cf-ipcity non-ASCII header rejection (gRPC error 500)
  - Workaround: Using VPN to ensure ASCII-only geolocation headers
  - Root cause: Portuguese city names with non-ASCII characters (e.g., "São Paulo")
  - Suggestion: Consider sanitizing cf-* headers on server-side for non-US locations

✓ Resolved: Unknown field errors when metadata not pre-defined in Collection schema
  - Workaround: Created auto-filtering uploader that detects Collection schema

Question: Are these known issues? Are there official workarounds or fixes planned?

### 6. Enterprise Pricing & Support
- Question: What is the pricing model for this scale (111K chunks)?
- Question: Are there enterprise plans with priority processing or dedicated support?
- Question: Is there an official Python SDK recommendation for large uploads?

## Technical Environment

Client:
- Platform: Windows + Python 3.x
- Location: Brazil (Portuguese locale, non-ASCII city names)
- Network: Using VPN (US/UK endpoints) to avoid Cloudflare header issues
- Upload tool: Custom Python uploader with auto-metadata filtering

Implementation:
- Direct REST API calls to https://api.x.ai/v1/collections/{collection_id}/documents
- Multipart form data for document content
- JSON metadata with fields: categoria, reclamada, numero_processo, data_publicacao, tipo_acao, keywords

## Timeline

Target: Complete full dataset upload within 2-3 weeks
Flexibility: Can adjust batching strategy based on your recommendations

## Request

I would appreciate:
1. Validation of my processing time estimates
2. Recommendation on batching strategy (single vs. multiple Collections)
3. Confirmation of any rate limits or quotas
4. Best practices for monitoring large uploads
5. Information on enterprise pricing for this scale
6. Any optimizations or priority processing options available

## Additional Information

Console Access: https://console.x.ai/team/aafa6ee3-2bc0-4564-80b1-0d0ed8299862/collections/collection_91555f79-facc-4ea7-a47b-e787ebd76896

GitHub Repository (Tools Created): https://github.com/fgbkiwi/GrokCollectionUpload-Search
- Custom uploaders with Cloudflare workarounds
- Processing time estimation tools
- Batch splitting utilities
- Status monitoring scripts

I'm happy to provide additional technical details or debug information if helpful.

Thank you for your time and assistance with this large-scale implementation. I look forward to your guidance.

Best regards,
"""
    
    return subject, body


def send_email_via_gmail(
    sender_email: str,
    sender_password: str,
    recipient_email: str,
    cc_email: str = None,
    subject: str = None,
    body: str = None,
    sender_name: str = None
):
    """
    Send email via Gmail SMTP.
    
    Args:
        sender_email: Your Gmail address
        sender_password: Gmail app password (not regular password)
        recipient_email: Recipient email (support@x.ai)
        cc_email: CC email (sales@x.ai)
        subject: Email subject
        body: Email body
        sender_name: Your name for signature
    """
    
    # Create message
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    if cc_email:
        msg['Cc'] = cc_email
    msg['Subject'] = subject
    
    # Add signature to body
    if sender_name:
        body += f"\n\n{sender_name}"
    
    # Attach body
    msg.attach(MIMEText(body, 'plain', 'utf-8'))
    
    # Send email
    try:
        print("📧 Connecting to Gmail SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        
        print("🔐 Authenticating...")
        server.login(sender_email, sender_password)
        
        print("📤 Sending email...")
        recipients = [recipient_email]
        if cc_email:
            recipients.append(cc_email)
        
        text = msg.as_string()
        server.sendmail(sender_email, recipients, text)
        
        server.quit()
        
        print("✅ Email sent successfully!")
        print(f"   To: {recipient_email}")
        if cc_email:
            print(f"   CC: {cc_email}")
        print(f"   Subject: {subject}")
        
        return True
    
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Send email to xAI support via Gmail",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Setup Gmail App Password:
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification (if not already)
3. Go to https://myaccount.google.com/apppasswords
4. Create app password for "Mail"
5. Use that password (not your regular Gmail password)

Usage:
    python send_xai_email.py --email your@gmail.com --name "Your Name"
    
    # With CC to sales
    python send_xai_email.py --email your@gmail.com --name "Your Name" --cc-sales
        """
    )
    
    parser.add_argument("--email", required=True, help="Your Gmail address")
    parser.add_argument("--name", required=True, help="Your name for email signature")
    parser.add_argument("--cc-sales", action="store_true", help="CC sales@x.ai")
    parser.add_argument("--dry-run", action="store_true", help="Print email without sending")
    
    args = parser.parse_args()
    
    # Get email content
    subject, body = create_email_content()
    
    # Recipients
    to_email = "support@x.ai"
    cc_email = "sales@x.ai" if args.cc_sales else None
    
    # Print preview
    print("=" * 70)
    print("EMAIL PREVIEW")
    print("=" * 70)
    print(f"From: {args.email}")
    print(f"To: {to_email}")
    if cc_email:
        print(f"CC: {cc_email}")
    print(f"Subject: {subject}")
    print()
    print("Body:")
    print("-" * 70)
    print(body)
    print()
    print(f"Signature: {args.name}")
    print("=" * 70)
    print()
    
    if args.dry_run:
        print("🔍 Dry run mode - email not sent")
        return 0
    
    # Confirm sending
    response = input("Send this email? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        print("❌ Email not sent")
        return 1
    
    # Get password
    print()
    print("📧 Gmail App Password Required")
    print("   (Not your regular Gmail password)")
    print("   Setup: https://myaccount.google.com/apppasswords")
    print()
    password = getpass.getpass("Enter Gmail app password: ")
    
    if not password:
        print("❌ Password required")
        return 1
    
    # Send email
    success = send_email_via_gmail(
        sender_email=args.email,
        sender_password=password,
        recipient_email=to_email,
        cc_email=cc_email,
        subject=subject,
        body=body,
        sender_name=args.name
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
