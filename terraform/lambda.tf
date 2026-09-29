# Empaqueta ingesta/src tal cual (sin capas ni dependencias: solo usa boto3, que ya viene en el runtime de Lambda).
data "archive_file" "lambda" {
  type        = "zip"
  source_dir  = "${path.module}/../ingesta/src"
  output_path = "${path.module}/build/ingesta.zip"
}

resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.nombre_proyecto}-ingesta"
  retention_in_days = 14 # sin esto los logs quedan para siempre y suman costo de guardado
}

resource "aws_lambda_function" "ingesta" {
  function_name    = "${var.nombre_proyecto}-ingesta"
  role             = aws_iam_role.lambda.arn
  handler          = "handler.handler"
  runtime          = "python3.12"
  timeout          = 30
  memory_size      = 128 # el trabajo es liviano: bajar 13 series y escribir un CSV de menos de 100 KB
  filename         = data.archive_file.lambda.output_path
  source_code_hash = data.archive_file.lambda.output_base64sha256

  environment {
    variables = {
      BUCKET = aws_s3_bucket.datos.bucket
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda]
}
