-- Variación mensual (%) de cada categoría, calculada con una window function por categoría.
with datos as (
    select * from {{ ref('stg_ipc_categorias') }}
),

con_rezago as (
    select
        categoria,
        mes,
        valor,
        lag(valor) over (partition by categoria order by mes) as valor_mes_anterior
    from datos
)

select
    categoria,
    mes,
    valor,
    round((valor / valor_mes_anterior - 1) * 100, 2) as variacion_m
from con_rezago
where valor_mes_anterior is not null
order by mes, categoria
