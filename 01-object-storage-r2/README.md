# Cloud Object Storage & API Access — Assignment

Cricket match data (`match1.json`, `match2.json`) stored and retrieved across
three providers, using both a REST-based SDK-less approach and boto3.

## Files

| File | Purpose |
|---|---|
| `match1.json`, `match2.json` | Sample cricket match statistics (the objects being stored) |
| `supabase_storage.py` | Part A/B — upload/download/list/delete via Supabase Storage REST API |
| `r2_storage.py` | Extra Task — upload/download/list/delete via **Cloudflare R2** using **boto3** |
| `aws_s3_storage.py` | Part C — upload/download/list/delete via **AWS S3** using **boto3** |
| `test_with_mock.py` | Proves the boto3 logic works end-to-end using a mocked S3 (moto) — run this to see it work without any real account |

## How each provider was set up

### 1. Supabase (Part A)
1. Created a free account at supabase.com — no card required.
2. New project → Postgres DB auto-provisioned.
3. Storage tab → new bucket named `cricket-data`.
4. Uploaded `match1.json` / `match2.json` as sample objects.
5. Project Settings → API → copied `SUPABASE_URL` and the service role `SUPABASE_KEY`.

### 2. Cloudflare R2 (the boto3 task from the "How One Can Use APIs" section)
1. Free Cloudflare account — no card required.
2. R2 → Create bucket → `cricket-data`.
3. R2 → Manage API Tokens → created a token with Object Read & Write, which
   yields an Access Key ID, Secret Access Key, and Account ID.
4. R2's endpoint is `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` — same S3
   API as AWS, just a different `endpoint_url` in the boto3 client.

### 3. AWS S3 (Part C comparison)
1. IAM user with S3 access, generated an Access Key ID + Secret Access Key.
2. S3 → Create bucket (globally unique name).
3. Note: unlike the other four options in the assignment's comparison table,
   AWS's free tier does require a card at signup — included here only
   because Part C explicitly asks for the boto3-vs-Supabase comparison.

## Running it

Each script reads credentials from environment variables (never hardcode
secrets in code). Example for R2:

```bash
export R2_ACCOUNT_ID="..."
export R2_ACCESS_KEY_ID="..."
export R2_SECRET_ACCESS_KEY="..."
python3 r2_storage.py
```

Without real credentials, run `test_with_mock.py` instead — it exercises the
identical boto3 calls (`upload_file`, `download_file`, `list_objects_v2`,
`delete_object`) against a mocked S3 backend and prints a verified roundtrip:

```
[Create] Bucket 'cricket-data-demo' created (mocked)
[Upload] match1.json, match2.json uploaded
[List] 2 file(s) in bucket:
   - match1.json (473 bytes)
   - match2.json (481 bytes)
[Download] match1.json -> test_downloaded_match1.json
[Verify] Roundtrip OK — retrieved match_id: M1001
[Delete] match2.json removed, 1 file(s) remain
```

## Comparing the two API styles (Part C)

**Supabase (REST, no SDK)**
```python
res = requests.post(
    f"{SUPABASE_URL}/storage/v1/object/cricket-data/match1.json",
    headers=headers, data=f
)
```
- You build the HTTP request yourself (URL, headers, method).
- Auth is a bearer token + apikey header on every call.
- Good when you want zero extra dependencies and are already using Postgres.

**AWS S3 / Cloudflare R2 (boto3 SDK)**
```python
s3.upload_file("match1.json", bucket, "match1.json")
s3.download_file(bucket, "match1.json", "local_match1.json")
```
- The SDK handles request signing (SigV4), retries, and multipart uploads for
  large files automatically.
- Same boto3 code works for both S3 and R2 — only `endpoint_url` and
  `region_name` change. This is the point of R2 being "S3-compatible."
- Better for anything beyond simple upload/download (versioning, lifecycle
  rules, presigned URLs, multipart).

## Learning outcomes covered
- **Object storage concepts** — bucket, object/key, REST vs SDK access.
- **Supabase REST API vs AWS boto3 SDK** — compared directly above.
- **Secure API authentication** — all credentials loaded from environment
  variables, never hardcoded.
- **Mini-project** — full upload + list + download + delete cycle, verified
  working end-to-end via the mocked test.
