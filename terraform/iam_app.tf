# Usuario de solo lectura para el Explorador SQL público (la app de Streamlit). No puede escribir,
# borrar ni crear nada en el dato ni en el catálogo: solo ejecutar consultas y leer sus resultados.
#
# No se crea la access key acá a propósito: si Terraform la generara, quedaría en el state (que
# puede terminar en git, en un log, en cualquier lado). La genera Lucas a mano en la consola de
# AWS, para ESTE usuario, y la carga como secreto en Streamlit Cloud. Nunca pasa por este repo.
resource "aws_iam_user" "app_sql" {
  name = "${var.nombre_proyecto}-app-sql"
}

resource "aws_iam_user_policy" "app_sql" {
  name = "solo-lectura-athena"
  user = aws_iam_user.app_sql.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CorrerConsultasEnElWorkgroupDelProyecto"
        Effect = "Allow"
        Action = [
          "athena:StartQueryExecution",
          "athena:GetQueryExecution",
          "athena:GetQueryResults",
          "athena:StopQueryExecution",
        ]
        Resource = aws_athena_workgroup.ipc.arn
      },
      {
        Sid      = "LeerElCatalogoDeGlue"
        Effect   = "Allow"
        Action   = ["glue:GetDatabase", "glue:GetTable", "glue:GetTables", "glue:GetPartitions"]
        Resource = "*" # Glue no permite acotar estas acciones a un ARN de tabla específico
      },
      {
        Sid      = "LeerElDatoCrudo"
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:GetBucketLocation", "s3:ListBucket"]
        Resource = [aws_s3_bucket.datos.arn, "${aws_s3_bucket.datos.arn}/raw/*"]
      },
      {
        # Athena necesita poder escribir el resultado de cada consulta; se lo permito solo en
        # su propio prefijo, que además se auto-borra a los 3 días (ver s3.tf).
        Sid      = "EscribirSoloLosResultadosDeConsulta"
        Effect   = "Allow"
        Action   = ["s3:PutObject", "s3:GetObject"]
        Resource = "${aws_s3_bucket.datos.arn}/athena-results/*"
      }
    ]
  })
}
