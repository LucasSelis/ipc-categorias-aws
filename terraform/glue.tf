# Tabla externa fija (sin crawler): el esquema del CSV es conocido y estable, así que no hace
# falta pagar ni mantener un crawler para algo que no cambia.
resource "aws_glue_catalog_database" "ipc" {
  name = replace(var.nombre_proyecto, "-", "_")
}

resource "aws_glue_catalog_table" "ipc_categorias" {
  name          = "ipc_categorias"
  database_name = aws_glue_catalog_database.ipc.name
  table_type    = "EXTERNAL_TABLE"

  parameters = {
    "classification"         = "csv"
    "skip.header.line.count" = "1"
    "EXTERNAL"               = "TRUE"
  }

  storage_descriptor {
    location      = "s3://${aws_s3_bucket.datos.bucket}/raw/ipc_categorias/"
    input_format  = "org.apache.hadoop.mapred.TextInputFormat"
    output_format = "org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat"

    ser_de_info {
      serialization_library = "org.apache.hadoop.hive.serde2.OpenCSVSerde"
      parameters = {
        "separatorChar" = ","
        "quoteChar"     = "\""
      }
    }

    # fecha y cargado_en quedan como string: el CSV SerDe no tipa fechas, y castear en la consulta
    # (CAST(fecha AS DATE)) es más simple y explícito que pelear con formatos de columna.
    columns {
      name = "categoria"
      type = "string"
    }
    columns {
      name = "fecha"
      type = "string"
    }
    columns {
      name = "valor"
      type = "double"
    }
    columns {
      name = "cargado_en"
      type = "string"
    }
  }
}
