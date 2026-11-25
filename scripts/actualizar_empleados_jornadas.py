import json
import os

json_files = [
    "c:/Users/Gaby/OneDrive/Desktop/empleados/empleados_iniciales.json",
    "c:/Users/Gaby/OneDrive/Desktop/rrhh-asistencia/empleados_iniciales.json",
    "c:/Users/Gaby/OneDrive/Desktop/rrhh-asistencia/static/js/empleados.json",
]

empleados_5h = [
    "NATALIA COSTILLA",
    "NATALIA VIRE",
    "JORGE CASTILLO",
    "ALFREDO CASTILLO",
    "ANDREA PRIOR",
    "MARISA PAEZ",
    "CINTIA ALVARADO",
    "ROMINA CAÑETE",
    "NICOLAS ACOSTA",
    "ROBERTO CARRANZA",
    "VICENTE BERNAL",
]

with open(json_files[0], "r", encoding="utf-8") as f:
    emps = json.load(f)

# Si Nicolas Acosta no está, lo agregamos
tiene_acosta = any("ACOSTA" in e.get("nombre", "").upper() for e in emps)
if not tiene_acosta:
    emps.append({
        "legajo": "426884",
        "dni": "",
        "nombre": "ACOSTA, NICOLAS",
        "horasJornada": "5 horas",
        "horas_jornada_numero": 5.0,
        "fechaIngreso": "",
        "usuario": "NAcosta",
        "telefono": "",
        "cumpleanos": "",
        "direccion": "",
        "email": "nacosta@local.com",
        "rol": "empleado",
        "franco_semanal": "1 franco por semana (lunes a domingo)",
    })

# Asignar legajo a Alancay Aldo si faltaba
for e in emps:
    if "ALANCAY" in e.get("nombre", "").upper() and not e.get("legajo"):
        e["legajo"] = "20740"

# Clasificar 5h vs 8h
for e in emps:
    nombre = e.get("nombre", "").upper()
    es_5h = (
        any(p in nombre for p in ["COSTILLA", "VIRE", "CASTILLO, JORGE", "CASTILLO ALFREDO", "PRIOR", "PAEZ", "ALVARADO", "CAÑETE", "ACOSTA", "CARRANZA", "BERNAL"])
        or (nombre == "CASTILLO JORGE")
    )
    if es_5h:
        e["horasJornada"] = "5 horas"
        e["horas_jornada_numero"] = 5.0
    else:
        e["horasJornada"] = "8 horas"
        e["horas_jornada_numero"] = 8.0
    e["franco_semanal"] = "1 franco por semana (lunes a domingo)"

# Guardar en todos los archivos
for path in json_files:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(emps, f, indent=2, ensure_ascii=False)

c5 = sum(1 for e in emps if e["horas_jornada_numero"] == 5.0)
c8 = sum(1 for e in emps if e["horas_jornada_numero"] == 8.0)
print(f"Total empleados: {len(emps)}")
print(f"Total 5 horas: {c5}")
print(f"Total 8 horas: {c8}")
print("\n--- EMPLEADOS CON JORNADA DE 5 HORAS ---")
for e in sorted(emps, key=lambda x: x["nombre"]):
    if e["horas_jornada_numero"] == 5.0:
        print(f"  • Legajo: {e.get('legajo', 'S/L'):<6} | {e['nombre']}")

print("\n--- EMPLEADOS CON JORNADA DE 8 HORAS ---")
for e in sorted(emps, key=lambda x: x["nombre"]):
    if e["horas_jornada_numero"] == 8.0:
        print(f"  • Legajo: {e.get('legajo', 'S/L'):<6} | {e['nombre']}")
