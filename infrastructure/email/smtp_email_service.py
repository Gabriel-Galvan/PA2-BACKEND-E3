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
import socket
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from domain.entities import Expediente
from domain.repositories import ServicioCorreo

logger = logging.getLogger(__name__)


class _SMTP_SSL_IPv4(smtplib.SMTP_SSL):
    """
    Identica a smtplib.SMTP_SSL, pero fuerza la resolucion DNS a una
    direccion IPv4.

    Por que hace falta: 'smtp.gmail.com' resuelve tanto a direcciones
    IPv4 como IPv6. Algunas plataformas de hosting (Render incluida,
    en su plan gratuito/estandar) no tienen salida saliente por IPv6
    configurada; si el sistema operativo le da a Python una direccion
    IPv6 primero, la conexion falla con
    "OSError: [Errno 101] Network is unreachable" aunque el servidor
    SI tenga salida normal a internet por IPv4. Forzar IPv4 evita ese
    problema sin perder la validacion del certificado SSL (se le sigue
    pasando el nombre real del host para el handshake TLS/SNI).
    """

    def _get_socket(self, host, port, timeout):
        direcciones_ipv4 = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM)
        ip_v4 = direcciones_ipv4[0][4][0]
        if self.debuglevel > 0:
            self._print_debug("connect (forzando IPv4):", (ip_v4, port))
        nuevo_socket = socket.create_connection((ip_v4, port), timeout, self.source_address)
        return self.context.wrap_socket(nuevo_socket, server_hostname=host)


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
            with _SMTP_SSL_IPv4(self._host, self._puerto, timeout=15) as servidor:
                servidor.login(self._usuario_smtp, self._password_smtp)
                servidor.sendmail(self._usuario_smtp, [destinatario], mensaje.as_string())
            logger.info("Correo de notificacion enviado a %s (%s)", destinatario, expediente.codigo_expediente)
            return True
        except Exception:  # noqa: BLE001 - un fallo de correo nunca debe tumbar la peticion HTTP
            logger.exception("No se pudo enviar el correo de notificacion a %s", destinatario)
            return False

    def enviar_notificacion_paciente(
        self,
        destinatario: str,
        expediente: Expediente,
        pdf_adjunto: bytes | None = None,
    ) -> bool:
        asunto = f"Su resultado ya esta disponible - {self._nombre_remitente}"
        cuerpo_texto, cuerpo_html = self._construir_cuerpo_paciente(expediente)

        if self._modo_simulado:
            logger.info(
                "[MODO SIMULADO - SMTP no configurado] Correo al PACIENTE no enviado realmente.\n"
                "Para: %s\nAsunto: %s\nAdjunto PDF: %s\n%s",
                destinatario,
                asunto,
                "si" if pdf_adjunto else "no",
                cuerpo_texto,
            )
            return False

        mensaje = MIMEMultipart("mixed")
        mensaje["Subject"] = asunto
        mensaje["From"] = f"{self._nombre_remitente} <{self._usuario_smtp}>"
        mensaje["To"] = destinatario

        cuerpo = MIMEMultipart("alternative")
        cuerpo.attach(MIMEText(cuerpo_texto, "plain", "utf-8"))
        cuerpo.attach(MIMEText(cuerpo_html, "html", "utf-8"))
        mensaje.attach(cuerpo)

        if pdf_adjunto:
            adjunto = MIMEApplication(pdf_adjunto, _subtype="pdf")
            nombre_archivo = f"{expediente.codigo_expediente}-aviso.pdf"
            adjunto.add_header("Content-Disposition", "attachment", filename=nombre_archivo)
            mensaje.attach(adjunto)

        try:
            with _SMTP_SSL_IPv4(self._host, self._puerto, timeout=15) as servidor:
                servidor.login(self._usuario_smtp, self._password_smtp)
                servidor.sendmail(self._usuario_smtp, [destinatario], mensaje.as_string())
            logger.info("Correo de aviso al paciente enviado a %s (%s)", destinatario, expediente.codigo_expediente)
            return True
        except Exception:  # noqa: BLE001 - un fallo de correo nunca debe tumbar la peticion HTTP
            logger.exception("No se pudo enviar el correo de aviso al paciente %s", destinatario)
            return False

    @staticmethod
    def _construir_cuerpo_paciente(expediente: Expediente) -> tuple[str, str]:
        texto = (
            f"Estimado(a) {expediente.nombre_paciente},\n\n"
            f"Le informamos que el analisis de laboratorio correspondiente a su muestra "
            f"(codigo de referencia {expediente.codigo_expediente}) ya se encuentra disponible.\n\n"
            "Por favor comuniquese con su medico tratante o acerquese a nuestras "
            "instalaciones para recibir la explicacion detallada de sus resultados.\n\n"
            "Este mensaje es una notificacion automatica y no reemplaza la consulta medica: "
            "los resultados clinicos completos solo se entregan de forma presencial o a "
            "traves de su profesional de salud. Encontrara mas detalles en el PDF adjunto.\n\n"
            "-- Sistema de Diagnostico Cervical"
        )
        html = f"""
        <div style="font-family: Arial, sans-serif; color: #3d2e1e; max-width: 480px;">
          <h2 style="color:#a07850;">Su resultado ya esta disponible</h2>
          <p>Estimado(a) <strong>{expediente.nombre_paciente}</strong>,</p>
          <p>Le informamos que el analisis de laboratorio correspondiente a su muestra
             (codigo de referencia <strong>{expediente.codigo_expediente}</strong>) ya se
             encuentra disponible.</p>
          <p>Por favor comuniquese con su medico tratante o acerquese a nuestras
             instalaciones para recibir la explicacion detallada de sus resultados.</p>
          <p style="font-size:12px; color:#8a7560;">Este mensaje es una notificacion
             automatica y no reemplaza la consulta medica: los resultados clinicos
             completos solo se entregan de forma presencial o a traves de su
             profesional de salud. Encontrara mas detalles en el PDF adjunto.</p>
          <hr style="border:none; border-top:1px solid #e8dece; margin:16px 0;">
          <p style="font-size:11px; color:#a09080;">Sistema de Diagnostico Cervical</p>
        </div>
        """
        return texto, html

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
