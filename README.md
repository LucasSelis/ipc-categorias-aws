# IPC por categoría — pipeline serverless en AWS

**¿Qué rubro empuja la inflación este mes?** El INDEC no solo publica el nivel general del IPC: también lo abre en 9 categorías de consumo (Alimentos, Transporte, Salud, ...) y en 3 por rigidez de precios (Núcleo, Regulados, Estacionales). Este proyecto arma ese detalle con un pipeline serverless en AWS: Lambda descarga las 13 series, Glue las cataloga sobre S3, dbt las modela en Athena, y una app de Streamlit deja explorarlas con SQL propio.

## Estado: diseñado y probado, no desplegado

**No hay una demo en vivo.** Para crear una cuenta de AWS (o de cualquier otro proveedor grande) hace falta una tarjeta, y no la tengo. En vez de dejar el proyecto a medio hacer, lo completé entero —ingesta, infraestructura como código, modelado, app— y verifiqué cada parte con lo que **no** necesita una cuenta:

| Parte | Cómo se verificó sin AWS | Resultado |
|---|---|---|
| Ingesta (`ingesta/`) | pytest + `moto` (simula S3 en memoria) | 12 tests, ✅ |
| App / Explorador SQL (`app/`) | pytest con el cliente de Athena mockeado + `AppTest` de Streamlit | 16 tests, ✅ |
| Infraestructura (`terraform/`) | `terraform validate` (revisa sintaxis y tipos; no se conecta a AWS) | ✅ sin errores |
| Modelos (`dbt/`) | `dbt parse` (resuelve Jinja, YAML, `source()`/`ref()`; no consulta Athena) | ✅ sin errores |

`dbt compile` y `terraform plan`/`apply` sí necesitan una cuenta real: ahí es donde se corta hoy. El día que consiga una forma de pagar la verificación de alta (una tarjeta prepaga suele alcanzar), desplegarlo es correr los comandos de la sección de abajo.

## La pregunta y los datos

13 series del INDEC (vía la API de datos.gob.ar), todas con base dic-2016=100, mensuales, nacionales:
`nivel_general`, `nucleo`, `regulados`, `estacionales`, y 9 divisiones de consumo (alimentos y bebidas, bebidas alcohólicas y tabaco, transporte, educación, salud, comunicaciones, hoteles y restaurantes, recreación y cultura, bienes y servicios varios). Verificadas antes de escribir una sola línea de infraestructura: 117 meses, sin huecos, mismo origen que el [observatorio de inflación](https://github.com/LucasSelis/observatorio-inflacion).

## Arquitectura

```
EventBridge Scheduler (mensual, día 18)
        │
        ▼
   Lambda (Python, sin capas)              S3 (versionado, privado)
   descarga 13 series ──────────────────►  raw/ipc_categorias/data.csv
   de datos.gob.ar                                │
                                                    ▼
                                         Glue Data Catalog (tabla externa fija)
                                                    │
                                                    ▼
                          dbt (dbt-athena) ──► Athena: staging + 2 marts
                                                    │
                          ┌─────────────────────────┴─────────────────────────┐
                          ▼                                                    ▼
              app Streamlit: panel                            app Streamlit: Explorador SQL
              (ranking del mes, series)                       (usuario IAM de solo lectura)
```

Todo en `terraform/`: bucket S3, rol y función Lambda, EventBridge Scheduler, base y tabla de Glue, workgroup de Athena, y el usuario IAM de la app. Nada se creó a mano.

## Decisiones de seguridad (antes de gastar un centavo)

- **Alarma de presupuesto primero.** `terraform/budget.tf` es de los primeros recursos: avisa por mail al 50%, 80%, 100% del presupuesto y también si el gasto *proyectado* lo va a superar.
- **Explorador SQL protegido por IAM, no por el código de la app.** El usuario que usa la app pública (`terraform/iam_app.tf`) solo puede ejecutar consultas y leer resultados; no tiene permiso para escribir, borrar ni crear nada, sin importar qué SQL le manden. La validación en `app/aws_athena.py` (una sola sentencia `SELECT`) es una segunda capa para dar un mensaje claro, no la barrera real.
- **Tope de costo por consulta.** El workgroup de Athena corta cualquier consulta que escanee más de 100 MB (`bytes_scanned_cutoff_per_query`). Con ~90 KB de datos totales, ninguna consulta legítima se acerca a ese límite.
- **Nada de secretos en el repo.** La access key del usuario de la app se genera a mano en la consola de AWS (no vía Terraform, para que nunca quede en el state) y se carga como secreto en Streamlit Cloud. El mail de la alarma de presupuesto va en `terraform.tfvars`, que está en `.gitignore`.

Más detalle, con los porqués y algún error en el camino, en [DECISIONES.md](DECISIONES.md).

## Cómo verificarlo hoy (sin cuenta de AWS)

```bash
# Ingesta: 12 tests, simula S3 con moto
cd ingesta && pip install -r requirements-dev.txt && pytest -q

# App: 16 tests, mockea el cliente de Athena
cd app && pip install -r requirements-dev.txt && pytest -q

# Infraestructura: valida sintaxis y tipos, no toca AWS
cd terraform && terraform init -backend=false && terraform validate

# Modelos: resuelve Jinja/YAML/refs, no consulta Athena
cd dbt && DBT_PROFILES_DIR=. OBS_BUCKET=x dbt parse

# La app en el navegador: sin AWS configurado muestra el aviso de "no desplegada" (ver captura
# arriba). --server.address 127.0.0.1 es a propósito: por defecto Streamlit escucha en toda la
# red, no solo en esta PC (ver DECISIONES.md, punto 19).
cd app && streamlit run IPC_por_categoria.py --server.address 127.0.0.1
```

## Cómo desplegarlo (cuando haya cuenta de AWS)

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # completar el mail para la alarma de presupuesto
terraform init
terraform apply                                 # revisar el plan antes de confirmar
```

Después: generar a mano la access key del usuario `ipc-categorias-app-sql` (consola de AWS → IAM), cargarla como secreto en Streamlit Community Cloud junto con `GLUE_DATABASE`/`ATHENA_WORKGROUP`/`AWS_REGION`, y correr `dbt build` una vez para poblar los modelos.

## Estructura

```
ingesta/    Lambda: descarga las 13 series y las sube a S3 (12 tests, moto)
terraform/  toda la infraestructura como código
dbt/        staging + 2 marts sobre Athena (ranking del mes, variación por categoría)
app/        Streamlit: panel + Explorador SQL (16 tests, Athena mockeado)
```
