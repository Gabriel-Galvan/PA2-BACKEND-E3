"""
CAPA: INFRASTRUCTURE (Infraestructura) - Notificaciones por correo
=====================================================================
Implementacion CONCRETA del puerto `ServicioCorreo`. Envia (via Gmail
SMTP, aunque funciona con cualquier proveedor SMTP estandar) un correo
al medico cuando el analisis de una imagen de su expediente concluyo
con exito.

MODO SIMULADO
-------------
Si las variables de entorno SMTP_USER / SMTP_PASSWORD no estan
configuradas (por ejemplo, mientras el proyecto todavia no tiene una
cuenta de Gmail dedicada con "contrasena de aplicacion"), este
servicio NO intenta conectarse a ningun servidor: simplemente registra
el contenido del correo en los logs del backend y devuelve False. Asi
el resto del sistema (crear expedientes, etc.) funciona igual sin
romperse por falta de credenciales, y basta con definir esas dos
variables de entorno en Render para activar el envio real, sin tocar
nada de codigo.

Configuracion esperada (variables de entorno):
    SMTP_HOST      (por defecto: smtp.gmail.com)
    SMTP_PORT      (por defecto: 465, SSL)
    SMTP_USER      (la cuenta de Gmail que envia, ej: clinica@gmail.com)
    SMTP_PASSWORD  (contrasena de aplicacion de Gmail, NO la contrasena normal)
    SMTP_FROM_NAME (nombre visible del remitente, por defecto: 'Sistema de Diagnostico Cervical')
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from domain.entities import Expediente
from domain.repositories import ServicioCorreo

logger = logging.getLogger(__name__)


class SMTPEmailService(ServicioCorreo):
    def __init__(
        self,
        host: str,
        puerto: int,
        usuario_smtp: str | None,
        password_smtp: str | None,
        nombre_remitente: str = "Sistema de Diagnostico Cervical",
    ):
        self._host = host
        self._puerto = puerto
        self._usuario_smtp = usuario_smtp
        self._password_smtp = password_smtp
        self._nombre_remitente = nombre_remitente

    @property
    def _modo_simulado(self) -> bool:
        return not (self._usuario_smtp and self._password_smtp)

    def enviar_notificacion_analisis(
        self,
        destinatario: str,
        nombre_medico: str,
        expediente: Expediente,
    ) -> bool:
        asunto = f"Analisis completado - {expediente.codigo_expediente} ({expediente.nombre_paciente})"
        cuerpo_texto, cuerpo_html = self._construir_cuerpo(nombre_medico, expediente)

        if self._modo_simulado:
            logger.info(
                "[MODO SIMULADO - SMTP no configurado] Correo NO enviado realmente.\n"
                "Para: %s\nAsunto: %s\n%s",
                destinatario,
                asunto,
                cuerpo_texto,
            )
            return False

        mensaje = MIMEMultipart("alternative")
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{self._nombre_remitente} <{self._usuario_smtp}>"
        mensaje["To"] = destinatario
        mensaje.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
        mensaje.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        try:
            with smtplib.SMTP_SSL(self._host, self._puerto, timeout=15) as servidor:
                servidor.login(self._usuario_smtp, self._password_smtp)
                servidor.sendmail(self._usuario_smtp, [destinatario], mensaje.as_string())
            logger.info("Correo de notificacion enviado a %s (%s)", destinatario, expediente.codigo_expediente)
            return True
        except Exception:  # noqa: BLE001 - un fallo de correo nunca debe tumbar la peticion HTTP
            logger.exception("No se pudo enviar el correo de notificacion a %s", destinatario)
            return False

    @staticmethod
    def _construir_cuerpo(nombre_medico: str, expediente: Expediente) -> tuple[str, str]:
        etiqueta_severidad = {
            "normal": "Normal",
            "revisar": "Requiere seguimiento",
            "positivo": "Hallazgo relevante",
        }.get(expediente.severidad, "Requiere seguimiento")

        texto = (
            f"Hola Dr(a). {nombre_medico},\n\n"
            f"El analisis de IA para el expediente {expediente.codigo_expediente} "
            f"del paciente {expediente.nombre_paciente} ha finalizado con exito.\n\n"
            f"Diagnostico sugerido por el modelo: {expediente.diagnostico_ia}\n"
            f"Confianza: {expediente.confianza_ia:.2f}%\n"
            f"Clasificacion de apoyo: {etiqueta_severidad}\n\n"
            "Recuerda que este resultado es una herramienta de apoyo diagnostico "
            "y no reemplaza el criterio clinico profesional.\n\n"
            "Puedes revisar el expediente completo iniciando sesion en el sistema.\n\n"
            "-- Sistema de Diagnostico Cervical"
        )

        html = f"""
        <div style="font-family: Arial, sans-serif; color: #3d2e1e; max-width: 480px;">
          <h2 style="color:#a07850;">Analisis completado con exito</h2>
          <p>Hola Dr(a). <strong>{nombre_medico}</strong>,</p>
          <p>El analisis de IA para el expediente <strong>{expediente.codigo_expediente}</strong>
             del paciente <strong>{expediente.nombre_paciente}</strong> ha finalizado con exito.</p>
          <table style="border-collapse:collapse; margin:12px 0;">
            <tr><td style="padding:4px 10px 4px 0; color:#8a7560;">Diagnostico sugerido:</td>
                <td style="padding:4px 0;"><strong>{expediente.diagnostico_ia}</strong></td></tr>
            <tr><td style="padding:4px 10px 4px 0; color:#8a7560;">Confianza:</td>
                <td style="padding:4px 0;">{expediente.confianza_ia:.2f}%</td></tr>
            <tr><td style="padding:4px 10px 4px 0; color:#8a7560;">Clasificacion de apoyo:</td>
                <td style="padding:4px 0;">{etiqueta_severidad}</td></tr>
          </table>
          <p style="font-size:12px; color:#8a7560;">Este resultado es una herramienta de apoyo
             diagnostico y no reemplaza el criterio clinico profesional.</p>
          <p style="font-size:12px; color:#8a7560;">Inicia sesion en el sistema para revisar el
             expediente completo.</p>
          <hr style="border:none; border-top:1px solid #e8dece; margin:16px 0;">
          <p style="font-size:11px; color:#a09080;">Sistema de Diagnostico Cervical</p>
        </div>
        """
        return texto, html
