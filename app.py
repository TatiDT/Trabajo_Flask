import pymysql
from flask import Flask, render_template, request, redirect, url_for, g

app = Flask(__name__)

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

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None and not db._closed:
        db.close()

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
        cursor.execute(
            "INSERT INTO camiones (patente, modelo, estado, kilometraje) VALUES (%s, %s, %s, %s)",
            (patente, modelo, estado, kilometraje)
        )
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
        if error:
            # Obtener el mantenimiento actual y la lista de elementos correspondiente
            cursor.execute("SELECT * FROM mantenimientos WHERE id = %s", (id,))
            mantenimiento = cursor.fetchone()
            # Obtener lista de camiones o equipos según el tipo
            if tipo_referencia == 'camion':
                cursor.execute("SELECT id, patente, modelo FROM camiones ORDER BY patente")
                elementos = cursor.fetchall()
                template = 'nuevo_mantenimiento_camion.html'
            else:
                cursor.execute("SELECT id, tipo, modelo, origen FROM equipos ORDER BY tipo, modelo")
                elementos = cursor.fetchall()
                template = 'nuevo_mantenimiento_equipo.html'
            cursor.close()
            return render_template(template, 
                                 elementos=elementos, 
                                 mantenimiento=mantenimiento, 
                                 editando=True, 
                                 error=error)
        
        # Actualizar
        cursor.execute("""
            UPDATE mantenimientos 
            SET referencia_id=%s, fecha_inicio=%s, fecha_fin=%s, descripcion=%s
            WHERE id=%s
        """, (referencia_id, fecha_inicio, fecha_fin, descripcion, id))
        db.commit()
        cursor.close()
        return redirect(url_for('mantenimiento'))
    else:
        cursor.execute("SELECT * FROM mantenimientos WHERE id = %s", (id,))
        mantenimiento = cursor.fetchone()
        if mantenimiento is None:
            return redirect(url_for('mantenimiento'))
        # Obtener lista de elementos según el tipo
        if mantenimiento['tipo_referencia'] == 'camion':
            cursor.execute("SELECT id, patente, modelo FROM camiones ORDER BY patente")
            elementos = cursor.fetchall()
            template = 'nuevo_mantenimiento_camion.html'
        else:
            cursor.execute("SELECT id, tipo, modelo, origen FROM equipos ORDER BY tipo, modelo")
            elementos = cursor.fetchall()
            template = 'nuevo_mantenimiento_equipo.html'
        cursor.close()
        return render_template(template, 
                             elementos=elementos, 
                             mantenimiento=mantenimiento, 
                             editando=True)

@app.route('/mantenimiento/<int:id>/eliminar', methods=['POST'])
def eliminar_mantenimiento(id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM mantenimientos WHERE id = %s", (id,))
    db.commit()
    cursor.close()
    return redirect(url_for('mantenimiento'))

if __name__ == '__main__':
    app.run(debug=True, port=5001)