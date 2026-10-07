variable "project" {
  description = "Short project slug used in resource names."
  type        = string
}

variable "docs_dir" {
  description = "Directory holding the knowledge documents (*.md) and their metadata (*.md.metadata.json)."
  type        = string
}

variable "embedding_model_id" {
  description = "Bedrock embedding model that turns text into vectors."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dimensions" {
  description = "Vector length. Titan Text Embeddings V2 supports 1024, 512 and 256; the vector index must use the same number."
  type        = number
  default     = 1024

  validation {
    condition     = contains([256, 512, 1024], var.embedding_dimensions)
    error_message = "Titan Text Embeddings V2 supports 256, 512 or 1024 dimensions."
  }
}

variable "chunk_max_tokens" {
  description = "Largest chunk a document is split into. Our documents are about 200 tokens, so each stays whole."
  type        = number
  default     = 512
}

variable "chunk_overlap_percent" {
  description = "How much consecutive chunks overlap, so a sentence cut at a boundary is still found."
  type        = number
  default     = 10
}
