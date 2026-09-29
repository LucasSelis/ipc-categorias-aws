# Decisiones de diseño

## Por qué no está desplegado

Crear una cuenta en AWS, Azure o GCP pide una tarjeta para verificar identidad, incluso para quedarse dentro del nivel gratuito. No es una limitación de AWS en particular: los tres piden lo mismo. No tengo tarjeta hoy, así que el proyecto queda **diseñado y probado, no desplegado**, y lo digo así en vez de simularlo con una demo que en realidad corre en otro lado (como DuckDB local con el nombre "AWS" encima, que sería engañoso).

La frontera exacta de qué se pudo verificar sin cuenta: `terraform validate` y `dbt parse` no necesitan credenciales (solo bajan plugins/dependencias públicas); `terraform plan`/`apply` y `dbt compile`/`build` sí, porque necesitan hablarle a la API real de AWS. Lo comprobé a propósito: corrí `terraform init` + `validate` (verde) y después `dbt compile`, que efectivamente falló con `NoCredentialsError` — la prueba de que la frontera es esa y no otra cosa.

## Datos

**1. Catálogo de series verificado antes de escribir infraestructura.** Busqué las 13 series en el buscador de datos.gob.ar, confirmé que las 13 tienen 117 meses sin huecos (dic-2016 a ago-2026, igual que el observatorio de inflación) y probé la descarga real contra la API antes de tocar Terraform. Encontrar las series costó más de lo esperado: el buscador de texto libre no las devolvía con términos como "IPC división alimentos"; aparecieron recién buscando por el patrón de nombre real del dataset ("Categoría", "Base dic 2016").

**2. Formato largo (tidy), no ancho.** Una fila por `(categoría, fecha)` en vez de una columna por categoría. Así agregar una categoría nueva el día de mañana no cambia el esquema de la tabla de Glue.

**3. `cargado_en` en vez de partición por fecha de corrida.** Con ~90 KB de datos totales, particionar por `dt=` de cada corrida (como se hace con volúmenes grandes) sería complejidad sin beneficio: un solo archivo, versionado por S3, alcanza y sobra. El versionado del bucket da el historial "quién cambió qué" sin manejar particiones a mano.

## Ingesta y AWS

**4. Lambda sin capas ni dependencias.** Solo usa `boto3` (ya viene en el runtime) y la librería estándar (`urllib`, `csv`), igual que `fuentes.py` en el observatorio de inflación. El paquete de despliegue pesa unos KB: nada de `pandas`/`pyarrow` en Lambda, que hubiera obligado a una capa o una imagen de contenedor.

**5. CSV, no Parquet.** Con 13 series y 117 meses, el ahorro de espacio de Parquet es irrelevante, y CSV evita la capa de `awswrangler`/`pyarrow`. Si el dataset creciera en volumen, sería la primera decisión a revisar.

**6. Tabla de Glue fija, sin crawler.** El esquema (`categoria`, `fecha`, `valor`, `cargado_en`) es conocido y estable; un crawler agrega costo y no determinismo por algo que no cambia. Se declara directo en Terraform.

**7. `fecha` queda como `string` en la tabla, se castea en dbt.** El SerDe de CSV de Athena no tipa fechas. Castear en la consulta (`CAST(fecha AS DATE)`) es más simple y explícito que pelear con el tipo de columna en la definición de la tabla.

**8. La ingesta nunca pisa datos buenos con una respuesta vacía.** Si la API devuelve `data: []` (o un error), la Lambda corta con una excepción antes de llamar a `s3:PutObject`. Cubierto por un test con `moto`: cargo datos, simulo una respuesta vacía, y verifico que el objeto en S3 sigue siendo el de antes, byte a byte.

**9. Programado para el día 18, no el 12.** El INDEC suele publicar el IPC entre el 12 y el 15; el margen evita depender de una fecha exacta que a veces se corre unos días.

## Infraestructura y seguridad

**10. La alarma de presupuesto es de los primeros recursos, no un agregado al final.** `budget.tf` se pensó antes que el resto: avisa al 50/80/100% del gasto real, y también si el gasto *proyectado* para fin de mes va a superar el límite (alerta más temprana que esperar a cruzar el umbral).

