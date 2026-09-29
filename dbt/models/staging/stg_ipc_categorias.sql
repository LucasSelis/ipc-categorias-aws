-- El CSV SerDe de Athena no tipa fechas: se castea acá, explícito, en vez de pelear con el tipo de columna.
-- cargado_en es ISO 8601 con 'Z' final; cast(... as timestamp) de Presto no lo acepta, por eso from_iso8601_timestamp.
select
    categoria,
    cast(fecha as date) as mes,
    valor,
    from_iso8601_timestamp(cargado_en) as cargado_en
from {{ source('raw', 'ipc_categorias') }}
