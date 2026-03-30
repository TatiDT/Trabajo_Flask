import pymysql
from flask import Flask, render_template, request, redirect, url_for, g

from apscheduler.schedulers.background import BackgroundScheduler
import random
import atexit

app = Flask(__name__)

scheduler = BackgroundScheduler() 


app.config['DB_HOST'] = 'localhost'
app.config['DB_USER'] = 'root'
app.config['DB_PASSWORD'] = ''
app.config['DB_NAME'] = 'hirata'                                        #falta la logica de que los camiones cambien su estado a "en mantenimiento" cuando se les asigna un mantenimiento activo
                                                                        #y que vuelvan a "disponible" cuando el mantenimiento se completa (fecha_fin se llena)

def get_db():
    if 'db' not in g:
        g.db = pymysql.connect(
            host=app.config['DB_HOST'],
            user=app.config['DB_USER'],
            password=app.config['DB_PASSWORD'],
            database=app.config['DB_NAME'],
            cursorclass=pymysql.cursors.DictCursor
        )
    return g.db

@app.context_processor
def inject_alertas():
    try:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT a.*, c.patente 
            FROM alertas a
            JOIN camiones c ON a.camion_id = c.id
            WHERE a.leida = 0
            ORDER BY a.fecha_creacion DESC
        """)
        alertas = cursor.fetchall()  #fetchall recoge todas las filas que resultan de la consulta y las devuelve como una lista de diccionarios (gracias a DictCursor)
        cursor.close()
        return dict(alertas_no_leidas=alertas) #DEBE retornar un diccionario con la clave 'alertas_no_leidas' para que esté disponible en todas las plantillas como variable global
    except:
        return dict(alertas_no_leidas=[])


def crear_alerta(camion_id, tipo, mensaje, datos_adicionales=None):
    db= get_db()
    cursor = db.cursor()
    query = """ INSERT INTO alertas (camion_id, tipo, mensaje, datos_adicionales) VALUES (%s, %s, %s, %s) """
    cursor.execute(query, (camion_id, tipo, mensaje, datos_adicionales))
    db.commit()
    cursor.close()

def verificar_alerta_mantenimiento(camion):
    km_actual = camion['kilometraje']
    ultimo_mantenimiento = camion['ultimo_mantenimiento_km']
    necesita_mantenimiento = km_actual - ultimo_mantenimiento >= 5000
    if necesita_mantenimiento:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""SELECT id FROM alertas WHERE camion_id=%s AND tipo='mantenimiento' AND leida=0""", (camion['id'],))
        
        existe = cursor.fetchone()  #fetchone pide cursor que recoja solo la primera fila luego se detiene
        cursor.close()
        if not existe:
            mensaje = f"El camión {camion['patente']} ha alcanzado {km_actual} km y requiere mantenimiento preventivo."
            crear_alerta(camion['id'], 'mantenimiento', mensaje)


def actualizar_kilometraje_automatico():
    with app.app_context():
        db= get_db()
        cursor = db.cursor()
        cursor.execute("""
            SELECT id, kilometraje, ultimo_mantenimiento_km, patente 
            FROM camiones WHERE estado = 'En ruta'
        """)
        camiones = cursor.fetchall()

        for camion in camiones:
            incremento = random.randint(50, 200)
            nuevo_km = camion['kilometraje'] + incremento
            cursor.execute("UPDATE camiones SET kilometraje = %s WHERE id = %s", (nuevo_km, camion['id']))
            verificar_alerta_mantenimiento(camion)
        db.commit()
        cursor.close()
    


def apagar_scheduler():
    scheduler.shutdown()

atexit.register(apagar_scheduler)
scheduler.add_job(func=actualizar_kilometraje_automatico, trigger="interval", seconds=5)
scheduler.start()

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None and not db._closed:
        db.close()

