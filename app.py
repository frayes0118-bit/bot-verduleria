"""
Bot de WhatsApp para la verdulería, usando Twilio + Google Gemini (gratis).

Cómo funciona:
1. Un cliente te escribe por WhatsApp.
2. Twilio recibe ese mensaje y lo manda a este servidor (a la ruta /webhook).
3. Este servidor le pasa el mensaje a Gemini, junto con la info del negocio
   (productos, precios, zona de delivery) que está en negocio.json.
4. Gemini arma una respuesta natural, y este servidor se la devuelve a Twilio,
   que la manda de vuelta al cliente por WhatsApp.

Antes de correr esto necesitás:
- Una cuenta en Twilio (gratis para probar) con el WhatsApp Sandbox activado.
- Tu GEMINI_API_KEY, gratis y sin tarjeta, desde aistudio.google.com/apikey
- Instalar las dependencias: pip install -r requirements.txt

Ver README.md para los pasos completos, incluyendo cómo publicar esto
en Railway para que funcione las 24 horas sin depender de tu notebook.
"""

import json
import os

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

# La API key se lee de una variable de entorno, nunca la escribas acá directamente.
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
modelo = genai.GenerativeModel("gemini-1.5-flash")

RUTA_NEGOCIO = os.path.join(os.path.dirname(__file__), "negocio.json")


def cargar_info_negocio():
    """Lee negocio.json cada vez, así siempre usa los precios más recientes."""
    with open(RUTA_NEGOCIO, "r", encoding="utf-8") as f:
        return json.load(f)


def armar_prompt_sistema(info):
    lineas_productos = "\n".join(
        f"- {p['nombre']}: ${p['precio']} por {p['unidad']}"
        for p in info["productos"]
    )
    return f"""Sos el asistente de WhatsApp de "{info['nombre_negocio']}", una verdulería.

Tu trabajo es atender consultas de clientes por WhatsApp: dar precios, tomar
pedidos y coordinar el delivery. Hablá en tono cercano y directo, como
el dueño del local, con frases cortas. No inventes productos ni precios
que no estén en esta lista.

INFORMACIÓN DEL NEGOCIO:
- Zona de delivery: {info['zona_delivery']}
- Horario de atención: {info['horario_atencion']}
- Horario para pedidos: {info['horario_pedidos']}

PRODUCTOS Y PRECIOS DE HOY:
{lineas_productos}

Si un cliente pide algo que no está en la lista, avisale amablemente que
hoy no tenés ese producto y ofrecele alternativas de la lista.
Si pide para hacer un pedido, confirmale los productos, el total, y pedile
la dirección de entrega si no la dio. Sé breve: los mensajes de WhatsApp
se leen en el celular, no hagas párrafos largos."""


@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje_cliente = request.form.get("Body", "")

    info = cargar_info_negocio()
    prompt_sistema = armar_prompt_sistema(info)

    respuesta_gemini = modelo.generate_content(
        [prompt_sistema, f"Mensaje del cliente: {mensaje_cliente}"]
    )
    texto_respuesta = respuesta_gemini.text

    respuesta_twilio = MessagingResponse()
    respuesta_twilio.message(texto_respuesta)
    return str(respuesta_twilio)


@app.route("/", methods=["GET"])
def salud():
    # Ruta simple para confirmar que el servidor está corriendo.
    return "Bot de la verdulería andando ✅"


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
