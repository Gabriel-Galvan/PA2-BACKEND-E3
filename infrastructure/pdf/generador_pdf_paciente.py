"""
CAPA: INFRASTRUCTURE (Infraestructura) - Generacion de PDF
=============================================================
Genera el PDF generico que se adjunta al correo que recibe el
PACIENTE (no el medico) avisandole que su resultado ya esta listo.

DECISION DE DISENO IMPORTANTE: a proposito este PDF NO incluye el
diagnostico de IA ni el nivel de confianza. Enviar un resultado
citologico (con terminologia como "hallazgo relevante" o nombres de
tipos celulares) directamente al correo de un paciente, sin la
mediacion de un profesional de salud que lo explique, no es una
practica clinica responsable y puede generar angustia innecesaria o
malas interpretaciones. El PDF es entonces un AVISO generico ("tu
resultado ya esta disponible, contacta a tu clinica/medico"), y el
informe clinico completo (con el diagnostico) sigue viviendo dentro
del sistema, accesible solo por el personal de salud autenticado.
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from domain.entities import Expediente
from domain.repositories import GeneradorPdfPaciente

_COLOR_ACENTO = colors.HexColor("#a07850")
_COLOR_TEXTO = colors.HexColor("#3d2e1e")
_COLOR_TEXTO_SUAVE = colors.HexColor("#8a7560")


class GeneradorPdfPacienteReportlab(GeneradorPdfPaciente):
    """Implementacion concreta (reportlab) del puerto `GeneradorPdfPaciente`."""

    def __init__(self, nombre_clinica: str = "Sistema de Diagnostico Cervical"):
        self._nombre_clinica = nombre_clinica

    def generar(self, expediente: Expediente) -> bytes:
        return _generar_pdf_aviso_paciente(expediente, self._nombre_clinica)


def _generar_pdf_aviso_paciente(expediente: Expediente, nombre_clinica: str) -> bytes:
    """Genera (en memoria, sin tocar disco) un PDF de aviso generico para el paciente."""
    buffer = io.BytesIO()
    doc = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4
    margen_x = 22 * mm
    y = alto - 30 * mm

    # ---- Encabezado ----
    doc.setFillColor(_COLOR_ACENTO)
    doc.circle(margen_x + 6 * mm, y, 6 * mm, fill=1, stroke=0)
    doc.setFillColor(colors.white)
    doc.setFont("Helvetica-Bold", 12)
    doc.drawCentredString(margen_x + 6 * mm, y - 4, "C")

    doc.setFillColor(_COLOR_TEXTO)
    doc.setFont("Helvetica-Bold", 13)
    doc.drawString(margen_x + 16 * mm, y + 2 * mm, nombre_clinica)
    doc.setFont("Helvetica", 8.5)
    doc.setFillColor(_COLOR_TEXTO_SUAVE)
    doc.drawString(margen_x + 16 * mm, y - 3.5 * mm, "Aviso de resultado disponible")

    y -= 18 * mm
    doc.setStrokeColor(colors.HexColor("#c9b99a"))
    doc.setLineWidth(0.6)
    doc.line(margen_x, y, ancho - margen_x, y)
    y -= 12 * mm

    # ---- Cuerpo ----
    doc.setFillColor(_COLOR_TEXTO)
    doc.setFont("Helvetica-Bold", 15)
    doc.drawString(margen_x, y, "Su resultado ya esta disponible")
    y -= 12 * mm

    doc.setFont("Helvetica", 10.5)
    lineas = [
        f"Estimado(a) {expediente.nombre_paciente},",
        "",
        "Le informamos que el analisis de laboratorio correspondiente a su muestra",
        f"(codigo de referencia {expediente.codigo_expediente}) ya se encuentra disponible.",
        "",
        "Por favor comuniquese con su medico tratante o acerquese a nuestras",
        "instalaciones para recibir la explicacion detallada de sus resultados y",
        "conversar sobre los siguientes pasos, si los hubiera.",
        "",
        "Este mensaje es una notificacion automatica y no reemplaza la consulta",
        "medica: los resultados clinicos completos solo se entregan de forma",
        "presencial o a traves de su profesional de salud.",
    ]
    for linea in lineas:
        doc.drawString(margen_x, y, linea)
        y -= 6 * mm

    y -= 6 * mm
    doc.setStrokeColor(colors.HexColor("#e8dece"))
    doc.line(margen_x, y, ancho - margen_x, y)
    y -= 8 * mm

    doc.setFont("Helvetica", 8)
    doc.setFillColor(_COLOR_TEXTO_SUAVE)
    doc.drawString(margen_x, y, "Documento generado automaticamente. No constituye una historia clinica ni un diagnostico.")
    y -= 5 * mm
    doc.drawString(margen_x, y, nombre_clinica)

    doc.showPage()
    doc.save()
    return buffer.getvalue()
