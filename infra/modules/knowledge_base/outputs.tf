output "knowledge_base_id" {
  description = "ID of the knowledge base (used by Retrieve and by the ingestion script)."
  value       = aws_bedrockagent_knowledge_base.this.id
}

output "knowledge_base_arn" {
  description = "ARN of the knowledge base (the only resource kb_retrieve may query)."
  value       = aws_bedrockagent_knowledge_base.this.arn
}

output "data_source_id" {
  description = "ID of the S3 data source (used by the ingestion script)."
  value       = aws_bedrockagent_data_source.docs.data_source_id
}

output "docs_bucket" {
  description = "S3 bucket holding the knowledge documents."
  value       = aws_s3_bucket.docs.id
}

output "vector_bucket" {
  description = "S3 Vectors bucket holding the search index."
  value       = aws_s3vectors_vector_bucket.this.vector_bucket_name
}

output "document_count" {
  description = "How many documents were uploaded for ingestion."
  value       = length(aws_s3_object.doc)
}
