variable "region" {
  description = "Región de AWS. us-east-1 tiene el catálogo de servicios más completo y suele ser la más barata."
  type        = string
  default     = "us-east-1"
}

variable "nombre_proyecto" {
  description = "Prefijo para nombrar los recursos (bucket, funciones, etc.). Los buckets de S3 son únicos"
  type        = string
  default     = "ipc-categorias"
}

variable "email_alertas_presupuesto" {
  description = "A dónde llega el aviso si el gasto del mes supera los umbrales. Sin default a propósito: nunca queda un mail hardcodeado en el repo."
  type        = string
}

variable "limite_presupuesto_usd" {
  description = "Presupuesto mensual de referencia (USD). El proyecto entero, bien usado, cuesta centavos; esto es un techo de seguridad, no lo esperado."
  type        = number
  default     = 5
}
