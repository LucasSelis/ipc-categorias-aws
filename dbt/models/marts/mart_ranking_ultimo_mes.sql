-- ¿Qué categoría empujó más la inflación en el último mes publicado? Ranking con RANK().
with variaciones as (
    select * from {{ ref('mart_variacion_categorias') }}
    where categoria not in ('nucleo', 'regulados', 'estacionales') -- son aperturas por rigidez, no por rubro de consumo: mezclarlas duplicaría el "peso" del nivel general en el ranking
),

ultimo_mes as (
    select max(mes) as mes from variaciones
)

select
    v.categoria,
    v.mes,
    v.variacion_m,
    rank() over (order by v.variacion_m desc) as puesto
from variaciones as v
inner join ultimo_mes as u on v.mes = u.mes
order by puesto
