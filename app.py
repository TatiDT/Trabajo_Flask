from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime, timedelta
import mysql.connector

app = Flask(__name__)

camiones = [ 
    {'id': 1, 'modelo': 'Volvo FH16', 'patente': 'AAA111', 'estado': 'En ruta', 'kilometraje': 150000},
    {'id': 2, 'modelo': 'Scania R500', 'patente': 'BBB222', 'estado': 'En mantenimiento', 'kilometraje': 120000},
    {'id': 3, 'modelo': 'Mercedes-Benz Actros', 'patente': 'CCC333', 'estado': 'Disponible', 'kilometraje': 80000},   #DATOS DE EJEMPLO DESPUES BORRAR 
]
    
@app.route('/')
def index():
    return render_template('index.html')
    
    

@app.route('/camiones')
def lista_camiones():
    return render_template('camiones.html', camiones=camiones)

@app.route('/camiones/nuevo', methods=['GET', 'POST'])
def nuevo_camion():
    if request.method == 'POST':
        # Crear nuevo camión
        nuevo_id = len(camiones) + 1
        nuevo_camion = {
            'id': nuevo_id,
            'modelo': request.form['modelo'],
            'patente': request.form['patente'],
            'estado': request.form['estado'],
            'kilometraje': int(request.form['kilometraje'])
        }
        camiones.append(nuevo_camion)
        return redirect(url_for('lista_camiones'))
    
    return render_template('nuevo_camion.html')

@app.route('/mantenimiento')
def mantenimiento():
    return render_template('mantenimiento.html')



if __name__ == '__main__':
    app.run(debug=True, port=5001)