@app.route('/alerta/<int:id>/leer', methods=['POST'])
def marcar_alerta_leida(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE alertas SET leida = 1 WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    
    return redirect(request.referrer or url_for('lista_camiones'))

@app.route('/sensores')
def sensores():
    db = get_db()
    cursor = db.cursor()
    
    
    cursor.execute("SELECT * FROM camiones")
    camiones = cursor.fetchall()
    
    cursor.execute("SELECT * FROM camiones WHERE estado = 'En ruta'")
    camiones_ruta = cursor.fetchall()
    
    cursor.close()
    return render_template('sensores.html', camiones=camiones, camiones_ruta=camiones_ruta)


ZONAS_PERMITIDAS = ['Santiago', 'Valparaíso', 'Concepción', 'Ruta 68', 'Ruta 5', 'Viña del Mar']

@app.route('/actualizar_ubicacion', methods=['POST'])
def actualizar_ubicacion():
    camion_id = request.form.get('camion_id')
    nueva_ubicacion = request.form.get('ubicacion', '').strip()
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE camiones SET ubicacion_actual = %s WHERE id = %s", (nueva_ubicacion, camion_id))
    
    cursor.execute("SELECT * FROM camiones WHERE id = %s", (camion_id,))
    camion = cursor.fetchone()
    
    
    if nueva_ubicacion not in ZONAS_PERMITIDAS:
        mensaje = f"El camión {camion['patente']} salió de la zona permitida (ubicación: {nueva_ubicacion})"
        crear_alerta(camion_id, 'ubicacion', mensaje, nueva_ubicacion)
    
    db.commit()
    cursor.close()
    return redirect(url_for('sensores'))

@app.route('/actualizar_temperatura', methods=['POST'])
def actualizar_temperatura():
    camion_id = request.form.get('camion_id') #guarda el dato de la plantilla html que se llama camion_id (que es un input hidden) para saber a qué camión actualizarle la temperatura
    nueva_temp = request.form.get('temperatura', '').strip() #strip() para eliminar espacios antes o después del número, por si el usuario los ingresa sin querer. Si no se ingresa nada, se guarda como cadena vacía '' y luego el try except lo detecta como error de conversión a float y redirige sin actualizar nada. Esto evita que se guarde un valor no numérico en la base de datos.
    
    try:
        nueva_temp = float(nueva_temp)
    except ValueError:
        return redirect(url_for('sensores'))
    
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE camiones SET temperatura_motor = %s WHERE id = %s", (nueva_temp, camion_id))
    
    
    cursor.execute("SELECT * FROM camiones WHERE id = %s", (camion_id,))
    camion = cursor.fetchone()
    
    
    if nueva_temp >= 95:
        mensaje = f"El camión {camion['patente']} tiene temperatura critica: {nueva_temp}°C"
        crear_alerta(camion_id, 'temperatura', mensaje, str(nueva_temp))
    
    db.commit()
    cursor.close()
    return redirect(url_for('sensores'))

@app.route('/actualizar_combustible', methods=['POST'])
def actualizar_combustible():
    camion_id = request.form.get('camion_id')
    litros = request.form.get('combustible', '').strip()
    
    try:
        litros = float(litros)
    except ValueError:
        return redirect(url_for('sensores'))
    
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("UPDATE camiones SET combustible_usado = COALESCE(combustible_usado,0) + %s WHERE id = %s", (litros, camion_id))
    db.commit()
    cursor.close()
    return redirect(url_for('sensores'))


@app.route('/')
def index():
    return redirect(url_for('lista_camiones'))

@app.route('/camiones')
def lista_camiones():
    busqueda = request.args.get('buscar', '').strip()
    db = get_db()
    cursor = db.cursor()
    
    if busqueda:
        like = f'%{busqueda}%'
        cursor.execute(
            "SELECT * FROM camiones WHERE patente LIKE %s OR modelo LIKE %s",
            (like, like)
        )
    else:
        cursor.execute("SELECT * FROM camiones")
    
    camiones = cursor.fetchall()
    cursor.close()
    return render_template('camiones.html', camiones=camiones, busqueda=busqueda)

@app.route('/camiones/nuevo', methods=['GET', 'POST'])
def nuevo_camion():
    if request.method == 'POST':
        patente = request.form.get('patente', '').strip().upper()
        modelo = request.form.get('modelo', '').strip()
        estado = request.form.get('estado', '').strip()
        kilometraje = request.form.get('kilometraje', '').strip()
        
        error = None
        if not patente or not modelo or not estado or not kilometraje:
            error = "Todos los campos son obligatorios."
        else:
            try:
                kilometraje = int(kilometraje)
                if kilometraje < 0:
                    error = "El kilometraje no puede ser negativo."
            except ValueError:
                error = "El kilometraje debe ser un número entero."
        
        if error:
            return render_template('nuevo_camion.html', error=error)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO camiones (patente, modelo, estado, kilometraje, ultimo_mantenimiento_km)
            VALUES (%s, %s, %s, %s, %s)
        """, (patente, modelo, estado, kilometraje, kilometraje))  
        db.commit()
        cursor.close()
        return redirect(url_for('lista_camiones'))
    
    return render_template('nuevo_camion.html')

@app.route('/equipos')
def lista_equipos():
    busqueda = request.args.get('buscar', '').strip()
    db = get_db()
    cursor = db.cursor()
    
    if busqueda:
        like = f'%{busqueda}%'
        cursor.execute(
            "SELECT * FROM equipos WHERE tipo LIKE %s OR modelo LIKE %s OR origen LIKE %s",
            (like, like, like)
        )
    else:
        cursor.execute("SELECT * FROM equipos")
    
    equipos = cursor.fetchall()
    cursor.close()
    return render_template('equipos.html', equipos=equipos, busqueda=busqueda)

@app.route('/equipos/nuevo', methods=['GET', 'POST'])
def nuevo_equipo():
    if request.method == 'POST':
        tipo = request.form.get('tipo', '').strip()
        modelo = request.form.get('modelo', '').strip()
        origen = request.form.get('origen', '').strip()
        
        error = None
        if not tipo or not modelo or not origen:
            error = "Todos los campos son obligatorios."
        
        if error:
            return render_template('nuevo_equipo.html', error=error)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute(
            "INSERT INTO equipos (tipo, modelo, origen) VALUES (%s, %s, %s)",
            (tipo, modelo, origen)
        )
        db.commit()
        cursor.close()
        return redirect(url_for('lista_equipos'))
    
    return render_template('nuevo_equipo.html')

@app.route('/mantenimiento')
def mantenimiento():
    """Lista todos los mantenimientos con información del elemento asociado."""
    busqueda = request.args.get('buscar', '').strip()
    db = get_db()
    cursor = db.cursor()
    
    
    query = """
        SELECT 
            m.*,
            CASE 
                WHEN m.tipo_referencia = 'camion' THEN c.patente
                WHEN m.tipo_referencia = 'equipo' THEN CONCAT(e.tipo, ' ', e.modelo)
            END as elemento_nombre
        FROM mantenimientos m
        LEFT JOIN camiones c ON m.tipo_referencia = 'camion' AND m.referencia_id = c.id
        LEFT JOIN equipos e ON m.tipo_referencia = 'equipo' AND m.referencia_id = e.id
    """
    
    if busqueda:
        like = f'%{busqueda}%'
        query += " WHERE m.descripcion LIKE %s OR fecha_inicio LIKE %s OR fecha_fin LIKE %s"
        cursor.execute(query, (like, like, like))
    else:
        cursor.execute(query)
    
    mantenimientos = cursor.fetchall()
    cursor.close()
    return render_template('mantenimiento.html', mantenimientos=mantenimientos, busqueda=busqueda)


@app.route('/mantenimiento/nuevo/camion', methods=['GET', 'POST'])
def nuevo_mantenimiento_camion():
    """Formulario para agregar mantenimiento a un camión."""
    db = get_db()
    cursor = db.cursor()
    
    
    cursor.execute("SELECT id, patente, modelo FROM camiones ORDER BY patente")
    camiones = cursor.fetchall()
    cursor.close()
    
    if request.method == 'POST':
        referencia_id = request.form.get('referencia_id', '').strip()
        fecha_inicio = request.form.get('fecha_inicio', '').strip()
        fecha_fin = request.form.get('fecha_fin', '').strip() or None  
        descripcion = request.form.get('descripcion', '').strip()
        
        error = None
        if not referencia_id or not fecha_inicio or not descripcion:
            error = "Todos los campos excepto fecha fin son obligatorios."
        elif fecha_fin and fecha_fin < fecha_inicio:
            error = "La fecha de fin no puede ser anterior a la fecha de inicio."
        
        if error:
            return render_template('nuevo_mantenimiento_camion.html', camiones=camiones, error=error)
        
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO mantenimientos (tipo_referencia, referencia_id, fecha_inicio, fecha_fin, descripcion)
            VALUES ('camion', %s, %s, %s, %s)
        """, (referencia_id, fecha_inicio, fecha_fin, descripcion))
        db.commit()
        cursor.close()
        return redirect(url_for('mantenimiento'))
    return render_template('nuevo_mantenimiento_camion.html', camiones=camiones)


