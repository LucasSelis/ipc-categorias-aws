-- Cada categoría debe tener un dato por mes, sin saltos, igual que se valida en el observatorio de inflación.
select categoria, mes, mes_anterior
from (
    select categoria, mes, lag(mes) over (partition by categoria order by mes) as mes_anterior
    from {{ ref('stg_ipc_categorias') }}
)
where mes_anterior is not null
  and mes <> date_add('month', 1, mes_anterior)
