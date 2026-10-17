resource "aws_s3_bucket" "tv" {
  bucket = var.tv_bucket_name != "" ? var.tv_bucket_name : "${var.name}-tv-${data.aws_caller_identity.current.account_id}"
}

data "aws_caller_identity" "current" {}

resource "aws_s3_bucket_public_access_block" "tv" {
  bucket                  = aws_s3_bucket.tv.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_cloudfront_origin_access_control" "tv" {
  name                              = "${var.name}-tv"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "tv" {
  enabled             = true
  default_root_object = "index.html"

  origin {
    domain_name              = aws_s3_bucket.tv.bucket_regional_domain_name
    origin_id                = "tv-s3"
    origin_access_control_id = aws_cloudfront_origin_access_control.tv.id
  }

  default_cache_behavior {
    target_origin_id       = "tv-s3"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD"]
    cached_methods         = ["GET", "HEAD"]
    forwarded_values {
      query_string = false
      cookies { forward = "none" }
    }
  }

  restrictions {
    geo_restriction { restriction_type = "none" }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}

data "aws_iam_policy_document" "tv" {
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.tv.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.tv.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "tv" {
  bucket = aws_s3_bucket.tv.id
  policy = data.aws_iam_policy_document.tv.json
}
