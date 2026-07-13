"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioExpedientes` (definido
en domain/repositories.py) usando SQLite. Espejo del repositorio de
usuarios: la tabla `expedientes` se crea en database/schema.sql.
"""

import json
import sqlite3
from datetime import datetime

from domain.entities import Expediente
from domain.repositories import RepositorioExpedientes


class RepositorioExpedientesSQLite(RepositorioExpedientes):
    def __init__(self, ruta_db: str):
        self._ruta_db = ruta_db

    def _conectar(self) -> sqlite3.Connection:
        conexion = sqlite3.connect(self._ruta_db)
        conexion.row_factory = sqlite3.Row
        return conexion

    _COLUMNAS_SIN_IMAGEN = (
        "id, medico_id, nombre_paciente, numero_documento, fecha_nacimiento, sexo, "
        "historial_ginecologico, sintomas, observaciones, diagnostico_ia, "
        "confianza_ia, probabilidades_ia, nombre_archivo_imagen, imagen_mime, "
        "celulas_detectadas, creado_en, actualizado_en"
    )

    def crear(self, expediente: Expediente) -> Expediente:
        ahora = datetime.utcnow().isoformat()
        with self._conectar() as conexion:
            cursor = conexion.execute(
                """
                INSERT INTO expedientes (
                    medico_id, nombre_paciente, numero_documento, fecha_nacimiento, sexo,
                    historial_ginecologico, sintomas, observaciones, diagnostico_ia,
                    confianza_ia, probabilidades_ia, nombre_archivo_imagen, imagen_mime,
                    imagen_datos, celulas_detectadas, creado_en, actualizado_en
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    expediente.medico_id,
                    expediente.nombre_paciente,
                    expediente.numero_documento,
                    expediente.fecha_nacimiento,
                    expediente.sexo,
                    expediente.historial_ginecologico,
                    expediente.sintomas,
                    expediente.observaciones,
                    expediente.diagnostico_ia,
                    expediente.confianza_ia,
                    json.dumps(expediente.probabilidades_ia),
                    expediente.nombre_archivo_imagen,
                    expediente.imagen_mime,
                    expediente.imagen_datos,
                    json.dumps(expediente.celulas_detectadas) if expediente.celulas_detectadas else None,
                    ahora,
                    ahora,
                ),
            )
            conexion.commit()
            nuevo_id = cursor.lastrowid
        return self.obtener_por_id(nuevo_id)

    def listar_por_medico(self, medico_id: int) -> list[Expediente]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                f"SELECT {self._COLUMNAS_SIN_IMAGEN} FROM expedientes "
                "WHERE medico_id = ? ORDER BY creado_en DESC",
                (medico_id,),
            ).fetchall()
        return [self._fila_a_entidad(f, incluir_imagen=False) for f in filas]

    def listar_todos(self) -> list[Expediente]:
        with self._conectar() as conexion:
            filas = conexion.execute(
                f"SELECT {self._COLUMNAS_SIN_IMAGEN} FROM expedientes ORDER BY creado_en DESC"
            ).fetchall()
        return [self._fila_a_entidad(f, incluir_imagen=False) for f in filas]

    def obtener_por_id(self, expediente_id: int) -> Expediente | None:
        with self._conectar() as conexion:
            fila = conexion.execute(
                "SELECT * FROM expedientes WHERE id = ?", (expediente_id,)
            ).fetchone()
        return self._fila_a_entidad(fila, incluir_imagen=True) if fila else None

    def actualizar_datos_clinicos(
        self,
        expediente_id: int,
        nombre_paciente: str,
        numero_documento: str,
        fecha_nacimiento: str | None,
        sexo: str | None,
        historial_ginecologico: str,
        sintomas: str,
        observaciones: str,
    ) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute(
                """
                UPDATE expedientes SET
                    nombre_paciente = ?, numero_documento = ?, fecha_nacimiento = ?, sexo = ?,
                    historial_ginecologico = ?, sintomas = ?, observaciones = ?,
                    actualizado_en = ?
                WHERE id = ?
                """,
                (
                    nombre_paciente,
                    numero_documento,
                    fecha_nacimiento,
                    sexo,
                    historial_ginecologico,
                    sintomas,
                    observaciones,
                    datetime.utcnow().isoformat(),
                    expediente_id,
                ),
            )
            conexion.commit()
        return cursor.rowcount > 0

    def eliminar(self, expediente_id: int) -> bool:
        with self._conectar() as conexion:
            cursor = conexion.execute("DELETE FROM expedientes WHERE id = ?", (expediente_id,))
            conexion.commit()
        return cursor.rowcount > 0

    @staticmethod
    def _fila_a_entidad(fila: sqlite3.Row, incluir_imagen: bool) -> Expediente:
        columnas = fila.keys()
        return Expediente(
            id=fila["id"],
            medico_id=fila["medico_id"],
            nombre_paciente=fila["nombre_paciente"],
            numero_documento=fila["numero_documento"],
            fecha_nacimiento=fila["fecha_nacimiento"],
            sexo=fila["sexo"] if "sexo" in columnas else None,
            historial_ginecologico=fila["historial_ginecologico"] or "",
            sintomas=fila["sintomas"] or "",
            observaciones=fila["observaciones"] or "",
            diagnostico_ia=fila["diagnostico_ia"],
            confianza_ia=fila["confianza_ia"],
            probabilidades_ia=json.loads(fila["probabilidades_ia"]) if fila["probabilidades_ia"] else {},
            nombre_archivo_imagen=fila["nombre_archivo_imagen"] or "",
            imagen_mime=fila["imagen_mime"] or "image/jpeg",
            imagen_datos=fila["imagen_datos"] if incluir_imagen and "imagen_datos" in columnas else None,
            creado_en=datetime.fromisoformat(fila["creado_en"]) if fila["creado_en"] else None,
            actualizado_en=datetime.fromisoformat(fila["actualizado_en"]) if fila["actualizado_en"] else None,
            celulas_detectadas=(
                json.loads(fila["celulas_detectadas"])
                if "celulas_detectadas" in columnas and fila["celulas_detectadas"]
                else None
            ),
        )
