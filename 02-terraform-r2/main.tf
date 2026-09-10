# -----------------------------------------------------------------------
# 1. Create the R2 bucket (name includes student ID as required)
# -----------------------------------------------------------------------
resource "cloudflare_r2_bucket" "student_bucket" {
  account_id = var.cloudflare_account_id
  name       = "nicole-tabby-${var.student_id}"
  location   = "APAC"
}

# -----------------------------------------------------------------------
# 2. Upload the object into the bucket (object key also includes the ID)
#    Works for any file type: PDF, JPG, XLSX, DOCX, MP4, etc. -
#    just change object_file_path and object_content_type in terraform.tfvars
# -----------------------------------------------------------------------
resource "aws_s3_object" "uploaded_object" {
  bucket       = cloudflare_r2_bucket.student_bucket.name
  key          = "${var.student_id}-shared-object${lower(regex("\\.[^.]+$", var.object_file_path))}"
  source       = var.object_file_path
  etag         = filemd5(var.object_file_path)
  content_type = var.object_content_type
}

# -----------------------------------------------------------------------



