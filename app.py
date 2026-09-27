"""
Bot de WhatsApp para la verdulería — versión con flujo de pedido completo.

Qué hace:
1. El cliente escribe pidiendo verduras (ej: "quiero 2 kg de tomate y 1 lechuga").
2. El bot entiende el pedido, revisa el stock real (almacen.json / stock.json) y
   arma un resumen con precios reales (no inventados).
3. Le pide confirmación al cliente.
4. Si confirma, pide nombre y apellido, dirección, y método de pago.
5. Al terminar: descuenta el stock vendido, guarda el pedido completo en
   pedidos.json (tu "base de datos" de clientes y pedidos), y confirma
   el pedido con un mensaje cálido, no robótico.

Las respuestas de confirmación de pedido, precios y stock las arma
directamente Python con los datos reales — así nunca hay un precio o
stock "inventado". Gemini se usa solo para dos cosas: entender qué pidió
el cliente en lenguaje natural, y responder preguntas sueltas (horarios,
zona de delivery, etc.) de forma natural.

Variables de entorno necesarias:
- GEMINI_API_KEY: tu clave gratuita de Google AI Studio
- DATA_DIR (opcional): carpeta donde se guardan negocio.json, stock.json,
  sesiones.json y pedidos.json. Si usás un Volume de Railway, apuntá esto
  a esa carpeta (ej: /data) para que el stock y los pedidos no se borren
  cada vez que se vuelve a desplegar el bot.
"""

import json
import os
import re
from datetime import datetime

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import google.generativeai as genai

app = Flask(__name__)

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
modelo = genai.GenerativeModel("gemini-3.8-flash")

DATA_DIR = os.environ.get("DATA_DIR", os.path.dirname(__file__))
RUTA_NEGOCIO = os.path.join(DATA_DIR, "negocio.json")
RUTA_STOCK = os.path.join(DATA_DIR, "stock.json")
RUTA_SESIONES = os.path.join(DATA_DIR, "sesiones.json")
RUTA_PEDIDOS = os.path.join(DATA_DIR, "pedidos.json")


# ---------- Utilidades para leer/escribir los archivos ----------

def cargar_json(ruta, default):
    if not os.path.exists(ruta):
        return default
    with open(ruta, "r", encoding="utf-8") as f:
        return json.load(f)


def guardar_json(ruta, data):
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def cargar_negocio():
    return cargar_json(RUTA_NEGOCIO, {})


def cargar_stock():
    return cargar_json(RUTA_STOCK, {})


def guardar_stock(stock):
    guardar_json(RUTA_STOCK, stock)


def cargar_sesiones():
    return cargar_json(RUTA_SESIONES, {})


def guardar_sesiones(sesiones):
    guardar_json(RUTA_SESIONES, sesiones)


def sesion_nueva():
    return {
        "estado": "inicio",
        "pedido": {"items": [], "total": 0},
        "nombre": None,
        "direccion": None,
        "metodo_pago": None,
    }


def guardar_pedido(numero_cliente, sesion):
    pedidos = cargar_json(RUTA_PEDIDOS, [])
    pedidos.append({
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cliente_whatsapp": numero_cliente,
        "nombre": sesion["nombre"],
        "direccion": sesion["direccion"],
        "metodo_pago": sesion["metodo_pago"],
        "items": sesion["pedido"]["items"],
        "total": sesion["pedido"]["total"],
    })
    guardar_json(RUTA_PEDIDOS, pedidos)


# ---------- Entender el pedido con Gemini (solo extracción, sin precios) ----------

