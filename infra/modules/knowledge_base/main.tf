# The knowledge base: short summaries of AWS documentation that the agent can search by meaning.
#
#   S3 bucket (the documents) --ingest--> Bedrock Knowledge Base --embeds with--> Titan V2
#                                                  |
#                                                  +--stores vectors in--> S3 Vectors index
#
# Nothing here bills while idle: storage is a few KB and every other part is pay-per-use.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  account_id          = data.aws_caller_identity.current.account_id
  region              = data.aws_region.current.region
  docs_bucket_name    = "${var.project}-kb-docs-${local.account_id}" # bucket names are global, so make it unique
  embedding_model_arn = "arn:aws:bedrock:${local.region}::foundation-model/${var.embedding_model_id}"
  doc_files           = fileset(var.docs_dir, "*.md")
  metadata_files      = fileset(var.docs_dir, "*.md.metadata.json")
}

# --- The documents -----------------------------------------------------------------------------

resource "aws_s3_bucket" "docs" {
  bucket        = local.docs_bucket_name
  force_destroy = true # sandbox: lets `make destroy` remove the bucket with its files in it
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256" # S3-managed keys: free, and no KMS key to grant access to
    }
  }
}

data "aws_iam_policy_document" "docs_bucket" {
  # Refuse any request that is not encrypted in transit.
  statement {
    sid       = "DenyInsecureTransport"
    effect    = "Deny"
    actions   = ["s3:*"]
    resources = [aws_s3_bucket.docs.arn, "${aws_s3_bucket.docs.arn}/*"]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "docs" {
  bucket = aws_s3_bucket.docs.id
  policy = data.aws_iam_policy_document.docs_bucket.json

  depends_on = [aws_s3_bucket_public_access_block.docs]
}

resource "aws_s3_object" "doc" {
  for_each = local.doc_files

  bucket       = aws_s3_bucket.docs.id
  key          = "docs/${each.value}"
  source       = "${var.docs_dir}/${each.value}"
  etag         = filemd5("${var.docs_dir}/${each.value}")
  content_type = "text/markdown"
}

# Bedrock reads <document>.metadata.json next to each document and returns those attributes
# (title, topic, source_url ...) with every retrieved passage, which is how citations work.
resource "aws_s3_object" "doc_metadata" {
  for_each = local.metadata_files

  bucket       = aws_s3_bucket.docs.id
  key          = "docs/${each.value}"
  source       = "${var.docs_dir}/${each.value}"
  etag         = filemd5("${var.docs_dir}/${each.value}")
  content_type = "application/json"
}

# --- The search index (S3 Vectors) -------------------------------------------------------------

resource "aws_s3vectors_vector_bucket" "this" {
  vector_bucket_name = "${var.project}-vectors"
  force_destroy      = true # sandbox: lets `make destroy` remove the bucket and its index
}

resource "aws_s3vectors_index" "kb" {
  index_name         = "kb-index"
  vector_bucket_name = aws_s3vectors_vector_bucket.this.vector_bucket_name

  data_type       = "float32" # S3 Vectors stores floating-point vectors only
  dimension       = var.embedding_dimensions
  distance_metric = "cosine" # similarity by direction; the usual choice for text embeddings

  # Bedrock stores each chunk's text and its own bookkeeping as metadata. AWS requires these two
  # keys to be non-filterable so they do not count against the filterable-metadata size limit.
  metadata_configuration {
    non_filterable_metadata_keys = ["AMAZON_BEDROCK_TEXT", "AMAZON_BEDROCK_METADATA"]
  }
}

# --- The service role Bedrock assumes while building and querying the knowledge base ------------

data "aws_iam_policy_document" "kb_trust" {
  # Only the Bedrock service may assume this role, only on behalf of this account, and only for
  # a knowledge base in this account and Region. (The wildcard is on the knowledge-base ID because
  # the role has to exist before the knowledge base does.)
  statement {
    sid     = "BedrockKnowledgeBasesMayAssume"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:aws:bedrock:${local.region}:${local.account_id}:knowledge-base/*"]
    }
  }
}

resource "aws_iam_role" "kb" {
  name               = "${var.project}-kb-role"
  description        = "Assumed by Amazon Bedrock to read the docs bucket, embed text and write the vector index."
  assume_role_policy = data.aws_iam_policy_document.kb_trust.json
}

data "aws_iam_policy_document" "kb_permissions" {
  # Needed to find the documents to ingest. Listing is allowed on this one bucket only, and only
  # while the bucket belongs to this account.
  statement {
    sid       = "ListDocsBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.docs.arn]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [local.account_id]
    }
  }

  # Needed to read each document. Limited to the docs/ prefix (the data source's inclusion prefix).
  # Read only: this role cannot change or delete documents.
  statement {
    sid       = "ReadDocs"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.docs.arn}/docs/*"]

    condition {
      test     = "StringEquals"
      variable = "aws:ResourceAccount"
      values   = [local.account_id]
    }
  }

  # Needed to turn text into vectors. One action on one model: Titan Text Embeddings V2.
  # (AWS's example also lists bedrock:ListFoundationModels on "*"; we leave it out as unneeded for
  # an embedding model we name explicitly.)
  statement {
    sid       = "EmbedWithTitanV2"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_model_arn]
  }

  # Needed to store and search the vectors. The five actions AWS documents for a knowledge base,
  # on this one index and nothing else.
  statement {
    sid = "UseTheVectorIndex"
    actions = [
      "s3vectors:PutVectors",    # write vectors during ingestion
      "s3vectors:GetVectors",    # read vectors back
      "s3vectors:DeleteVectors", # remove vectors of deleted or changed documents
      "s3vectors:QueryVectors",  # similarity search when someone retrieves
      "s3vectors:GetIndex",      # read the index's settings
    ]
    resources = [aws_s3vectors_index.kb.index_arn]
  }
}

resource "aws_iam_role_policy" "kb" {
  name   = "${var.project}-kb-permissions"
  role   = aws_iam_role.kb.id
  policy = data.aws_iam_policy_document.kb_permissions.json
}

# --- The knowledge base ------------------------------------------------------------------------

resource "aws_bedrockagent_knowledge_base" "this" {
  name        = "${var.project}-kb"
  description = "Short summaries of AWS documentation for pre-sales discovery briefs."
  role_arn    = aws_iam_role.kb.arn

  knowledge_base_configuration {
    type = "VECTOR"

    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_model_arn

      embedding_model_configuration {
        bedrock_embedding_model_configuration {
          dimensions          = var.embedding_dimensions
          embedding_data_type = "FLOAT32"
        }
      }
    }
  }

  storage_configuration {
    type = "S3_VECTORS"

    s3_vectors_configuration {
      index_arn = aws_s3vectors_index.kb.index_arn
    }
  }

  # Bedrock checks the role's permissions when the knowledge base is created.
  depends_on = [aws_iam_role_policy.kb]
}

resource "aws_bedrockagent_data_source" "docs" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.this.id
  name              = "${var.project}-docs"

  # Removing the data source removes its vectors too, so `make destroy` leaves nothing behind.
  data_deletion_policy = "DELETE"

  data_source_configuration {
    type = "S3"

    s3_configuration {
      bucket_arn         = aws_s3_bucket.docs.arn
      inclusion_prefixes = ["docs/"]
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE" # simplest option; hierarchical chunking can exceed S3 Vectors' metadata limit

      fixed_size_chunking_configuration {
        max_tokens         = var.chunk_max_tokens
        overlap_percentage = var.chunk_overlap_percent
      }
    }
  }

  # The documents must be in the bucket before anyone starts an ingestion job.
  depends_on = [aws_s3_object.doc, aws_s3_object.doc_metadata]
}
