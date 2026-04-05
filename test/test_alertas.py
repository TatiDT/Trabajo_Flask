import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ===========================================================================
# TEST 1: crear_alerta inserta en BD y hace commit
# ===========================================================================

@patch('app.get_db')
def test_crear_alerta(mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import crear_alerta

    crear_alerta(1, 'temperatura', 'Alerta crítica', '100')

    mock_cursor.execute.assert_called_once()
    mock_db.commit.assert_called_once()
    mock_cursor.close.assert_called_once()



# ===========================================================================
# TEST 2: verificar_alerta_mantenimiento CREA alerta (sin alerta previa)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_verificar_mantenimiento_crea(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # No existe alerta previa
    mock_cursor.fetchone.return_value = None

    from app import verificar_alerta_mantenimiento

    camion = {
        'id': 1,
        'patente': 'ABC123',
        'kilometraje': 6000,
        'ultimo_mantenimiento_km': 0
    }

    verificar_alerta_mantenimiento(camion)

    mock_crear_alerta.assert_called_once()



# ===========================================================================
# TEST 3: verificar_alerta_mantenimiento NO crea alerta (ya existe una)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_verificar_mantenimiento_no_crea(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # Ya existe alerta
    mock_cursor.fetchone.return_value = {'id': 1}

    from app import verificar_alerta_mantenimiento

    camion = {
        'id': 1,
        'patente': 'ABC123',
        'kilometraje': 6000,
        'ultimo_mantenimiento_km': 0
    }

    verificar_alerta_mantenimiento(camion)

    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 4: alerta por temperatura (CREA alerta cuando temp >= 95)
# CORREGIDO: ahora hay 2 llamadas a fetchone (camion + chequeo deduplicacion)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_alerta_temperatura(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # 1ra llamada: devuelve el camion. 2da llamada: no hay alerta previa (deduplicacion)
    mock_cursor.fetchone.side_effect = [
        {'patente': 'ABC123'},
        None
    ]

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_temperatura', data={
            'camion_id': 1,
            'temperatura': '100'
        })

    mock_crear_alerta.assert_called_once()



# ===========================================================================
# TEST 5: alerta de ubicacion (CREA alerta cuando zona no permitida)
# CORREGIDO: ahora hay 2 llamadas a fetchone (camion + chequeo deduplicacion)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_alerta_ubicacion(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # 1ra llamada: devuelve el camion. 2da llamada: no hay alerta previa (deduplicacion)
    mock_cursor.fetchone.side_effect = [
        {'patente': 'ABC123'},
        None
    ]

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_ubicacion', data={
            'camion_id': 1,
            'ubicacion': 'Argentina'
        })

    mock_crear_alerta.assert_called_once()



# ===========================================================================
# TEST 6: alerta de combustible (CREA alerta cuando total acumulado > 30)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_alerta_combustible(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # 1ra llamada: camion con total acumulado > 30. 2da: no hay alerta previa
    mock_cursor.fetchone.side_effect = [
        {'patente': 'ABC123', 'combustible_usado': 50},
        None
    ]

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_combustible', data={
            'camion_id': 1,
            'combustible': '20'
        })

    mock_crear_alerta.assert_called_once()