def interpretar_mensaje(mensaje_cliente, stock):
    """
    Le pide a Gemini que interprete el mensaje del cliente y devuelva SOLO
    un JSON con la intención y los productos pedidos (nombre tal cual
    aparecen en el catálogo, y cantidad). Los precios y el stock los
    calcula Python después, con datos reales.
    """
    catalogo = ", ".join(stock.keys())
    prompt = f"""Sos un sistema que interpreta pedidos de una verdulería.

Catálogo disponible (usá EXACTAMENTE estos nombres si el cliente los pide,
aunque los escriba distinto o con errores de tipeo): {catalogo}

Mensaje del cliente: "{mensaje_cliente}"

Respondé SOLO con un JSON (sin texto adicional, sin backticks) con esta forma:
{{
  "intencion": "pedido" | "confirmacion" | "cancelacion" | "otro",
  "items": [{{"producto": "nombre exacto del catálogo", "cantidad": numero}}]
}}

Reglas:
- "intencion": "pedido" si el cliente está pidiendo productos.
- "intencion": "confirmacion" si el cliente está diciendo que sí, dale, confirmo, etc.
- "intencion": "cancelacion" si el cliente quiere cancelar o dice que no.
- "intencion": "otro" para preguntas generales (horarios, zona, etc.) o cualquier
  otra cosa que no sea un pedido ni una confirmación.
- Si no menciona cantidad para un producto, asumí cantidad 1.
- Si el producto no está en el catálogo, no lo incluyas en "items"."""

    respuesta = modelo.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    try:
        return json.loads(respuesta.text)
    except (json.JSONDecodeError, AttributeError):
        return {"intencion": "otro", "items": []}


def responder_pregunta_libre(mensaje_cliente, negocio):
    prompt = f"""Sos el asistente de WhatsApp de "{negocio.get('nombre_negocio', 'la verdulería')}".
Hablá en tono cercano, cálido y directo, como el dueño del local — nunca digas
que sos un bot ni una inteligencia artificial. Frases cortas, como se escribe
en WhatsApp.

Datos del negocio:
- Zona de delivery: {negocio.get('zona_delivery', '')}
- Horario de atención: {negocio.get('horario_atencion', '')}
- Horario para pedidos: {negocio.get('horario_pedidos', '')}
- Métodos de pago: {', '.join(negocio.get('metodos_pago', []))}

Mensaje del cliente: "{mensaje_cliente}"

Respondé de forma breve y natural."""
    respuesta = modelo.generate_content(prompt)
    return respuesta.text


# ---------- Armar el pedido con datos reales de stock ----------

def armar_pedido(items_pedidos, stock):
    """
    Devuelve (items_confirmados, faltantes, total) usando SOLO datos reales
    del archivo de stock. No usa nada que haya dicho Gemini sobre precios.
    """
    items_confirmados = []
    faltantes = []
    total = 0

    for item in items_pedidos:
        nombre = item.get("producto")
        cantidad = item.get("cantidad", 1)
        producto = stock.get(nombre)

        if not producto:
            continue

        if producto["stock_disponible"] < cantidad:
            faltantes.append({
                "producto": nombre,
                "pedido": cantidad,
                "disponible": producto["stock_disponible"],
                "unidad": producto["unidad"],
            })
            continue

        subtotal = producto["precio"] * cantidad
        items_confirmados.append({
            "producto": nombre,
            "cantidad": cantidad,
            "unidad": producto["unidad"],
            "precio_unitario": producto["precio"],
            "subtotal": subtotal,
        })
        total += subtotal

    return items_confirmados, faltantes, total


def texto_resumen_pedido(items, total):
    lineas = [
        f"• {it['cantidad']} {it['unidad']} de {it['producto']} — ${it['subtotal']:.0f}"
        for it in items
    ]
    return "\n".join(lineas) + f"\n\n*Total: ${total:.0f}*"


# ---------- El webhook principal ----------

