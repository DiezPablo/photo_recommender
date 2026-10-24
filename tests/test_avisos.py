"""Resumen de Telegram a partir del informe."""

from rasante.avisos.telegram import construir_mensaje


def test_avisos_leen_el_informe_nuevo(informe):
    fecha = informe["fechas"][0]
    msg = construir_mensaje(informe, fecha, umbral=0, top=3, web="https://ejemplo.app")
    assert msg and "/10" in msg and "https://ejemplo.app/spot/" in msg
    assert construir_mensaje(informe, "1999-01-01", 0, 3) is None