**11. Cada rol de IAM hace una sola cosa.** El rol de la Lambda solo puede escribir en `raw/ipc_categorias/*` y sus propios logs. El rol del scheduler de EventBridge solo puede invocar esta Lambda (no otra). Ninguno de los dos tiene permisos de lectura, borrado, ni de administración.

**12. El Explorador SQL público se protege con IAM, no con el código de la app.** Es la decisión que más quise dejar clara: en el observatorio de inflación (DuckDB), la barrera contra un `DROP TABLE` era que el proceso corría en modo solo lectura y sin acceso a archivos —una barrera de *proceso*—. Acá el proceso (la app de Streamlit) corre en un servidor ajeno a AWS (Streamlit Cloud): la única barrera real es qué le permite hacer AWS al usuario IAM con el que se conecta, sin importar qué SQL le pase. Por eso el usuario `ipc-categorias-app-sql` no tiene ningún permiso de escritura sobre el dato ni el catálogo, solo `athena:StartQueryExecution`/`GetQueryResults` y lectura de S3/Glue. La validación de "una sola sentencia `SELECT`" en `app/aws_athena.py` sigue estando (mejor mensaje de error, no gastar una consulta en algo que va a fallar), pero es la segunda capa, no la primera.

**13. Tope de bytes escaneados por consulta.** El workgroup de Athena corta cualquier consulta que escanee más de 100 MB. Con el dataset completo pesando ~90 KB, ninguna consulta legítima se acerca; esto cubre el caso de una consulta mal escrita que termine escaneando de más.

**14. Los resultados de Athena se autodestruyen a los 3 días.** Cada consulta del Explorador SQL deja un archivo en `athena-results/`; sin este lifecycle rule, muchas consultas de mucha gente irían acumulando basura para siempre.

**15. El access key del usuario de la app no se genera con Terraform.** Si Terraform creara la clave (`aws_iam_access_key`), quedaría en el state, que puede terminar en git, en un log, o en cualquier backup. La genero a mano en la consola de AWS para ese usuario puntual, y la cargo directo como secreto en Streamlit Cloud: nunca pasa por un archivo de este repo. Es un trade-off consciente: una clave de acceso de larga duración para un usuario IAM es, hoy, la única forma práctica de que una app pública en Streamlit Cloud llame a la API de AWS (no hay soporte de roles asumibles vía OIDC ahí). Se mitiga con permisos mínimos, el tope de bytes escaneados y la expiración de los resultados.

**16. El mail de la alarma de presupuesto no tiene default.** `variables.tf` lo deja obligatorio, y se completa en `terraform.tfvars` (gitignoreado) a partir de `terraform.tfvars.example`. Ningún mail personal queda en el repo.

## dbt

**17. `nucleo`/`regulados`/`estacionales` se excluyen del ranking de categorías.** Son una apertura del *mismo* nivel general por rigidez de precios, no rubros de consumo: incluirlas en el ranking de "qué categoría empujó más" duplicaría conceptualmente el peso del nivel general. Se filtran en `mart_ranking_ultimo_mes` con un comentario explicando por qué.

**18. Rango de variación más ancho que en el observatorio general (-10..100, no -5..50).** Una categoría puntual (Regulados, por un ajuste tarifario; Transporte, por un aumento de combustibles) puede saltar fuerte en un mes sin que sea un error de carga. Un rango calcado del nivel general daría falsos positivos.

## App local

**19. `server.address` no va en `.streamlit/config.toml`, va como bandera al correrla local.** Por defecto Streamlit escucha en todas las interfaces de red, no solo en la PC donde corre: cualquiera en la misma WiFi podría abrirla. Lo mismo que encontré en el observatorio de inflación. Acá la solución es distinta a propósito: esta app se piensa para Streamlit Community Cloud, y si `server.address = "127.0.0.1"` quedara fijo en el archivo de configuración, un servidor de despliegue podría obedecerlo y la app quedaría inaccesible para todo el mundo. Por eso la restricción va como bandera (`--server.address 127.0.0.1`) solo al correrla en una PC local, documentada en el README.

## Lo que sigue (cuando haya cuenta)

`terraform plan` (para ver qué se crearía, sin aplicar nada), después `terraform apply`, generar la access key del usuario de la app a mano, correr `dbt build` una vez, y cargar los secretos en Streamlit Cloud. Todo documentado en el README.
