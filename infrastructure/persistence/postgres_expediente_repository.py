"""
CAPA: INFRASTRUCTURE (Infraestructura) - Persistencia
========================================================
Implementacion CONCRETA del puerto `RepositorioExpedientes` usando
PostgreSQL (Render Postgres). Espejo de sqlite_expediente_repository.py,
mismo contrato.
"""

import json

import psycopg2
import psycopg2.extras

from domain.entities import Expediente
from domain.repositories import RepositorioExpedientes

_COLUMNAS_SIN_IMAGEN = (
    "id, medico_id, nombre_paciente, numero_documento, fecha_nacimiento, sexo, "
    "historial_ginecologico, sintomas, observaciones, diagnostico_ia, "
    "confianza_ia, probabilidades_ia, nombre_archivo_imagen, imagen_mime, "
    "creado_en, actualizado_en"
)


class RepositorioExpedientesPostgres(RepositorioExpedientes):
    def __init__(self, database_url: str):
        self._database_url = database_url.replace("postgres://", "postgresql://", 1)

    def _conectar(self):
        return psycopg2.connect(self._database_url)

    def crear(self, expediente: Expediente) -> Expediente:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO expedientes (
                        medico_id, nombre_paciente, numero_documento, fecha_nacimiento, sexo,
                        historial_ginecologico, sintomas, observaciones, diagnostico_ia,
                        confianza_ia, probabilidades_ia, nombre_archivo_imagen, imagen_mime,
                        imagen_datos, creado_en, actualizado_en
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    RETURNING id
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
                        psycopg2.Binary(expediente.imagen_datos) if expediente.imagen_datos else None,
                    ),
                )
                nuevo_id = cursor.fetchone()[0]
            conexion.commit()
        return self.obtener_por_id(nuevo_id)

    def listar_por_medico(self, medico_id: int) -> list[Expediente]:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"SELECT {_COLUMNAS_SIN_IMAGEN} FROM expedientes "
                    "WHERE medico_id = %s ORDER BY creado_en DESC",
                    (medico_id,),
                )
                filas = cursor.fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    def listar_todos(self) -> list[Expediente]:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"SELECT {_COLUMNAS_SIN_IMAGEN} FROM expedientes ORDER BY creado_en DESC"
                )
                filas = cursor.fetchall()
        return [self._fila_a_entidad(f) for f in filas]

    def obtener_por_id(self, expediente_id: int) -> Expediente | None:
        with self._conectar() as conexion:
            with conexion.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM expedientes WHERE id = %s", (expediente_id,))
                fila = cursor.fetchone()
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
            with conexion.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE expedientes SET
                        nombre_paciente = %s, numero_documento = %s, fecha_nacimiento = %s, sexo = %s,
                        historial_ginecologico = %s, sintomas = %s, observaciones = %s,
                        actualizado_en = NOW()
                    WHERE id = %s
                    """,
                    (
                        nombre_paciente,
                        numero_documento,
                        fecha_nacimiento,
                        sexo,
                        historial_ginecologico,
                        sintomas,
                        observaciones,
                        expediente_id,
                    ),
                )
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    def eliminar(self, expediente_id: int) -> bool:
        with self._conectar() as conexion:
            with conexion.cursor() as cursor:
                cursor.execute("DELETE FROM expedientes WHERE id = %s", (expediente_id,))
                filas_afectadas = cursor.rowcount
            conexion.commit()
        return filas_afectadas > 0

    @staticmethod
    def _fila_a_entidad(fila, incluir_imagen: bool = False) -> Expediente:
        imagen_datos = None
        if incluir_imagen and fila.get("imagen_datos") is not None:
            imagen_datos = bytes(fila["imagen_datos"])
        probabilidades = fila.get("probabilidades_ia")
        if isinstance(probabilidades, str):
            probabilidades = json.loads(probabilidades)
        return Expediente(
            id=fila["id"],
            medico_id=fila["medico_id"],
            nombre_paciente=fila["nombre_paciente"],
            numero_documento=fila["numero_documento"],
            fecha_nacimiento=str(fila["fecha_nacimiento"]) if fila["fecha_nacimiento"] else None,
            sexo=fila.get("sexo"),
            historial_ginecologico=fila["historial_ginecologico"] or "",
            sintomas=fila["sintomas"] or "",
            observaciones=fila["observaciones"] or "",
            diagnostico_ia=fila["diagnostico_ia"],
            confianza_ia=float(fila["confianza_ia"]),
            probabilidades_ia=probabilidades or {},
            nombre_archivo_imagen=fila["nombre_archivo_imagen"] or "",
            imagen_mime=fila["imagen_mime"] or "image/jpeg",
            imagen_datos=imagen_datos,
            creado_en=fila["creado_en"],
            actualizado_en=fila["actualizado_en"],
        )
