# Bucket único para todo: datos crudos + resultados de consultas de Athena, en prefijos separados.
# Un solo bucket simplifica el ejemplo; en un proyecto real con más tráfico convendría separarlos
# (los resultados de Athena son basura de corta vida, el dato crudo no).
resource "aws_s3_bucket" "datos" {
  bucket = "${var.nombre_proyecto}-${data.aws_caller_identity.actual.account_id}"
}

resource "aws_s3_bucket_versioning" "datos" {
  bucket = aws_s3_bucket.datos.id
  versioning_configuration {
    status = "Enabled" # da un historial barato de cada carga, sin manejar particiones a mano
  }
}

resource "aws_s3_bucket_public_access_block" "datos" {
  bucket                  = aws_s3_bucket.datos.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "datos" {
  bucket = aws_s3_bucket.datos.id

  rule {
    id     = "borrar-versiones-viejas-del-dato-crudo"
    status = "Enabled"
    filter { prefix = "raw/" }
    noncurrent_version_expiration {
      noncurrent_days = 180
    }
  }

  rule {
    id     = "los-resultados-de-athena-son-descartables"
    status = "Enabled"
    filter { prefix = "athena-results/" }
    expiration {
      days = 3
    }
  }
}

data "aws_caller_identity" "actual" {}
