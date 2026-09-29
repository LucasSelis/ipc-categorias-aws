# Permisos mínimos: la Lambda puede escribir sus propios logs y un único prefijo de S3. Nada más:
# no lee ni borra nada, no toca otros buckets, no tiene permisos de administración.
resource "aws_iam_role" "lambda" {
  name = "${var.nombre_proyecto}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "lambda" {
  name = "escribir-raw-y-logs"
  role = aws_iam_role.lambda.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid      = "EscribirElCsvDeIpc"
        Effect   = "Allow"
        Action   = ["s3:PutObject"]
        Resource = "${aws_s3_bucket.datos.arn}/raw/ipc_categorias/*"
      },
      {
        Sid      = "LogsPropios"
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda.arn}:*"
      }
    ]
  })
}
