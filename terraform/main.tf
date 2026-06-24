# 1. VARIABLES
variable "region" { default = "ap-southeast-1" }
variable "bucket" { default = "lks-data-lake-tema01" }
variable "table" { default = "lks-transaction" }

# 2. PROVIDER
provider "aws" { region = var.region }

# 3. S3 BUCKET
resource "aws_s3_bucket" "dl" { bucket = var.bucket }

resource "aws_s3_bucket_versioning" "dl" {
    bucket = aws_s3_bucket.dl.id
    versioning_configuration { status = "Enabled" }
}

# 4. DYNAMODB
resource "aws_dynamodb_table" "tx" {
    name         = var.table
    billing_mode = "PAY_PER_REQUEST"
    hash_key     = "transaction_id"

    attribute {
        name = "transaction_id"
        type = "S"
    }
}