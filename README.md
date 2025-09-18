# Nómina Simple (ES)

Aplicación web **sencilla y personalizable** para gestionar nómina, asistencias y puntualidad para ~20 empleados.  
UI en **español**, diseño simple con **Bootstrap**, base de datos **SQLite** por defecto.

## Características clave (MVP)
- **Empleados**: Altas / bajas / edición; salario por hora o mensual; horario de entrada para medir puntualidad.
- **Asistencias**: Registro manual de entrada/salida; cálculo automático de **horas trabajadas** y **minutos de tardanza** vs horario del empleado.
- **Períodos de nómina**: Definición de periodos; cálculo de **salario bruto**, **deducciones**, **impuestos** y **neto** por empleado.
- **Fórmulas configurables**: Deducciones e impuestos como **porcentaje** o **monto fijo**, aplicados a base **bruta** o **pre-neta**.
- **Reportes**: Asistencia por rango de fechas; ranking de puntualidad; resumen de nómina; exportación CSV.
- **100% en español**. Diseño limpio y minimalista.

> Nota: Impuestos y cargas sociales varían por país (p. ej., Honduras). Aquí se modelan de forma **configurable** para adaptarse a su régimen.

## Requisitos
- Python 3.10+
- Pip
- (Opcional) Docker

## Instalación local
```bash
python -m venv .venv
source .venv/bin/activate  # (Windows: .venv\Scripts\activate)
pip install -r requirements.txt
cp .env.example .env
python app.py  # inicia en http://127.0.0.1:5000
```

## Estructura
```
NominaSimple-ES/
├─ app.py
├─ models.py
├─ requirements.txt
├─ .env.example
├─ Dockerfile
├─ Procfile
├─ README.md
├─ .gitignore
├─ templates/
│  ├─ base.html
│  ├─ dashboard.html
│  ├─ empleados_list.html
│  ├─ empleados_form.html
│  ├─ asistencias_list.html
│  ├─ asistencias_form.html
│  ├─ periodos_list.html
│  ├─ nomina_list.html
│  ├─ nomina_detalle.html
│  ├─ config.html
│  └─ reportes.html
└─ static/
   └─ custom.css
```

## Variables de entorno
- `SECRET_KEY`: Cambie en producción.
- `DATABASE_URL`: `sqlite:///nomina.db` por defecto. Para Postgres: `postgresql+psycopg://user:pass@host:5432/dbname` (necesitará instalar `psycopg` en requirements si lo usa).

## Despliegue recomendado (Cloud)
### Opción A: Render.com (simple y gratis al inicio)
1. Cree un repo en GitHub y suba este proyecto.
2. En Render, cree un **Web Service**:
   - Runtime: Docker (usa el `Dockerfile` provisto) **o** Python con `gunicorn` usando el `Procfile`.
   - Variables: `SECRET_KEY`, `DATABASE_URL` (si usa Postgres, agregue un servicio de Postgres en Render y copie la URL).
3. Auto deploy desde `main`/`master`.
4. Listo: Render expondrá la URL de su app.

### Opción B: Railway / Fly.io / AWS Lightsail
- Siga un flujo similar: cree servicio, cargue variables, exponga puerto 8000 con `gunicorn`.
- Con Docker la portabilidad es inmediata.

## Uso básico
1. Entre a **Configuración** y defina deducciones e impuestos (porcentaje/fijo).
2. Cargue **Empleados** (defina tipo de pago y horario de entrada).
3. Registre **Asistencias** (entrada/salida).
4. Cree un **Periodo de Nómina** (fechas) y presione **Calcular**.
5. Vea **Reportes** de asistencia, puntualidad y nómina; exporte CSV.

## Seguridad y siguientes pasos
- Agregar **autenticación**/roles (admin, RR.HH., supervisor).
- Integrar **biometría** o importación de **CSV** de reloj checador.
- Soportar **recibos** (PDF) y firma.
- Multipaís: presets de fórmulas por país.

> Cualquier duda, consulte `app.py` (comentado) o escriba issues.
