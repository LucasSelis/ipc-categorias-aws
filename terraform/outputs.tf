output "bucket" {
  value = aws_s3_bucket.datos.bucket
}

output "lambda" {
  value = aws_lambda_function.ingesta.function_name
}

output "base_athena" {
  value = aws_glue_catalog_database.ipc.name
}

output "workgroup_athena" {
  value = aws_athena_workgroup.ipc.name
}

output "usuario_iam_de_la_app" {
  value       = aws_iam_user.app_sql.name
  description = "Generale la access key a mano en la consola de AWS (IAM > Usuarios > este usuario > Claves de acceso)."
}
