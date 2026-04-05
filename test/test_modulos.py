import pytest
from unittest.mock import patch, MagicMock, call

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


# ===========================================================================
# MÓDULO: CAMIONES — GET
# ===========================================================================

@patch('app.get_db')
def test_lista_camiones_get(mock_get_db):
    """GET /camiones devuelve 200 con la lista."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/camiones')

    assert response.status_code == 200


@patch('app.get_db')
def test_nuevo_camion_get(mock_get_db):
    """GET /camiones/nuevo devuelve 200 con el formulario vacío."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/camiones/nuevo')

    assert response.status_code == 200


# ===========================================================================
# MÓDULO: CAMIONES — VALIDACIONES AL CREAR
# ===========================================================================

@patch('app.get_db')
def test_nuevo_camion_campos_vacios(mock_get_db):
    """POST /camiones/nuevo con campos vacíos muestra error, no hace commit."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/nuevo', data={
            'patente': '', 'modelo': '', 'estado': '', 'kilometraje': ''
        })

    assert response.status_code == 200
    assert 'Todos los campos son obligatorios'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_nuevo_camion_km_negativo(mock_get_db):
    """POST /camiones/nuevo con kilometraje negativo muestra error, no hace commit."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/nuevo', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'Disponible', 'kilometraje': '-100'
        })

    assert response.status_code == 200
    assert 'El kilometraje no puede ser negativo'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_nuevo_camion_km_no_numerico(mock_get_db):
    """POST /camiones/nuevo con kilometraje no numérico muestra error."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/nuevo', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'Disponible', 'kilometraje': 'abc'
        })

    assert response.status_code == 200
    assert 'El kilometraje debe ser un número entero'.encode() in response.data
    mock_db.commit.assert_not_called()


# ===========================================================================
# MÓDULO: CAMIONES — EDITAR (GET)
# ===========================================================================

@patch('app.get_db')
def test_editar_camion_get_existe(mock_get_db):
    """GET /camiones/<id>/editar con camión existente devuelve 200."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        'id': 1, 'patente': 'ABC123', 'modelo': 'Volvo FH',
        'estado': 'Disponible', 'kilometraje': 10000
    }
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/camiones/1/editar')

    assert response.status_code == 200


@patch('app.get_db')
def test_editar_camion_get_no_existe(mock_get_db):
    """GET /camiones/<id>/editar con camión inexistente redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None

    from app import app
    with app.test_client() as client:
        response = client.get('/camiones/999/editar')

    assert response.status_code == 302


# ===========================================================================
# MÓDULO: CAMIONES — EDITAR (POST / VALIDACIONES)
# ===========================================================================

@patch('app.get_db')
def test_editar_camion_estado_invalido(mock_get_db):
    """POST /camiones/<id>/editar con estado inválido muestra error."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    # fetchone para mostrar el camión en el formulario de error
    mock_cursor.fetchone.return_value = {
        'id': 1, 'patente': 'ABC123', 'modelo': 'Volvo FH',
        'estado': 'Disponible', 'kilometraje': 10000
    }
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/1/editar', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'Volando', 'kilometraje': '10000'
        })

    assert response.status_code == 200
    assert 'Estado no válido'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_editar_camion_patente_duplicada(mock_get_db):
    """POST /camiones/<id>/editar con patente de otro camión muestra error."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    # 1ra fetchone: encuentra patente duplicada en otro camión
    # 2da fetchone: devuelve camión actual para mostrarlo en formulario
    mock_cursor.fetchone.side_effect = [
        {'id': 2},
        {'id': 1, 'patente': 'ABC123', 'modelo': 'Volvo FH', 'estado': 'Disponible', 'kilometraje': 10000}
    ]
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/1/editar', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'Disponible', 'kilometraje': '10000'
        })

    assert response.status_code == 200
    assert 'Ya existe otro camión con la patente'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_editar_camion_exito(mock_get_db):
    """POST /camiones/<id>/editar con datos válidos hace commit y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    # 1ra fetchone: no hay patente duplicada
    # 2da fetchone: estado anterior del camión
    mock_cursor.fetchone.side_effect = [
        None,
        {'estado': 'Disponible'}
    ]

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/1/editar', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'En ruta', 'kilometraje': '15000'
        })

    assert response.status_code == 302
    mock_db.commit.assert_called_once()


