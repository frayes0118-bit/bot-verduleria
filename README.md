# Bot de WhatsApp para la verdulería (100% gratis)

Este bot responde automáticamente a tus clientes por WhatsApp usando
Google Gemini (gratis, sin tarjeta), con los precios y productos que
vos cargás en `negocio.json`.

## Paso 1 — Editar tus datos

Abrí `negocio.json` y completá:
- El nombre de tu negocio
- Tu zona de delivery
- Tus productos y precios reales de hoy

Guardalo cada vez que cambien los precios.

## Paso 2 — Crear cuenta en Twilio y activar el WhatsApp Sandbox

1. Andá a twilio.com/try-twilio y registrate.
2. Buscá (con la lupa) **"Try WhatsApp"** o **"WhatsApp Sandbox"**.
3. Vas a ver un número de Twilio y un código para conectarte
   (ej: `join palabra-clave`).
4. Desde tu WhatsApp normal, mandale ese código exacto a ese número.

## Paso 3 — Conseguir tu API key de Gemini (gratis, sin tarjeta)

1. Andá a **aistudio.google.com/apikey** (Google AI Studio).
2. Iniciá sesión con tu cuenta de Google.
3. Tocá **"Create API key"**.
4. Copiá la clave que te da (empieza distinto según el momento, pero
   es una cadena larga de letras y números).
5. Esto no pide tarjeta ni tarjeta de crédito — es gratis dentro de
   los límites de uso diario, que para una verdulería alcanzan de sobra.

## Paso 4 — Subir el código a GitHub

1. Andá a github.com y entrá con tu cuenta.
2. **"+" → "New repository"** → nombre `bot-verduleria` → "Create repository".
3. **"Add file" → "Upload files"** → subí `app.py`, `negocio.json`,
   `requirements.txt`, `README.md`.
4. **"Commit changes"**.

## Paso 5 — Desplegar en Railway

1. Andá a railway.app y entrá con tu cuenta de GitHub.
2. **"New Project" → "Deploy from GitHub repo"** → elegí `bot-verduleria`.
3. En la pestaña **"Variables"**, agregá:
   - `GEMINI_API_KEY` = la clave que copiaste en el Paso 3
4. Si te pide Start Command, poné: `gunicorn app:app`
5. Cuando termine el deploy, andá a **"Settings" → "Networking" →
   "Generate Domain"** para conseguir tu URL pública.

## Paso 6 — Conectar Twilio con tu bot

1. Volvé a la pantalla del Sandbox de Twilio (Paso 2).
2. En **"When a message comes in"**, pegá tu URL de Railway + `/webhook`:
   `https://tu-bot-verduleria.up.railway.app/webhook`
3. Guardá.

## Paso 7 — Probarlo

Desde tu WhatsApp, escribile algo al número de Twilio, por ejemplo
"¿tenés tomate?" — el bot debería responderte con el precio que
cargaste en `negocio.json`.

## Sobre los costos

- Twilio Sandbox: gratis para probar (limitado a quienes mandan el
  código "join...").
- Gemini API: gratis dentro del límite diario de uso, sin tarjeta.
- Railway: tiene un plan gratuito con horas limitadas por mes; para
  un bot que recibe mensajes ocasionales de WhatsApp, alcanza de sobra
  para empezar.

Cuando quieras pasar a producción real (tu propio número de WhatsApp
Business, verificado por Meta), es un trámite aparte — pero el código
del bot no cambia.
