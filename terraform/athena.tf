# bytes_scanned_cutoff_per_query es la red de seguridad de costo: con datos de menos de 100 KB
# nunca se debería acercar a este tope, pero corta cualquier consulta rara antes de que escale.
resource "aws_athena_workgroup" "ipc" {
  name = var.nombre_proyecto

  configuration {
    enforce_workgroup_configuration    = true
    publish_cloudwatch_metrics_enabled = true
    bytes_scanned_cutoff_per_query     = 104857600 # 100 MB

    result_configuration {
      output_location = "s3://${aws_s3_bucket.datos.bucket}/athena-results/"
    }
  }
}