# ===========================================================================
# MÓDULO: CAMIONES — ELIMINAR (CASCADE DELETE)
# ===========================================================================

@patch('app.get_db')
def test_eliminar_camion_cascade(mock_get_db):
    """POST /camiones/<id>/eliminar borra alertas, mantenimientos y camión."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/camiones/1/eliminar')

    assert response.status_code == 302
    mock_db.commit.assert_called_once()
    # 3 DELETEs: alertas, mantenimientos, camiones
    assert mock_cursor.execute.call_count == 3


# ===========================================================================
# MÓDULO: EQUIPOS — CRUD
# ===========================================================================

@patch('app.get_db')
def test_lista_equipos_get(mock_get_db):
    """GET /equipos devuelve 200."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/equipos')

    assert response.status_code == 200


@patch('app.get_db')
def test_nuevo_equipo_exito(mock_get_db):
    """POST /equipos/nuevo con datos válidos hace commit y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/equipos/nuevo', data={
            'tipo': 'Celular', 'modelo': 'Samsung A52', 'origen': 'oficina'
        })

    assert response.status_code == 302
    mock_db.commit.assert_called_once()


@patch('app.get_db')
def test_nuevo_equipo_campos_vacios(mock_get_db):
    """POST /equipos/nuevo con campos vacíos muestra error, no hace commit."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/equipos/nuevo', data={
            'tipo': '', 'modelo': '', 'origen': ''
        })

    assert response.status_code == 200
    assert 'Todos los campos son obligatorios'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_editar_equipo_get(mock_get_db):
    """GET /equipos/<id>/editar con equipo existente devuelve 200."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        'id': 1, 'tipo': 'Celular', 'modelo': 'Samsung A52', 'origen': 'oficina'
    }
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/equipos/1/editar')

    assert response.status_code == 200


@patch('app.get_db')
def test_editar_equipo_exito(mock_get_db):
    """POST /equipos/<id>/editar con datos válidos hace commit y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/equipos/1/editar', data={
            'tipo': 'Celular', 'modelo': 'iPhone 14', 'origen': 'flota'
        })

    assert response.status_code == 302
    mock_db.commit.assert_called_once()


@patch('app.get_db')
def test_eliminar_equipo_cascade(mock_get_db):
    """POST /equipos/<id>/eliminar borra mantenimientos y equipo."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/equipos/1/eliminar')

    assert response.status_code == 302
    mock_db.commit.assert_called_once()
    # 2 DELETEs: mantenimientos y equipos
    assert mock_cursor.execute.call_count == 2


# ===========================================================================
# MÓDULO: MANTENIMIENTOS — GET
# ===========================================================================

@patch('app.get_db')
def test_lista_mantenimientos_get(mock_get_db):
    """GET /mantenimiento devuelve 200."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/mantenimiento')

    assert response.status_code == 200


@patch('app.get_db')
def test_nuevo_mantenimiento_camion_get(mock_get_db):
    """GET /mantenimiento/nuevo/camion devuelve 200 con lista de camiones."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/mantenimiento/nuevo/camion')

    assert response.status_code == 200


# ===========================================================================
# MÓDULO: MANTENIMIENTOS — CREAR
# ===========================================================================

@patch('app.get_db')
def test_nuevo_mantenimiento_camion_exito(mock_get_db):
    """POST /mantenimiento/nuevo/camion con datos válidos hace commit y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'patente': 'ABC123', 'modelo': 'Volvo FH'}
    ]

    from app import app
    with app.test_client() as client:
        response = client.post('/mantenimiento/nuevo/camion', data={
            'referencia_id': '1',
            'fecha_inicio': '2024-01-01',
            'fecha_fin': '',
            'descripcion': 'Cambio de aceite'
        })

    assert response.status_code == 302
    mock_db.commit.assert_called_once()


