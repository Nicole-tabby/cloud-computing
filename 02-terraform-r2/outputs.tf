output "bucket_name" {
  description = "Name of the created R2 bucket"
  value       = cloudflare_r2_bucket.student_bucket.name
}

output "object_key" {
  description = "Key (filename) of the uploaded object inside the bucket"
  value       = aws_s3_object.uploaded_object.key
}

output "next_step_get_public_url" {
  description = "Run this command after apply to retrieve the public r2.dev domain"
  value       = "curl -X GET \"https://api.cloudflare.com/client/v4/accounts/${var.cloudflare_account_id}/r2/buckets/${cloudflare_r2_bucket.student_bucket.name}/domains/managed\" -H \"Authorization: Bearer YOUR_API_TOKEN\""
}
