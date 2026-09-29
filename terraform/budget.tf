# Lo primero que se despliega. Avisa por mail al 50%, 80% y 100% del presupuesto,
# y también si el gasto YA PROYECTADO para fin de mes lo va a superar (alerta más temprana que
# esperar a que el gasto real cruce el umbral).
resource "aws_budgets_budget" "mensual" {
  name         = "${var.nombre_proyecto}-mensual"
  budget_type  = "COST"
  limit_amount = tostring(var.limite_presupuesto_usd)
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.email_alertas_presupuesto]
    }
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.email_alertas_presupuesto]
  }
}