@patch('app.get_db')
def test_nuevo_mantenimiento_camion_fecha_invalida(mock_get_db):
    """POST /mantenimiento/nuevo/camion con fecha_fin < fecha_inicio muestra error."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'patente': 'ABC123', 'modelo': 'Volvo FH'}
    ]

    from app import app
    with app.test_client() as client:
        response = client.post('/mantenimiento/nuevo/camion', data={
            'referencia_id': '1',
            'fecha_inicio': '2024-06-01',
            'fecha_fin': '2024-01-01',
            'descripcion': 'Cambio de aceite'
        })

    assert response.status_code == 200
    assert 'La fecha de fin no puede ser anterior'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_nuevo_mantenimiento_equipo_exito(mock_get_db):
    """POST /mantenimiento/nuevo/equipo con datos válidos hace commit y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'tipo': 'Celular', 'modelo': 'Samsung A52', 'origen': 'oficina'}
    ]

    from app import app
    with app.test_client() as client:
        response = client.post('/mantenimiento/nuevo/equipo', data={
            'referencia_id': '1',
            'fecha_inicio': '2024-01-01',
            'fecha_fin': '',
            'descripcion': 'Revisión general'
        })

    assert response.status_code == 302
    mock_db.commit.assert_called_once()


# ===========================================================================
# MÓDULO: MANTENIMIENTOS — EDITAR / ELIMINAR
# ===========================================================================

@patch('app.get_db')
def test_editar_mantenimiento_get_camion(mock_get_db):
    """GET /mantenimiento/<id>/editar de tipo camion devuelve 200."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        'id': 1, 'tipo_referencia': 'camion', 'referencia_id': 1,
        'fecha_inicio': '2024-01-01', 'fecha_fin': None, 'descripcion': 'Test'
    }
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.get('/mantenimiento/1/editar')

    assert response.status_code == 200


@patch('app.get_db')
def test_editar_mantenimiento_fecha_invalida(mock_get_db):
    """POST /mantenimiento/<id>/editar con fecha_fin < fecha_inicio muestra error."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        'id': 1, 'tipo_referencia': 'camion', 'referencia_id': 1,
        'fecha_inicio': '2024-01-01', 'fecha_fin': None, 'descripcion': 'Test'
    }
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        response = client.post('/mantenimiento/1/editar', data={
            'referencia_id': '1',
            'fecha_inicio': '2024-06-01',
            'fecha_fin': '2024-01-01',
            'descripcion': 'Test'
        })

    assert response.status_code == 200
    assert 'La fecha de fin no puede ser anterior'.encode() in response.data
    mock_db.commit.assert_not_called()


@patch('app.get_db')
def test_eliminar_mantenimiento(mock_get_db):
    """POST /mantenimiento/<id>/eliminar borra el registro y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/mantenimiento/1/eliminar')

    assert response.status_code == 302
    mock_db.commit.assert_called_once()
    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM mantenimientos WHERE id = %s", (1,)
    )


# ===========================================================================
# MÓDULO: TRANSICIONES DE ESTADO DEL CAMIÓN
# ===========================================================================

@patch('app.get_db')
def test_crear_mantenimiento_sin_fecha_fin_pone_en_mantenimiento(mock_get_db):
    """Crear mantenimiento de camión sin fecha_fin actualiza estado a En mantenimiento."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'patente': 'ABC123', 'modelo': 'Volvo FH'}
    ]

    from app import app
    with app.test_client() as client:
        client.post('/mantenimiento/nuevo/camion', data={
            'referencia_id': '1',
            'fecha_inicio': '2024-01-01',
            'fecha_fin': '',
            'descripcion': 'Cambio de aceite'
        })

    sqls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any('En mantenimiento' in sql for sql in sqls)


@patch('app.get_db')
def test_editar_mantenimiento_con_fecha_fin_pone_disponible(mock_get_db):
    """Editar mantenimiento de camión con fecha_fin actualiza estado a Disponible."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = {
        'id': 1, 'tipo_referencia': 'camion', 'referencia_id': 1,
        'fecha_inicio': '2024-01-01', 'fecha_fin': None, 'descripcion': 'Test'
    }
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        client.post('/mantenimiento/1/editar', data={
            'referencia_id': '1',
            'fecha_inicio': '2024-01-01',
            'fecha_fin': '2024-03-01',
            'descripcion': 'Test'
        })

    sqls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any('Disponible' in sql for sql in sqls)


@patch('app.get_db')
def test_crear_camion_en_mantenimiento_crea_registro(mock_get_db):
    """Crear camión con estado En mantenimiento genera registro en mantenimientos."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None   # no hay patente duplicada
    mock_cursor.lastrowid = 1
    mock_cursor.fetchall.return_value = []

    from app import app
    with app.test_client() as client:
        client.post('/camiones/nuevo', data={
            'patente': 'NEW001', 'modelo': 'Volvo FH',
            'estado': 'En mantenimiento', 'kilometraje': '5000'
        })

    sqls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any('INSERT INTO mantenimientos' in sql for sql in sqls)
    mock_db.commit.assert_called_once()


