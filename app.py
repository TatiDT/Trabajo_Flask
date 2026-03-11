from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')
@app.route('/camiones')
def camiones():
    return render_template('camiones.html')
@app.route('/mantenimiento')
def mantenimiento():
    return render_template('mantenimiento.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
