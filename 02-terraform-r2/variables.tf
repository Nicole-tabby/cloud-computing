variable "cloudflare_api_token" {
  description = "Cloudflare API token with R2 edit permissions"
  type        = string
  sensitive   = true
}

variable "cloudflare_account_id" {
  description = "Cloudflare account ID"
  type        = string
}

variable "r2_access_key_id" {
  description = "R2 S3-compatible Access Key ID"
  type        = string
  sensitive   = true
}

variable "r2_secret_access_key" {
  description = "R2 S3-compatible Secret Access Key"
  type        = string
  sensitive   = true
}

variable "student_id" {
  description = "Student registration number, used in bucket and object naming"
  type        = string
  default     = "24ug00216"
}

variable "object_file_path" {
  description = "Local path to the file that will be uploaded to the bucket"
  type        = string
  default     = "./upload/sample-report.pdf"
}

variable "object_content_type" {
  description = "MIME type of the uploaded object (e.g. application/pdf, image/jpeg, video/mp4)"
  type        = string
  default     = "application/pdf"
}
