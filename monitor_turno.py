from datetime import datetime

# ─── CONSTANTES ───────────────────────────────────────────────────────────────

TURNOS = {
    "corto": {"oficiales": 320, "reales": 310, "fin": 360},   # Mar–Vie
    "largo": {"oficiales": 650, "reales": 640, "fin": 720},   # Sábado
}

# Normalización de días: aliases → clave canónica
ALIAS_DIA = {
    "martes":    "martes",
    "miércoles": "miércoles",
    "miercoles": "miércoles",
    "jueves":    "jueves",
    "viernes":   "viernes",
    "sábado":    "sábado",
    "sabado":    "sábado",
}

INDICADORES = [
    ("85%",  0.85),
    ("90%",  0.90),
    ("100%", 1.00),
    ("101%", 1.01),
]

# ─── HELPERS ──────────────────────────────────────────────────────────────────

def parse_hora(texto: str) -> int | None:
    """
    Convierte texto como '1:30', '3am', '11:45pm' a minutos desde medianoche.
    Rango válido: 0–720 (medianoche a 12:00pm).
    Retorna None si el formato es inválido.
    """
    texto = texto.strip().lower()
    es_pm = texto.endswith("pm")
    es_am = texto.endswith("am")
    texto = texto.replace("am", "").replace("pm", "").strip()

    partes = texto.split(":")
    try:
        h = int(partes[0])
        m = int(partes[1]) if len(partes) > 1 else 0
    except (ValueError, IndexError):
        return None

    # Validación básica antes de aplicar am/pm
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None

    if es_pm and h != 12:
        h += 12
    elif es_am and h == 12:
        h = 0

    minutos = h * 60 + m
    return minutos if 0 <= minutos <= 720 else None


