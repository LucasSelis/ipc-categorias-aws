# El INDEC publica el IPC entre el día 12 y el 15 de cada mes. Se corre el 18 a las 13:00 UTC
# (10:00 en Argentina) para dar margen y no depender de una fecha exacta que a veces se corre.
resource "aws_scheduler_schedule" "mensual" {
  name       = "${var.nombre_proyecto}-mensual"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression = "cron(0 13 18 * ? *)"

  target {
    arn      = aws_lambda_function.ingesta.arn
    role_arn = aws_iam_role.scheduler.arn
  }
}

resource "aws_iam_role" "scheduler" {
  name = "${var.nombre_proyecto}-scheduler"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "invocar-solo-esta-lambda"
  role = aws_iam_role.scheduler.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = "lambda:InvokeFunction"
      Resource = aws_lambda_function.ingesta.arn
    }]
  })
}
