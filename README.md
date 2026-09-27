# Bot de WhatsApp con pedidos, stock y clientes (v2)

Esta versión ya no solo responde preguntas: toma el pedido completo,
revisa tu stock real, pide nombre, dirección y forma de pago, y al
final descuenta lo vendido de tu almacén y guarda el pedido.

## Archivos nuevos / cambiados

- **`negocio.json`** — datos generales (nombre, zona, horarios, métodos de pago).
- **`stock.json`** — tu almacén: cada producto con precio y cantidad
  disponible. Se descuenta solo con cada venta confirmada.
- **`app.py`** — toda la lógica del flujo de conversación.
- **`sesiones.json`** y **`pedidos.json`** — se crean solos cuando el
  bot empieza a funcionar. No hace falta tocarlos a mano.
  - `sesiones.json`: en qué paso de la conversación está cada cliente.
  - `pedidos.json`: el historial completo de pedidos — tu "base de datos"
    de clientes (nombre, dirección, qué compraron, cuánto pagaron, cuándo).

## Paso 1 — Cargar tu stock real

Abrí `stock.json` en GitHub y completá, para cada producto:
- `"precio"`: precio actual por kg o unidad
- `"stock_disponible"`: cuánto tenés hoy

Ejemplo:
```json
"Tomate": { "unidad": "kg", "precio": 1500, "stock_disponible": 25 }
```

Podés agregar más productos copiando el mismo formato, o borrar los
que no vendas.

## Paso 2 — Reemplazar los archivos en GitHub

Subí/reemplazá en tu repo `bot-verduleria`: `app.py`, `negocio.json`,
`stock.json`, `requirements.txt` (si cambió) y este `README.md`.

## Paso 2.5 — Activar los comandos de administrador (para vos)

Ahora podés cargar y actualizar el stock **directamente por WhatsApp**,
sin tocar GitHub, escribiéndole al bot desde tu propio número.

1. En Railway, andá a **Variables** y agregá una nueva:
   - Nombre: `OWNER_WHATSAPP`
   - Valor: `whatsapp:+549XXXXXXXXXX` (tu número, con `whatsapp:+` adelante,
     código de país incluido, sin espacios ni guiones). Por ejemplo, si tu
     número es +54 9 261 555 1234, el valor sería `whatsapp:+5492615551234`
2. Guardá — Railway va a reiniciar el bot solo.

A partir de ahí, escribiéndole al bot desde tu WhatsApp (el mismo que
usás para todo esto), podés mandar:

- **`admin ayuda`** — ver la lista de comandos
- **`admin stock`** — ver todo tu stock actual
- **`admin precio Tomate 1500`** — cambiar el precio de un producto
- **`admin cantidad Tomate 25`** — poner cuánto tenés disponible
- **`admin nuevo Acelga kg 800 10`** — agregar un producto que no estaba
- **`admin pedidos`** — ver los últimos 5 pedidos que te hicieron

⚠️ El nombre del producto tiene que escribirse igual a como aparece en
`admin stock` (mayúscula inicial, tal cual). Si te equivocás, el bot
te avisa que no lo encontró.

Con esto, para cargar tu stock inicial real, simplemente le mandás al
bot varios mensajes tipo `admin precio Tomate 1500` y `admin cantidad
Tomate 25` para cada producto, en vez de tocar el archivo en GitHub.

## Paso 3 — MUY IMPORTANTE: agregar un Volume en Railway

Por defecto, cada vez que Railway vuelve a desplegar tu bot (por
ejemplo, cuando editás el código), **borra los archivos que se generan
solos** (`sesiones.json`, `pedidos.json`, y los cambios de stock que
hizo el bot). Para que no se pierdan:

1. En Railway, andá a tu servicio `bot-verduleria`
2. Buscá la pestaña **"Settings"** (⚙️) o el ícono de un disco/base de
   datos, según la versión de la app — buscá algo que diga **"Volumes"**
3. Tocá **"New Volume"** o **"+ Add Volume"**
4. Ponele un **Mount Path** (ruta): `/data`
5. En **"Variables"**, agregá una nueva:
   - Nombre: `DATA_DIR`
   - Valor: `/data`
6. La primera vez, copiá manualmente tu `stock.json` y `negocio.json`
   a esa carpeta (podés hacerlo con la terminal de Railway, o simplemente
   dejar que el bot arranque sin volumen al principio para probar, y
   agregarlo cuando ya estés en confianza con el flujo)

Mientras estás probando, podés arrancar SIN el Volume — el bot
funciona igual, solo que si Railway vuelve a desplegar, el stock
vendido y los pedidos guardados se resetean. Para uso real del
negocio, el Volume es necesario.

## Cómo se ve la conversación con un cliente

```
Cliente: quiero 2 kg de tomate y una lechuga
Bot: Este sería tu pedido:
     • 2 kg de Tomate — $3000
     • 1 unidad de Lechuga — $800

     *Total: $3800*

     ¿Confirmás el pedido así? 🙂

Cliente: sí dale
Bot: Genial 🥬 ¿Me pasás tu nombre y apellido para el pedido?

Cliente: Franco Reyes
Bot: Gracias Franco! ¿A qué dirección te lo llevo?

Cliente: Belgrano 450, Rodeo del Medio
Bot: Perfecto. ¿Cómo vas a pagar: Efectivo o Transferencia?

Cliente: efectivo
Bot: ¡Listo, Franco! Tu pedido quedó confirmado 🎉
     [resumen, dirección, método de pago]
```

Todo esto queda guardado en `pedidos.json`, y el stock de tomate y
lechuga baja automáticamente en `stock.json`.

## Sobre pasar a tu propio número de WhatsApp Business

Ahora mismo el bot funciona sobre el **Sandbox de Twilio** — un número
compartido de prueba al que cada cliente tiene que "unirse" primero
con el código `join tower-exist`. Eso no sirve para clientes reales.

Para que la gente te escriba directo a **tu propio número**, hay que:

1. Tener (o crear) una página de Facebook para tu negocio
2. Crear un **Meta Business Manager** (business.facebook.com) — es gratis
3. En Twilio, ir a **Messaging → Senders → WhatsApp senders → "Register a WhatsApp Sender"**
4. Seguir el asistente: te va a pedir vincular tu Meta Business Manager,
   el número de teléfono que querés usar (no puede estar ya en WhatsApp
   normal — hay que "liberarlo" o usar uno nuevo), nombre del negocio,
   categoría, y una descripción
5. Meta revisa la solicitud — normalmente tarda entre 1 y 3 días hábiles
6. Una vez aprobado, cambiás el webhook de ese número (no del sandbox)
   a la misma URL de Railway que ya tenés, y listo

Este trámite lo hacemos juntos cuando quieras avanzar — es más lento
que técnico (hay que esperar la aprobación de Meta), pero el código del
bot no cambia en nada.