def min_a_hora(minutos: int) -> str:
    """Convierte minutos desde medianoche a formato '1:30am' / '6:00pm'."""
    h = (minutos // 60) % 24
    m = minutos % 60
    sufijo = "am" if h < 12 else "pm"
    h12 = h % 12 or 12          # 0 → 12, 13 → 1, etc.
    return f"{h12}:{m:02d}{sufijo}"


def pedir(prompt: str, validar=None, opciones: list[str] | None = None) -> str:
    """
    Solicita input al usuario con validación.
    - opciones: lista de strings válidos (case-insensitive)
    - validar:  función que retorna el valor procesado o None si es inválido
    """
    opciones_lower = [o.lower() for o in opciones] if opciones else []

    while True:
        resp = input(prompt).strip()

        if opciones:
            if resp.lower() in opciones_lower:
                return resp.lower()
            print(f"  Opciones válidas: {' / '.join(opciones)}")
            continue

        if validar:
            resultado = validar(resp)
            if resultado is not None:
                return resultado
            print("  Formato inválido. Intenta de nuevo (ej. 1:30, 3am, 11:45pm).")
            continue

        if resp:
            return resp

        print("  La respuesta no puede estar vacía.")


def pedir_numero(prompt: str, solo_positivo: bool = True) -> float:
    """
    Solicita un número al usuario.
    solo_positivo=True rechaza valores ≤ 0.
    """
    while True:
        try:
            n = float(input(prompt).strip())
            if solo_positivo and n <= 0:
                print("  Ingresa un número mayor a 0.")
                continue
            return n
        except ValueError:
            print("  Ingresa un número válido.")


# ─── LÓGICA DE ESTADOS ────────────────────────────────────────────────────────

def get_estado(piezas: int, proy_real: int, proy_turbo: int, meta: int) -> str:
    """
    ✅ = ya alcanzado o proyectado al ritmo actual
    ⚡ = solo alcanzable acelerando al máximo
    ❌ = imposible en este turno
    """
    if piezas >= meta or proy_real >= meta:
        return "✅"
    if proy_turbo >= meta:
        return "⚡"
    return "❌"


def texto_situacion(estados: list[str], max_real: float) -> str:
    """Genera un mensaje de diagnóstico legible según el estado de los indicadores."""
    etiquetas = ["85%", "90%", "100%", "101%"]

    verdes = [e for e, s in zip(etiquetas, estados) if s == "✅"]
    rayos  = [e for e, s in zip(etiquetas, estados) if s == "⚡"]
    rojos  = [e for e, s in zip(etiquetas, estados) if s == "❌"]

    if not rojos and not rayos:
        return "Vas muy bien — todos los indicadores están asegurados a tu ritmo actual."

    if not verdes and not rayos:
        return "Este turno ya no tiene recuperación en números. Concéntrate en hacer las cosas bien, no rápido."

    if not verdes and not rojos:
        return (
            f"A tu ritmo actual no alcanzas ningún indicador. "
            f"Acelerando al máximo ({int(max_real)} pz/h) puedes alcanzar todos — hasta el 101%."
        )

    partes = []
    if verdes:
        partes.append(f"El {verdes[-1]} ya está asegurado a tu ritmo actual.")
    if rayos:
        partes.append(f"Con turbo ({int(max_real)} pz/h) alcanzas hasta el {rayos[-1]}.")
    if rojos:
        partes.append(f"El {rojos[0]} ya no es posible en este turno.")

    return " ".join(partes)


# ─── FLUJO PRINCIPAL ──────────────────────────────────────────────────────────

def calcular():
    print()

    # P1 — Día
    resp_dia = pedir(
        "¿Qué día es?\nMartes / Miércoles / Jueves / Viernes / Sábado\n→ ",
        opciones=list(ALIAS_DIA.keys())
    )
    dia = ALIAS_DIA[resp_dia]                   # normalizado a forma canónica
    es_sabado = dia == "sábado"
    turno = TURNOS["largo"] if es_sabado else TURNOS["corto"]

    min_oficiales = turno["oficiales"]
    min_reales    = turno["reales"]
    fin_turno     = turno["fin"]
    hora_fin_str  = min_a_hora(fin_turno)

    print()

    # P2 — Velocidades
    meta_pzh = pedir_numero("¿Meta pz/h? → ")
    max_real  = pedir_numero("¿Máximo real de la línea pz/h? → ")

    if max_real < meta_pzh:
        print(f"  ⚠️  El máximo real ({max_real:.0f}) es menor a la meta ({meta_pzh:.0f}). Verifica los datos.")

    print()

    # P3 — Hora actual (auto-detectada del sistema)
    _ahora = datetime.now()
    _auto_min = _ahora.hour * 60 + _ahora.minute
    _auto_str = min_a_hora(_auto_min)
    _confirm = pedir(f"Hora detectada: {_auto_str} — ¿es correcta? (si / no) → ", opciones=["si", "sí", "no"])
    if _confirm in ("si", "sí") and 0 <= _auto_min <= 720:
        hora_actual_min = _auto_min
    else:
        if _confirm in ("si", "sí"):
            print("  Esa hora está fuera del rango del turno.")
        hora_actual_min: int = pedir("¿Qué hora es? (ej. 1:30, 3am, 11:45pm) → ", validar=parse_hora)

    print()

    # P4 — Paros (comida y breaks)
    comio  = False
    breaks = 0

    if es_sabado:
        r = pedir("¿Ya comiste? (si / no) → ", opciones=["si", "sí", "no"])
        comio = r in ("si", "sí")
        b = pedir("¿Cuántos breaks tomaron? (0 / 1 / 2) → ", opciones=["0", "1", "2"])
        breaks = int(b)
        print()
    elif hora_actual_min >= 120:            # ≥ 2:00am
        r = pedir("¿Ya comiste? (si / no) → ", opciones=["si", "sí", "no"])
        comio = r in ("si", "sí")
        print()

    # P5 — Piezas hechas
    piezas = int(pedir_numero("¿Cuántas piezas llevas? → ", solo_positivo=False))

    # ─── CÁLCULOS ───────────────────────────────────────────────────────────

    # Minutos productivos reales hasta ahorita
    min_productivos = hora_actual_min - 10          # descuenta arranque
    if comio:
        min_productivos -= 30
    min_productivos -= breaks * 15
    min_productivos = max(min_productivos, 1)       # evita división por cero

    # Piezas esperadas y diferencia
    esperadas  = round((meta_pzh / 60) * min_productivos)
    diferencia = piezas - esperadas
    dif_str    = f"+{diferencia}" if diferencia >= 0 else str(diferencia)

    # Minutos productivos restantes hasta fin de turno
    min_restantes = max(min_reales - min_productivos, 0)

    # Ritmo real observado (con protección ante valores extremos)
    ritmo_real = (piezas / min_productivos) * 60
    proy_real  = round(piezas + (ritmo_real / 60) * min_restantes)
    proy_meta  = round(piezas + (meta_pzh   / 60) * min_restantes)
    proy_turbo = round(piezas + (max_real   / 60) * min_restantes)

    # Metas absolutas por indicador y su estado
    metas_pz = [(label, round((meta_pzh / 60) * min_oficiales * pct)) for label, pct in INDICADORES]
    estados  = [get_estado(piezas, proy_real, proy_turbo, m) for _, m in metas_pz]
    faltan   = [max(m - piezas, 0) for _, m in metas_pz]

    # Ritmo necesario de aquí en adelante para alcanzar cada meta
    ritmos_nec = [
        round((f / min_restantes) * 60) if f > 0 and min_restantes > 0 else None
        for f in faltan
    ]

    # El personal para 10 min antes del cierre oficial
    fin_real_clock = fin_turno - 10

    # Minutos de reloj que aún se perderán en paras pendientes
    clock_breaks_futuros = 0
    if not comio:
        clock_breaks_futuros += 30
    if es_sabado:
        clock_breaks_futuros += max(2 - breaks, 0) * 15

    # ETA al ritmo actual (para ✅) y al máximo (para ⚡), capeado en fin_real_clock
    horas_termino_real  = []
    horas_termino_turbo = []
    for falta in faltan:
        if falta <= 0:
            horas_termino_real.append(None)
            horas_termino_turbo.append(None)
        else:
            eta_r = hora_actual_min + (falta * 60 / ritmo_real) + clock_breaks_futuros if ritmo_real > 0 else None
            eta_t = hora_actual_min + (falta * 60 / max_real)   + clock_breaks_futuros if max_real  > 0 else None
            horas_termino_real.append(round(eta_r) if eta_r is not None and eta_r <= fin_real_clock else None)
            horas_termino_turbo.append(round(eta_t) if eta_t is not None and eta_t <= fin_real_clock else None)

    hora_str    = min_a_hora(hora_actual_min)
    dia_display = dia.capitalize()

    # ─── OUTPUT ─────────────────────────────────────────────────────────────

    print()
    print(f"── {dia_display} · 12:00am–{hora_fin_str} {'─'*20}")
    print(f"Hora: {hora_str} · Llevas: {piezas:,} pz · Esperadas: {esperadas:,} pz · Diferencia: {dif_str} pz")
    print()
    print("PROYECCIONES")
    print(f"  📊 Real   → {proy_real:,} pz   (a {ritmo_real:.1f} pz/h)")
    print(f"  📈 Ideal  → {proy_meta:,} pz   (a {int(meta_pzh)} pz/h)")
    print(f"  ⚡ Turbo  → {proy_turbo:,} pz   (a {int(max_real)} pz/h)")
    print()
    print("INDICADORES")
    for (label, meta), estado, falta, eta_real, eta_turbo, r_nec in zip(
            metas_pz, estados, faltan, horas_termino_real, horas_termino_turbo, ritmos_nec):
        if falta <= 0:
            barra = "alcanzado"
        elif estado == "✅":
            sufijo = f" · ~{min_a_hora(eta_real)}" if eta_real is not None else ""
            barra = f"faltan {falta:,} pz{sufijo}"
        elif estado == "⚡":
            eta_str   = f" · con turbo ~{min_a_hora(eta_turbo)}" if eta_turbo is not None else ""
            ritmo_str = f" · necesitas {r_nec} pz/h" if r_nec is not None else ""
            barra = f"faltan {falta:,} pz{eta_str}{ritmo_str}"
        else:
            ritmo_str = f" (necesitarías {r_nec} pz/h)" if r_nec is not None else ""
            barra = f"faltan {falta:,} pz · imposible{ritmo_str}"
        print(f"  {estado} {label:>4}  →  {meta:,} pz   ({barra})")
    print()
    print(f"📋 {texto_situacion(estados, max_real)}")
    print()


# ─── ENTRY POINT ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    while True:
        calcular()
        print()
        again = pedir("¿Calcular otro turno? (si / no) → ", opciones=["si", "sí", "no"])
        if again not in ("si", "sí"):
            print("Que te vaya bien en el turno. 👊")
            break
        print("\n" + "═" * 45 + "\n")