# ===========================================================================
# TEST 7: NO crea alerta de temperatura si ya existe una sin leer (deduplicacion)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_no_alerta_temperatura_duplicada(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # 1ra llamada: el camion. 2da llamada: ya existe una alerta sin leer
    mock_cursor.fetchone.side_effect = [
        {'patente': 'ABC123'},
        {'id': 5}
    ]

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_temperatura', data={
            'camion_id': 1,
            'temperatura': '100'
        })

    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 8: NO crea alerta de ubicacion si ya existe una para esa ubicacion (deduplicacion)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_no_alerta_ubicacion_duplicada(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # 1ra llamada: el camion. 2da llamada: ya existe una alerta sin leer para esa ubicacion
    mock_cursor.fetchone.side_effect = [
        {'patente': 'ABC123'},
        {'id': 3}
    ]

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_ubicacion', data={
            'camion_id': 1,
            'ubicacion': 'Argentina'
        })

    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 9: NO crea alerta de combustible si ya existe una sin leer (deduplicacion)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_no_alerta_combustible_duplicada(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # 1ra llamada: camion con total > 30. 2da llamada: ya existe alerta sin leer
    mock_cursor.fetchone.side_effect = [
        {'patente': 'ABC123', 'combustible_usado': 50},
        {'id': 7}
    ]

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_combustible', data={
            'camion_id': 1,
            'combustible': '20'
        })

    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 10: ubicacion en minusculas NO genera alerta (comparacion case-insensitive)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_ubicacion_minusculas_no_alerta(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # Solo hay una llamada a fetchone (el camion), no llega al chequeo de alerta
    mock_cursor.fetchone.return_value = {'patente': 'ABC123'}

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_ubicacion', data={
            'camion_id': 1,
            'ubicacion': 'santiago'  # minusculas, debe ser aceptado igual que 'Santiago'
        })

    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 11: temperatura negativa NO se guarda (fuera de rango valido)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_temperatura_negativa_invalida(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app

    with app.test_client() as client:
        response = client.post('/actualizar_temperatura', data={
            'camion_id': 1,
            'temperatura': '-10'
        })

    # Redirige sin guardar nada
    assert response.status_code == 302
    mock_db.commit.assert_not_called()
    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 12: temperatura sobre 200 NO se guarda (fuera de rango valido)
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_temperatura_sobre_limite_invalida(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app

    with app.test_client() as client:
        response = client.post('/actualizar_temperatura', data={
            'camion_id': 1,
            'temperatura': '250'
        })

    assert response.status_code == 302
    mock_db.commit.assert_not_called()
    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 13: combustible negativo NO se guarda
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_combustible_negativo_invalido(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app

    with app.test_client() as client:
        response = client.post('/actualizar_combustible', data={
            'camion_id': 1,
            'combustible': '-15'
        })

    assert response.status_code == 302
    mock_db.commit.assert_not_called()
    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 14: combustible en cero NO se guarda
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_combustible_cero_invalido(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app

    with app.test_client() as client:
        response = client.post('/actualizar_combustible', data={
            'camion_id': 1,
            'combustible': '0'
        })

    assert response.status_code == 302
    mock_db.commit.assert_not_called()
    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 15: ubicacion vacia NO se guarda
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_ubicacion_vacia_invalida(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app

    with app.test_client() as client:
        response = client.post('/actualizar_ubicacion', data={
            'camion_id': 1,
            'ubicacion': ''
        })

    assert response.status_code == 302
    mock_db.commit.assert_not_called()
    mock_crear_alerta.assert_not_called()



# ===========================================================================
# TEST 16: patente duplicada al crear camion muestra error (no inserta en BD)
# ===========================================================================

@patch('app.get_db')
def test_patente_duplicada_crear(mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # fetchone devuelve un camion existente con esa patente
    mock_cursor.fetchone.return_value = {'id': 1}

    from app import app

    with app.test_client() as client:
        response = client.post('/camiones/nuevo', data={
            'patente': 'ABC123',
            'modelo': 'Volvo FH',
            'estado': 'Disponible',
            'kilometraje': '10000'
        })

    assert response.status_code == 200
    assert 'Ya existe un camión con la patente ABC123'.encode() in response.data
    mock_db.commit.assert_not_called()



# ===========================================================================
# TEST 17: estado invalido al crear camion muestra error (no inserta en BD)
# ===========================================================================

@patch('app.get_db')
def test_estado_invalido_crear(mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app

    with app.test_client() as client:
        response = client.post('/camiones/nuevo', data={
            'patente': 'XYZ999',
            'modelo': 'Mercedes Actros',
            'estado': 'Volando',  # estado que no existe
            'kilometraje': '5000'
        })

    assert response.status_code == 200
    assert 'Estado no válido'.encode() in response.data
    mock_db.commit.assert_not_called()



# ===========================================================================
# TEST 18: verificar_alerta_mantenimiento usa km_actual en vez del km del dict
# Verifica el fix del Bug 1: el scheduler pasaba el km viejo
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_verificar_mantenimiento_km_actual_override(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # Sin override: 4900 km → multiplos = 0 → no crea alerta
    mock_cursor.fetchone.return_value = None

    from app import verificar_alerta_mantenimiento

    camion = {'id': 1, 'patente': 'ABC123', 'kilometraje': 4900}

    verificar_alerta_mantenimiento(camion)
    mock_crear_alerta.assert_not_called()

    # Con override de 5100 km → multiplos = 1 → SÍ crea alerta para umbral 5000
    verificar_alerta_mantenimiento(camion, km_actual=5100)
    mock_crear_alerta.assert_called_once()



# ===========================================================================
# TEST 19: verificar_alerta_mantenimiento genera alertas para MULTIPLES umbrales
# Ej: 12300 km → umbrales 5000 y 10000 → 2 alertas
# ===========================================================================

@patch('app.get_db')
@patch('app.crear_alerta')
def test_verificar_mantenimiento_multiples_umbrales(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # Ninguno de los dos umbrales tiene alerta previa
    mock_cursor.fetchone.side_effect = [None, None]

    from app import verificar_alerta_mantenimiento

    camion = {'id': 1, 'patente': 'ABC123', 'kilometraje': 12300}

    verificar_alerta_mantenimiento(camion)

    # Debe crear 2 alertas: una para 5000 km y otra para 10000 km
    assert mock_crear_alerta.call_count == 2