@app.route("/webhook", methods=["POST"])
def webhook():
    mensaje_cliente = request.form.get("Body", "").strip()
    numero_cliente = request.form.get("From", "")

    negocio = cargar_negocio()
    stock = cargar_stock()
    sesiones = cargar_sesiones()
    sesion = sesiones.get(numero_cliente, sesion_nueva())

    respuesta_twilio = MessagingResponse()
    estado = sesion["estado"]

    # --- Paso 1: cliente pidiendo productos, o consulta libre ---
    if estado == "inicio":
        analisis = interpretar_mensaje(mensaje_cliente, stock)

        if analisis["intencion"] == "pedido" and analisis["items"]:
            items_confirmados, faltantes, total = armar_pedido(analisis["items"], stock)

            if not items_confirmados:
                texto = "Uy, disculpá, no me quedan esos productos en este momento 😕 ¿Querés que te diga qué tengo disponible hoy?"
            else:
                sesion["pedido"] = {"items": items_confirmados, "total": total}
                sesion["estado"] = "confirmando_pedido"
                texto = "Este sería tu pedido:\n\n" + texto_resumen_pedido(items_confirmados, total)
                if faltantes:
                    lineas_falt = [
                        f"⚠️ De {f['producto']} solo tengo {f['disponible']} {f['unidad']} (pediste {f['pedido']})"
                        for f in faltantes
                    ]
                    texto += "\n\n" + "\n".join(lineas_falt)
                texto += "\n\n¿Confirmás el pedido así? 🙂"

        else:
            texto = responder_pregunta_libre(mensaje_cliente, negocio)

        respuesta_twilio.message(texto)

    # --- Paso 2: esperando que confirme o cancele el pedido ---
    elif estado == "confirmando_pedido":
        analisis = interpretar_mensaje(mensaje_cliente, stock)

        if analisis["intencion"] == "confirmacion":
            sesion["estado"] = "esperando_nombre"
            texto = "Genial 🥬 ¿Me pasás tu nombre y apellido para el pedido?"
        elif analisis["intencion"] == "cancelacion":
            sesion = sesion_nueva()
            texto = "Sin problema, cancelé el pedido. ¿Querés pedir otra cosa?"
        else:
            texto = "¿Confirmás el pedido de arriba? Respondeme sí o no 🙂"

        respuesta_twilio.message(texto)

    # --- Paso 3: esperando nombre y apellido ---
    elif estado == "esperando_nombre":
        sesion["nombre"] = mensaje_cliente
        sesion["estado"] = "esperando_direccion"
        respuesta_twilio.message(f"Gracias {mensaje_cliente.split()[0]}! ¿A qué dirección te lo llevo?")

    # --- Paso 4: esperando dirección ---
    elif estado == "esperando_direccion":
        sesion["direccion"] = mensaje_cliente
        sesion["estado"] = "esperando_pago"
        metodos = negocio.get("metodos_pago", ["Efectivo"])
        texto_metodos = " o ".join(metodos)
        respuesta_twilio.message(f"Perfecto. ¿Cómo vas a pagar: {texto_metodos}?")

    # --- Paso 5: esperando método de pago -> cerrar pedido ---
    elif estado == "esperando_pago":
        sesion["metodo_pago"] = mensaje_cliente

        # Descontar stock real
        for it in sesion["pedido"]["items"]:
            if it["producto"] in stock:
                stock[it["producto"]]["stock_disponible"] -= it["cantidad"]
        guardar_stock(stock)

        # Guardar el pedido en la "base de datos" de pedidos
        guardar_pedido(numero_cliente, sesion)

        resumen = texto_resumen_pedido(sesion["pedido"]["items"], sesion["pedido"]["total"])
        texto = (
            f"¡Listo, {sesion['nombre'].split()[0]}! Tu pedido quedó confirmado 🎉\n\n"
            f"{resumen}\n\n"
            f"📍 {sesion['direccion']}\n"
            f"💳 {sesion['metodo_pago']}\n\n"
            f"Cualquier cosa me escribís. ¡Gracias por tu pedido! 🙌"
        )
        respuesta_twilio.message(texto)

        sesion = sesion_nueva()

    sesiones[numero_cliente] = sesion
    guardar_sesiones(sesiones)

    return str(respuesta_twilio)


@app.route("/", methods=["GET"])
def salud():
    return "Bot de la verdulería andando ✅"


if __name__ == "__main__":
    puerto = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=puerto)