@patch('app.get_db')
def test_editar_camion_a_en_mantenimiento_crea_registro(mock_get_db):
    """Cambiar estado de camión a En mantenimiento crea registro si no hay uno activo."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    # 1ra fetchone: no hay patente duplicada
    # 2da fetchone: estado anterior = Disponible
    # 3ra fetchone: no hay mantenimiento activo
    mock_cursor.fetchone.side_effect = [
        None,
        {'estado': 'Disponible'},
        None
    ]

    from app import app
    with app.test_client() as client:
        client.post('/camiones/1/editar', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'En mantenimiento', 'kilometraje': '10000'
        })

    sqls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any('INSERT INTO mantenimientos' in sql for sql in sqls)
    mock_db.commit.assert_called_once()


@patch('app.get_db')
def test_editar_camion_desde_en_mantenimiento_cierra_registro(mock_get_db):
    """Cambiar estado de camión desde En mantenimiento cierra el mantenimiento activo."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    # 1ra fetchone: no hay patente duplicada
    # 2da fetchone: estado anterior = En mantenimiento
    mock_cursor.fetchone.side_effect = [
        None,
        {'estado': 'En mantenimiento'}
    ]

    from app import app
    with app.test_client() as client:
        client.post('/camiones/1/editar', data={
            'patente': 'ABC123', 'modelo': 'Volvo FH',
            'estado': 'Disponible', 'kilometraje': '10000'
        })

    sqls = [str(c) for c in mock_cursor.execute.call_args_list]
    assert any('UPDATE mantenimientos SET fecha_fin' in sql for sql in sqls)
    mock_db.commit.assert_called_once()


# ===========================================================================
# MÓDULO: ALERTAS — MARCAR LEÍDA / ELIMINAR
# ===========================================================================

@patch('app.get_db')
def test_marcar_alerta_leida(mock_get_db):
    """POST /alerta/<id>/leer actualiza leida=1 y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/alerta/1/leer')

    assert response.status_code == 302
    mock_cursor.execute.assert_called_once_with(
        "UPDATE alertas SET leida = 1 WHERE id = %s", (1,)
    )
    mock_db.commit.assert_called_once()


@patch('app.get_db')
def test_eliminar_alerta_ruta(mock_get_db):
    """POST /alerta/<id>/eliminar borra la alerta y redirige."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor

    from app import app
    with app.test_client() as client:
        response = client.post('/alerta/1/eliminar')

    assert response.status_code == 302
    mock_cursor.execute.assert_called_once_with(
        "DELETE FROM alertas WHERE id = %s", (1,)
    )
    mock_db.commit.assert_called_once()


# ===========================================================================
# MÓDULO: SCHEDULER — actualizar_kilometraje_automatico
# ===========================================================================

@patch('app.get_db')
@patch('app.verificar_alerta_mantenimiento')
def test_actualizar_kilometraje_automatico(mock_verificar, mock_get_db):
    """El scheduler incrementa km de cada camión En ruta y llama a verificar alertas."""
    mock_db = MagicMock()
    mock_cursor = MagicMock()
    mock_get_db.return_value = mock_db
    mock_db.cursor.return_value = mock_cursor
    mock_cursor.fetchall.return_value = [
        {'id': 1, 'patente': 'ABC123', 'kilometraje': 5000},
        {'id': 2, 'patente': 'XYZ999', 'kilometraje': 10000},
    ]

    from app import actualizar_kilometraje_automatico
    actualizar_kilometraje_automatico()

    mock_db.commit.assert_called_once()
    # 1 SELECT + 2 UPDATEs (uno por camión)
    assert mock_cursor.execute.call_count == 3
    # verificar_alerta_mantenimiento llamado una vez por camión
    assert mock_verificar.call_count == 2
