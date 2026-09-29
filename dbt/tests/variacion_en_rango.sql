-- Igual que en el observatorio de inflación: un valor fuera de rango casi seguro es un error de carga.
-- El rango es más ancho que el del nivel general (-5..50) porque categorías puntuales (Regulados,
-- Transporte) pueden saltar fuerte en un mes por un ajuste tarifario, sin que sea un error de datos.
select mes, categoria, variacion_m
from {{ ref('mart_variacion_categorias') }}
where variacion_m not between -10 and 100
