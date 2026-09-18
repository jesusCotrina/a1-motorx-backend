from datetime import date

from fastapi import HTTPException, status


def rango_mes(mes: str | None) -> tuple[str, date, date]:
    """Convierte un 'YYYY-MM' (o None, para el mes actual) en el rango
    [inicio, fin) de fechas de ese mes, mas su representacion normalizada."""
    if mes:
        try:
            anio, mes_num = (int(p) for p in mes.split("-"))
            inicio = date(anio, mes_num, 1)
        except (ValueError, TypeError) as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY, "Formato de mes invalido (usa YYYY-MM)"
            ) from exc
    else:
        hoy = date.today()
        inicio = date(hoy.year, hoy.month, 1)
    if inicio.month == 12:
        fin = date(inicio.year + 1, 1, 1)
    else:
        fin = date(inicio.year, inicio.month + 1, 1)
    return inicio.strftime("%Y-%m"), inicio, fin
