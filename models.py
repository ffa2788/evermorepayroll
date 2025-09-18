from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta
from sqlalchemy import JSON, CheckConstraint

db = SQLAlchemy()

class Empleado(db.Model):
    __tablename__ = "empleados"
    id = db.Column(db.Integer, primary_key=True)
    nombres = db.Column(db.String(120), nullable=False)
    apellidos = db.Column(db.String(120), nullable=False)
    identificacion = db.Column(db.String(80), unique=True, nullable=True)
    puesto = db.Column(db.String(120))
    tipo_pago = db.Column(db.String(20), default="por_hora")  # por_hora | mensual
    tarifa_hora = db.Column(db.Float, default=0.0)            # si por_hora
    salario_mensual = db.Column(db.Float, default=0.0)        # si mensual
    horario_entrada = db.Column(db.String(5), default="08:00")# "HH:MM"
    activo = db.Column(db.Boolean, default=True)

    # extras
    foto = db.Column(db.String(255), nullable=True)
    biometric_id = db.Column(db.String(120), nullable=True)

    asistencias = db.relationship("Asistencia", backref="empleado", lazy=True)

class Asistencia(db.Model):
    __tablename__ = "asistencias"
    id = db.Column(db.Integer, primary_key=True)
    empleado_id = db.Column(db.Integer, db.ForeignKey("empleados.id"), nullable=False)
    fecha = db.Column(db.Date, nullable=False)
    hora_entrada = db.Column(db.Time, nullable=True)
    hora_salida = db.Column(db.Time, nullable=True)
    minutos_tarde = db.Column(db.Integer, default=0)

class PeriodoNomina(db.Model):
    __tablename__ = "periodos"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(120), nullable=False)
    fecha_inicio = db.Column(db.Date, nullable=False)
    fecha_fin = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(20), default="borrador")  # borrador | calculado | cerrado
    items = db.relationship("NominaItem", backref="periodo", lazy=True, cascade="all, delete-orphan")

class NominaItem(db.Model):
    __tablename__ = "nomina_items"
    id = db.Column(db.Integer, primary_key=True)
    periodo_id = db.Column(db.Integer, db.ForeignKey("periodos.id"), nullable=False)
    empleado_id = db.Column(db.Integer, db.ForeignKey("empleados.id"), nullable=False)
    horas_trabajadas = db.Column(db.Float, default=0.0)
    salario_bruto = db.Column(db.Float, default=0.0)
    deducciones = db.Column(JSON, default=dict)  # {"nombre": monto}
    impuestos = db.Column(JSON, default=dict)    # {"nombre": monto}
    salario_neto = db.Column(db.Float, default=0.0)

    empleado = db.relationship("Empleado")

class Configuracion(db.Model):
    __tablename__ = "config"
    id = db.Column(db.Integer, primary_key=True)
    moneda = db.Column(db.String(10), default="L")
    # Config biometría (placeholders)
    bio_provider = db.Column(db.String(80), default="")
    bio_api_base = db.Column(db.String(255), default="")
    bio_api_token = db.Column(db.String(255), default="")
    # listas de reglas: [{"nombre":"Seguro Social", "tipo":"porcentaje","valor":5.0,"base":"bruto"}]
    reglas_deducciones = db.Column(JSON, default=list)
    reglas_impuestos = db.Column(JSON, default=list)

def parse_hhmm(s):
    try:
        hh, mm = s.split(":")
        return time(int(hh), int(mm))
    except:
        return time(8,0)

def horas_entre(hora_entrada, hora_salida):
    if not hora_entrada or not hora_salida:
        return 0.0
    dt0 = datetime.combine(date.today(), hora_entrada)
    dt1 = datetime.combine(date.today(), hora_salida)
    if dt1 < dt0:
        dt1 += timedelta(days=1)
    return round((dt1 - dt0).total_seconds() / 3600.0, 2)

def minutos_tarde_vs(hora_entrada_real, horario_entrada_str):
    if not hora_entrada_real:
        return 0
    hprog = parse_hhmm(horario_entrada_str)
    dtp = datetime.combine(date.today(), hprog)
    dtr = datetime.combine(date.today(), hora_entrada_real)
    delay = int((dtr - dtp).total_seconds() / 60)
    return max(0, delay)
