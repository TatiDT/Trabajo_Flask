import pytest
from unittest.mock import patch, MagicMock

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# TEST 1: crear_alerta

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



# TEST 2: mantenimiento (CREA alerta)

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



# TEST 3: mantenimiento (NO crea alerta)

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



# TEST 4: alerta por temperatura

@patch('app.get_db')
@patch('app.crear_alerta')
def test_alerta_temperatura(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    mock_cursor.fetchone.return_value = {
        'patente': 'ABC123'
    }

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_temperatura', data={
            'camion_id': 1,
            'temperatura': '100'
        })

    mock_crear_alerta.assert_called_once()



# TEST 5: alerta de ubicación

@patch('app.get_db')
@patch('app.crear_alerta')
def test_alerta_ubicacion(mock_crear_alerta, mock_get_db):

    mock_db = MagicMock()
    mock_cursor = MagicMock()

    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    # Simula SELECT del camión
    mock_cursor.fetchone.return_value = {
        'patente': 'ABC123'
    }

    from app import app

    with app.test_client() as client:
        client.post('/actualizar_ubicacion', data={
            'camion_id': 1,
            'ubicacion': 'Argentina'
        })

    mock_crear_alerta.assert_called_once()