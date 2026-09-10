terraform {
  required_version = ">= 1.5.0"

  required_providers {
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 4.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Cloudflare provider - manages the R2 bucket itself
provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

# AWS provider, pointed at R2's S3-compatible endpoint - used to upload
# the actual object, since R2 speaks the S3 API for object operations.
provider "aws" {
  region     = "auto"
  access_key = var.r2_access_key_id
  secret_key = var.r2_secret_access_key

  skip_credentials_validation = true
  skip_region_validation      = true
  skip_requesting_account_id  = true

  endpoints {
    s3 = "https://${var.cloudflare_account_id}.r2.cloudflarestorage.com"
  }
}
