import os
from datetime import datetime, date, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from dotenv import load_dotenv
import pandas as pd
from io import StringIO
from werkzeug.utils import secure_filename
from models import db, Empleado, Asistencia, PeriodoNomina, NominaItem, Configuracion, horas_entre, minutos_tarde_vs

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///nomina.db")
SECRET_KEY = os.getenv("SECRET_KEY", "cambialo-por-favor")

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.secret_key = SECRET_KEY
app.config['UPLOAD_FOLDER'] = os.path.join('static','uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
ALLOWED_EXTENSIONS = {'.png','.jpg','.jpeg','.webp'}
db.init_app(app)

with app.app_context():
    db.create_all()
    if Configuracion.query.count() == 0:
        db.session.add(Configuracion(moneda="L", reglas_deducciones=[], reglas_impuestos=[]))
        db.session.commit()

@app.template_filter("money")
def money(v):
    try:
        return f"{float(v):,.2f}"
    except:
        return "0.00"

@app.route("/")
def index():
    empleados = Empleado.query.count()
    asistencias_hoy = Asistencia.query.filter_by(fecha=date.today()).count()
    periodos = PeriodoNomina.query.order_by(PeriodoNomina.id.desc()).limit(5).all()
    return render_template("dashboard.html", empleados=empleados, asistencias_hoy=asistencias_hoy, periodos=periodos)

# ---------- EMPLEADOS ----------
@app.route("/empleados")
def empleados_list():
    q = request.args.get("q","").strip()
    qry = Empleado.query
    if q:
        like = f"%{q}%"
        qry = qry.filter((Empleado.nombres.ilike(like)) | (Empleado.apellidos.ilike(like)) | (Empleado.puesto.ilike(like)))
    empleados = qry.order_by(Empleado.id.desc()).all()
    return render_template("empleados_list.html", empleados=empleados, q=q)

@app.route("/empleados/nuevo", methods=["GET","POST"])
def empleados_nuevo():
    if request.method == "POST":
        foto_path = _save_foto(request.files.get('foto'))
        foto_path = _save_foto(request.files.get('foto'))
        d = request.form
        emp = Empleado(
            nombres=d.get("nombres"), apellidos=d.get("apellidos"),
            identificacion=d.get("identificacion") or None,
            puesto=d.get("puesto") or "",
            tipo_pago=d.get("tipo_pago"),
            tarifa_hora=float(d.get("tarifa_hora") or 0),
            salario_mensual=float(d.get("salario_mensual") or 0),
            horario_entrada=d.get("horario_entrada") or "08:00",
            activo=("activo" in d),
            foto=foto_path,
            biometric_id=d.get('biometric_id') or None
        )
        db.session.add(emp); db.session.commit()
        flash("Empleado creado", "success")
        return redirect(url_for("empleados_list"))
    return render_template("empleados_form.html", emp=None)

@app.route("/empleados/<int:emp_id>/editar", methods=["GET","POST"])
def empleados_editar(emp_id):
    emp = Empleado.query.get_or_404(emp_id)
    if request.method == "POST":
        foto_path = _save_foto(request.files.get('foto'))
        foto_path = _save_foto(request.files.get('foto'))
        d = request.form
        emp.nombres = d.get("nombres")
        emp.apellidos = d.get("apellidos")
        emp.identificacion = d.get("identificacion") or None
        emp.puesto = d.get("puesto") or ""
        emp.tipo_pago = d.get("tipo_pago")
        emp.tarifa_hora = float(d.get("tarifa_hora") or 0)
        emp.salario_mensual = float(d.get("salario_mensual") or 0)
        emp.horario_entrada = d.get("horario_entrada") or "08:00"
        emp.activo = ("activo" in d)
        if foto_path:
            emp.foto = foto_path
        emp.biometric_id = d.get('biometric_id') or emp.biometric_id
        db.session.commit()
        flash("Empleado actualizado", "success")
        return redirect(url_for("empleados_list"))
    return render_template("empleados_form.html", emp=emp)

@app.route("/empleados/<int:emp_id>/borrar", methods=["POST"])
def empleados_borrar(emp_id):
    emp = Empleado.query.get_or_404(emp_id)
    db.session.delete(emp); db.session.commit()
    flash("Empleado eliminado", "success")
    return redirect(url_for("empleados_list"))

# ---------- ASISTENCIAS ----------
@app.route("/asistencias")
def asistencias_list():
    desde = request.args.get("desde") or date.today().replace(day=1).isoformat()
    hasta = request.args.get("hasta") or date.today().isoformat()
    empleado_id = request.args.get("empleado_id") or ""
    qry = Asistencia.query.join(Empleado).filter(Asistencia.fecha.between(desde, hasta))
    if empleado_id:
        qry = qry.filter(Asistencia.empleado_id==int(empleado_id))
    asistencias = qry.order_by(Asistencia.fecha.desc(), Asistencia.id.desc()).all()
    empleados = Empleado.query.order_by(Empleado.nombres).all()
    return render_template("asistencias_list.html", asistencias=asistencias, empleados=empleados, desde=desde, hasta=hasta, empleado_id=empleado_id)

@app.route("/asistencias/nuevo", methods=["GET","POST"])
def asistencias_nuevo():
    empleados = Empleado.query.order_by(Empleado.nombres).all()
    if request.method == "POST":
        foto_path = _save_foto(request.files.get('foto'))
        foto_path = _save_foto(request.files.get('foto'))
        d = request.form
        emp = Empleado.query.get(int(d.get("empleado_id")))
        h_in = datetime.strptime(d.get("hora_entrada"), "%H:%M").time() if d.get("hora_entrada") else None
        h_out = datetime.strptime(d.get("hora_salida"), "%H:%M").time() if d.get("hora_salida") else None
        minutos_tarde = minutos_tarde_vs(h_in, emp.horario_entrada) if emp and h_in else 0
        a = Asistencia(
            empleado_id=emp.id,
            fecha=datetime.strptime(d.get("fecha"), "%Y-%m-%d").date(),
            hora_entrada=h_in,
            hora_salida=h_out,
            minutos_tarde=minutos_tarde
        )
        db.session.add(a); db.session.commit()
        flash("Asistencia registrada", "success")
        return redirect(url_for("asistencias_list"))
    return render_template("asistencias_form.html", empleados=empleados, hoy=date.today().isoformat())

# ---------- PERIODOS ----------
@app.route("/periodos")
def periodos_list():
    periodos = PeriodoNomina.query.order_by(PeriodoNomina.id.desc()).all()
    return render_template("periodos_list.html", periodos=periodos)

@app.route("/periodos/nuevo", methods=["POST"])
def periodos_nuevo():
    d = request.form
    p = PeriodoNomina(
        nombre=d.get("nombre"),
        fecha_inicio=datetime.strptime(d.get("fecha_inicio"), "%Y-%m-%d").date(),
        fecha_fin=datetime.strptime(d.get("fecha_fin"), "%Y-%m-%d").date(),
        estado="borrador"
    )
    db.session.add(p); db.session.commit()
    flash("Periodo creado", "success")
    return redirect(url_for("periodos_list"))

@app.route("/periodos/<int:pid>/calcular", methods=["POST"])
def periodos_calcular(pid):
    p = PeriodoNomina.query.get_or_404(pid)
    conf = Configuracion.query.first()
    # limpiar items previos
    NominaItem.query.filter_by(periodo_id=pid).delete()
    db.session.commit()

    empleados = Empleado.query.filter_by(activo=True).all()
    for emp in empleados:
        asistencias = Asistencia.query.filter(
            Asistencia.empleado_id==emp.id,
            Asistencia.fecha.between(p.fecha_inicio, p.fecha_fin)
        ).all()
        horas = sum([(a.hora_salida and a.hora_entrada) and ((a.hora_salida.hour + a.hora_salida.minute/60) - (a.hora_entrada.hour + a.hora_entrada.minute/60)) or 0 for a in asistencias])
        horas = round(horas, 2)

        if emp.tipo_pago == "por_hora":
            bruto = round(horas * float(emp.tarifa_hora or 0), 2)
        else:
            # prorrateo mensual simple por días del periodo / 30
            dias = (p.fecha_fin - p.fecha_inicio).days + 1
            bruto = round((float(emp.salario_mensual or 0) * dias) / 30.0, 2)

        ded_map = {}
        base_ded = bruto
        for r in (conf.reglas_deducciones or []):
            if r.get("tipo") == "porcentaje":
                monto = round(base_ded * float(r.get("valor",0))/100.0, 2)
            else:
                monto = round(float(r.get("valor",0)), 2)
            ded_map[r.get("nombre","Deducción")] = monto
            if r.get("base","bruto") == "pre-neta":
                base_ded = max(0.0, base_ded - monto)

        imp_map = {}
        base_imp = bruto - sum(ded_map.values())
        for r in (conf.reglas_impuestos or []):
            if r.get("tipo") == "porcentaje":
                monto = round(base_imp * float(r.get("valor",0))/100.0, 2)
            else:
                monto = round(float(r.get("valor",0)), 2)
            imp_map[r.get("nombre","Impuesto")] = monto

        neto = round(bruto - sum(ded_map.values()) - sum(imp_map.values()), 2)

        item = NominaItem(
            periodo_id=pid, empleado_id=emp.id,
            horas_trabajadas=horas,
            salario_bruto=bruto,
            deducciones=ded_map,
            impuestos=imp_map,
            salario_neto=neto
        )
        db.session.add(item)
    p.estado = "calculado"
    db.session.commit()
    flash("Nómina calculada", "success")
    return redirect(url_for("nomina_detalle", pid=pid))

@app.route("/periodos/<int:pid>")
def nomina_detalle(pid):
    p = PeriodoNomina.query.get_or_404(pid)
    items = NominaItem.query.filter_by(periodo_id=pid).all()
    conf = Configuracion.query.first()
    total_bruto = sum(i.salario_bruto for i in items)
    total_dedu = sum(sum(i.deducciones.values()) for i in items)
    total_imp = sum(sum(i.impuestos.values()) for i in items)
    total_neto = sum(i.salario_neto for i in items)
    return render_template("nomina_detalle.html", p=p, items=items, conf=conf,
                           total_bruto=total_bruto, total_dedu=total_dedu, total_imp=total_imp, total_neto=total_neto)

@app.route("/periodos/<int:pid>/csv")
def nomina_csv(pid):
    p = PeriodoNomina.query.get_or_404(pid)
    items = NominaItem.query.filter_by(periodo_id=pid).all()
    rows = []
    for i in items:
        row = {
            "Empleado": f"{i.empleado.nombres} {i.empleado.apellidos}",
            "Horas": i.horas_trabajadas,
            "Bruto": i.salario_bruto,
            "Neto": i.salario_neto
        }
        for k,v in (i.deducciones or {}).items():
            row[f"Ded: {k}"] = v
        for k,v in (i.impuestos or {}).items():
            row[f"Imp: {k}"] = v
        rows.append(row)
    df = pd.DataFrame(rows)
    csv_buf = StringIO()
    df.to_csv(csv_buf, index=False)
    csv_buf.seek(0)
    return send_file(
        io.BytesIO(csv_buf.getvalue().encode("utf-8")),
        as_attachment=True, download_name=f"nomina_{p.id}.csv",
        mimetype="text/csv"
    )

# ---------- CONFIG ----------
@app.route("/config", methods=["GET","POST"])
def config():
    conf = Configuracion.query.first()
    if request.method == "POST":
        foto_path = _save_foto(request.files.get('foto'))
        foto_path = _save_foto(request.files.get('foto'))
        conf.moneda = request.form.get("moneda") or "L"
        conf.reglas_deducciones = _parse_reglas(request.form.get("reglas_deducciones_json") or "[]")
        conf.reglas_impuestos = _parse_reglas(request.form.get("reglas_impuestos_json") or "[]")
        db.session.commit()
        flash("Configuración guardada", "success")
        return redirect(url_for("config"))
    return render_template("config.html", conf=conf)

def _parse_reglas(js):
    try:
        data = pd.read_json(StringIO(js)).to_dict(orient="records")
        # saneamiento mínimo
        out = []
        for r in data:
            out.append({
                "nombre": str(r.get("nombre","Regla")).strip()[:50],
                "tipo": "porcentaje" if str(r.get("tipo","porcentaje")).startswith("porc") else "fijo",
                "valor": float(r.get("valor",0)),
                "base": "pre-neta" if "pre" in str(r.get("base","bruto")) else "bruto"
            })
        return out
    except Exception as e:
        return []

# ---------- REPORTES ----------
@app.route("/reportes")
def reportes():
    # filtros
    desde = request.args.get("desde") or (date.today().replace(day=1)).isoformat()
    hasta = request.args.get("hasta") or date.today().isoformat()

    # asistencia agregada
    rows = db.session.query(
        Empleado.id, Empleado.nombres, Empleado.apellidos,
        func.sum(
            (func.julianday(func.datetime(Asistencia.fecha, Asistencia.hora_salida)) -
             func.julianday(func.datetime(Asistencia.fecha, Asistencia.hora_entrada))) * 24.0
        ).label("horas"),
        func.sum(Asistencia.minutos_tarde).label("min_tarde")
    ).join(Asistencia, Asistencia.empleado_id==Empleado.id, isouter=True)     .filter(Asistencia.fecha.between(desde, hasta))     .group_by(Empleado.id)     .all()

    data = [{
        "Empleado": f"{r[1]} {r[2]}",
        "Horas Trabajadas": round(r[3] or 0, 2),
        "Min. Tarde": int(r[4] or 0)
    } for r in rows]

    # ranking puntualidad (menos min_tarde mejor)
    ranking = sorted(data, key=lambda x: x["Min. Tarde"])

    return render_template("reportes.html", data=data, ranking=ranking, desde=desde, hasta=hasta)

if __name__ == "__main__":
    app.run(debug=True)


def _save_foto(file):
    if not file or file.filename.strip()=="":
        return None
    ext = os.path.splitext(file.filename.lower())[1]
    if ext not in ALLOWED_EXTENSIONS:
        return None
    fname = datetime.now().strftime("%Y%m%d%H%M%S") + "_" + secure_filename(file.filename)
    path = os.path.join(app.config['UPLOAD_FOLDER'], fname)
    file.save(path)
    return path.replace('static/','/static/')


@app.route('/biometria/test')
def biometria_test():
    conf = Configuracion.query.first()
    ok = bool((conf.bio_provider or '').strip() and (conf.bio_api_base or '').strip())
    msg = 'Configuración biométrica incompleta' if not ok else f"Proveedor: {conf.bio_provider} — Base: {conf.bio_api_base}"
    return msg, (200 if ok else 400)