@app.route('/mantenimiento/nuevo/equipo', methods=['GET', 'POST'])
def nuevo_mantenimiento_equipo():
    """Formulario para agregar mantenimiento a un equipo."""
    db = get_db()
    cursor = db.cursor()
    
    
    cursor.execute("SELECT id, tipo, modelo, origen FROM equipos ORDER BY tipo, modelo")
    equipos = cursor.fetchall()
    cursor.close()
    
    if request.method == 'POST':
        referencia_id = request.form.get('referencia_id', '').strip()
        fecha_inicio = request.form.get('fecha_inicio', '').strip()
        fecha_fin = request.form.get('fecha_fin', '').strip() or None
        descripcion = request.form.get('descripcion', '').strip()
        
        error = None
        if not referencia_id or not fecha_inicio or not descripcion:
            error = "Todos los campos excepto fecha fin son obligatorios."
        elif fecha_fin and fecha_fin < fecha_inicio:
            error = "La fecha de fin no puede ser anterior a la fecha de inicio."
        
        if error:
            return render_template('nuevo_mantenimiento_equipo.html', equipos=equipos, error=error)
        
        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO mantenimientos (tipo_referencia, referencia_id, fecha_inicio, fecha_fin, descripcion)
            VALUES ('equipo', %s, %s, %s, %s)
        """, (referencia_id, fecha_inicio, fecha_fin, descripcion))
        db.commit()
        cursor.close()
        return redirect(url_for('mantenimiento'))
    
    return render_template('nuevo_mantenimiento_equipo.html', equipos=equipos)

@app.route('/camiones/<int:id>/editar', methods=['GET', 'POST'])
def editar_camion(id):
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        patente = request.form.get('patente', '').strip().upper()
        modelo = request.form.get('modelo', '').strip()
        estado = request.form.get('estado', '').strip()
        kilometraje = request.form.get('kilometraje', '').strip()
        
        # Validaciones
        error = None
        if not patente or not modelo or not estado or not kilometraje:
            error = "Todos los campos son obligatorios."
        else:
            try:
                kilometraje = int(kilometraje)
                if kilometraje < 0:
                    error = "El kilometraje no puede ser negativo."
            except ValueError:
                error = "El kilometraje debe ser un número entero."
        
        if error:
            # Obtener el camión actual para mostrarlo en el formulario
            cursor.execute("SELECT * FROM camiones WHERE id = %s", (id,))
            camion = cursor.fetchone()
            cursor.close()
            return render_template('nuevo_camion.html', camion=camion, editando=True, error=error)
        
        # Actualizar
        cursor.execute("""
            UPDATE camiones SET patente=%s, modelo=%s, estado=%s, kilometraje=%s
            WHERE id=%s
        """, (patente, modelo, estado, kilometraje, id))
        db.commit()
        cursor.close()
        return redirect(url_for('lista_camiones'))
    else:
        cursor.execute("SELECT * FROM camiones WHERE id = %s", (id,))
        camion = cursor.fetchone()
        cursor.close()
        if camion is None:
            return redirect(url_for('lista_camiones'))
        return render_template('nuevo_camion.html', camion=camion, editando=True)

@app.route('/camiones/<int:id>/eliminar', methods=['POST'])
def eliminar_camion(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM camiones WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('lista_camiones'))

@app.route('/equipos/<int:id>/editar', methods=['GET', 'POST'])
def editar_equipo(id):
    db = get_db()
    cursor = db.cursor()
    if request.method == 'POST':
        tipo = request.form.get('tipo', '').strip()
        modelo = request.form.get('modelo', '').strip()
        origen = request.form.get('origen', '').strip()
        error = None
        if not tipo or not modelo or not origen:
            error = "Todos los campos son obligatorios."
        if error:
            cursor.execute("SELECT * FROM equipos WHERE id = %s", (id,))
            equipo = cursor.fetchone()
            cursor.close()
            return render_template('nuevo_equipo.html', equipo=equipo, editando=True, error=error)
        cursor.execute("""
            UPDATE equipos SET tipo=%s, modelo=%s, origen=%s
            WHERE id=%s
        """, (tipo, modelo, origen, id))
        db.commit()
        cursor.close()
        return redirect(url_for('lista_equipos'))
    else:
        cursor.execute("SELECT * FROM equipos WHERE id = %s", (id,))
        equipo = cursor.fetchone()
        cursor.close()
        if equipo is None:
            return redirect(url_for('lista_equipos'))
        return render_template('nuevo_equipo.html', equipo=equipo, editando=True)

@app.route('/equipos/<int:id>/eliminar', methods=['POST'])
def eliminar_equipo(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM equipos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('lista_equipos'))

@app.route('/mantenimiento/<int:id>/editar', methods=['GET', 'POST'])
def editar_mantenimiento(id):
    db = get_db()
    cursor = db.cursor()

    
    cursor.execute("SELECT * FROM mantenimientos WHERE id = %s", (id,))
    mantenimiento = cursor.fetchone()

    if mantenimiento is None:
        cursor.close()
        return redirect(url_for('mantenimiento'))

    if request.method == 'POST':
        referencia_id = request.form.get('referencia_id', '').strip()
        fecha_inicio = request.form.get('fecha_inicio', '').strip()
        fecha_fin = request.form.get('fecha_fin', '').strip() or None
        descripcion = request.form.get('descripcion', '').strip()
        tipo_referencia = request.form.get('tipo_referencia', '')

        error = None

        if not referencia_id or not fecha_inicio or not descripcion:
            error = "Todos los campos excepto fecha fin son obligatorios."
        elif fecha_fin and fecha_fin < fecha_inicio:
            error = "La fecha de fin no puede ser anterior a la fecha de inicio."

        if not error:
            cursor.execute("""
                UPDATE mantenimientos 
                SET referencia_id=%s, fecha_inicio=%s, fecha_fin=%s, descripcion=%s
                WHERE id=%s
            """, (referencia_id, fecha_inicio, fecha_fin, descripcion, id))

            db.commit()
            cursor.close()
            return redirect(url_for('mantenimiento'))

        tipo = tipo_referencia

    else:
        
        tipo = mantenimiento['tipo_referencia']

    
    if tipo == 'camion':
        cursor.execute("SELECT id, patente, modelo FROM camiones ORDER BY patente")
        elementos = cursor.fetchall()
        template = 'nuevo_mantenimiento_camion.html'
    else:
        cursor.execute("SELECT id, tipo, modelo, origen FROM equipos ORDER BY tipo, modelo")
        elementos = cursor.fetchall()
        template = 'nuevo_mantenimiento_equipo.html'

    cursor.close()

    return render_template(
        template,
        elementos=elementos,
        mantenimiento=mantenimiento,
        editando=True,
        error=error if request.method == 'POST' else None
    )

@app.route('/mantenimiento/<int:id>/eliminar', methods=['POST'])
def eliminar_mantenimiento(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM mantenimientos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('mantenimiento'))  #lerolero



if __name__ == '__main__':
    app.run(debug=True, port=5001)