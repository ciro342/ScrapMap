from playwright.sync_api import sync_playwright
from groq import Groq
import argparse
import csv
import os
import re
import time
import urllib.parse

MI_NOMBRE = "nombre de tu negocio :v"  
OFERTA = (
    "páginas web para negocios y automatización de procesos "
    "(respuestas, docume1ntos y correos) para negocios y emprendimientos"
)
MODELO = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
PAUSA_API = 2.2  

SISTEMA = f"""Eres {MI_NOMBRE}, una empresa independiente de Colombia que escribe por WhatsApp a dueños de negocios locales. Ofreces: {OFERTA}.
Escribe UN primer mensaje de contacto. Reglas:
- Máximo 4 frases cortas. Tono cercano y respetuoso, español colombiano, sin sonar a vendedor ni a plantilla.
- Salúdalo usando el nombre del negocio y menciona algo específico según su tipo de negocio y su presencia online.
- Preséntate con tu nombre.
- Si el negocio no tiene página web, puedes mencionar que una le ayudaría. Si ya tiene, NO le ofrezcas una: enfócate en ahorrarle trabajo repetitivo.
- Termina con UNA pregunta simple. No des precios ni vendas todavía.
- Incluye una salida amable .
- Máximo 1 emoji. Sin hashtags, sin comillas, sin markdown.
- Responde SOLO con el texto del mensaje."""


def normalizar_tel(tel):
    """Devuelve celular colombiano con indicativo (57...) o None si no sirve para WhatsApp."""
    d = re.sub(r'\D', '', tel or '')
    if len(d) == 10 and d.startswith('3'):
        return '57' + d
    if len(d) == 12 and d.startswith('573'):
        return d
    return None  


REDES = (
    "instagram.com", "facebook.com", "fb.com", "fb.me", "tiktok.com",
    "twitter.com", "x.com", "youtube.com", "youtu.be", "wa.me",
    "wa.link", "whatsapp.com", "linktr.ee", "beacons.ai", "bio.link",
    "taplink.cc", "linkin.bio",
)

def es_red_social(url):
    host = (urllib.parse.urlparse(url).hostname or "").removeprefix("www.")
    return any(host == r or host.endswith("." + r) for r in REDES)


def presencia(web, social):
    if web:
        return "tiene página web"
    if social:
        return "solo tiene red social, sin página web propia"
    return "no tiene página web ni redes sociales visibles"

def mensaje_respaldo(nombre):
    """Se usa si Groq falla o no hay API key."""
    return (
        f"Hola, ¿cómo están en {nombre}? Soy {MI_NOMBRE}, hago {OFERTA}. "
        "¿Les interesaría que les cuente cómo podría ayudarles? "

    )

def generar_mensaje(client, nombre, tipo, contexto):
    """Pide a Groq un mensaje único para este negocio. Nunca lanza excepción."""
    if client is None:
        return mensaje_respaldo(nombre)

    usuario = f"Negocio: {nombre}\nTipo de negocio: {tipo}\nPresencia online: {contexto}"
    extra = {"reasoning_effort": "low"} if "gpt-oss" in MODELO else {}

    for intento in range(2):
        try:
            r = client.chat.completions.create(
                model=MODELO,
                messages=[
                    {"role": "system", "content": SISTEMA},
                    {"role": "user", "content": usuario},
                ],
                temperature=0.9,
                max_tokens=800,
                **extra,
            )
            texto = (r.choices[0].message.content or "").strip().strip('"').strip()
            if texto:
                return texto
            print(f"  Vacío para '{nombre}' (finish_reason={r.choices[0].finish_reason})")
        except Exception as e:
            print(f"  Groq falló para '{nombre}' (intento {intento + 1}): {e}")
            time.sleep(5)  

    return mensaje_respaldo(nombre)


def wame(tel, mensaje):
    return f"https://wa.me/{tel}?text={urllib.parse.quote(mensaje)}"


def cargar_existentes(archivo):
    """Teléfonos ya guardados, para no duplicar al re-ejecutar."""
    if not os.path.exists(archivo):
        return set()
    with open(archivo, encoding="utf-8") as f:
        filas = list(csv.reader(f))[1:]
    return {fila[1] for fila in filas if len(fila) > 1}


def scraping(servicio, lugar, headless=True):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})

        context.route(
            "**/*",
            lambda r: r.abort()
            if r.request.resource_type in ("image", "font", "media")
            else r.continue_()
        )

        page = context.new_page()
        query = f"{servicio} en {lugar}"
        url = f"https://www.google.com/maps/search/{urllib.parse.quote(query)}"
        print(f"Navegando a: {url}")

        try:
            page.goto(url, timeout=60000)
            print("Esperando resultados...")
            page.wait_for_selector('div[role="feed"]', timeout=30000)

            # Scroll sin sleeps fijos
            previo = 0
            while True:
                page.evaluate(
                    "document.querySelector('div[role=\"feed\"]').scrollTo(0, 1e9)"
                )
                try:
                    page.wait_for_function(
                        "n => document.querySelectorAll('div[role=\"article\"]').length > n",
                        arg=previo,
                        timeout=4000,
                    )
                except Exception:
                    print("No hay más resultados")
                    break
                previo = page.locator('div[role="article"]').count()
                print(f"Cargados: {previo}")

            # Extraer todo en una sola llamada al navegador
            datos = page.eval_on_selector_all(
                'div[role="article"]',
                """
                els => els.map(e => ({
                    nombre: e.querySelector('div.qBF1Pd')?.innerText,
                    tel: [...e.querySelectorAll('span.UsdlK')]
                            .map(s => s.innerText).find(t => t.trim()),
                    web: e.querySelector('a[data-value="Sitio web"]')?.href ?? ""
                }))
                """,
            )
            print(f"Artículos encontrados: {len(datos)}")

            archivo = f"{lugar}_{servicio}.csv"
            nuevo = not os.path.exists(archivo)
            vistos = cargar_existentes(archivo)
            nuevos = []  # (nombre, tel, web, social)
            sin_web = 0
            descartados = 0

            with open(archivo, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if nuevo:
                    writer.writerow(["Nombre", "Teléfono", "Web", "Red social"])
                for d in datos:
                    if not d["nombre"] or not d["tel"]:
                        continue
                    tel = normalizar_tel(d["tel"])
                    if not tel:
                        descartados += 1
                        continue
                    if tel in vistos:
                        continue
                    vistos.add(tel)
                    url = d["web"]
                    social = url if url and es_red_social(url) else ""
                    web = "" if social else url
                    writer.writerow([d["nombre"], tel, web, social])
                    nuevos.append((d["nombre"], tel, web, social))
                    if not web:
                        sin_web += 1

            # Generar un mensaje distinto por cada negocio nuevo con Groq
            if nuevos:
                api_key = os.getenv("GROQ_API_KEY")
                client = Groq(api_key=api_key) if api_key else None
                if client is None:
                    print("AVISO: falta GROQ_API_KEY, uso mensaje fijo de respaldo.")

                lineas = []
                for i, (nombre, tel, web, social) in enumerate(nuevos, 1):
                    print(f"Generando mensaje {i}/{len(nuevos)}: {nombre}")
                    msg = generar_mensaje(
                        client, nombre, servicio, presencia(web, social)
                    )
                    lineas.append(f"{nombre} -> {wame(tel, msg)}")
                    if client is not None:
                        time.sleep(PAUSA_API)

                with open("linkswame.txt", "a", encoding="utf-8") as f:
                    f.write("\n".join(lineas) + "\n")

            print(f"\n¡Terminado! {len(nuevos)} contactos nuevos en '{archivo}'.")
            print(f"  - Sin página web (mejores leads): {sin_web}")
            print(f"  - Descartados (fijos/sin WhatsApp): {descartados}")

        except Exception as e:
            print(f"Error: {e}")
            page.screenshot(path="error_debug.png")
        finally:
            browser.close()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scraper de negocios en Google Maps")
    ap.add_argument("negocio", nargs="?", help="tipo de negocio, ej: restaurantes")
    ap.add_argument("lugar", nargs="?", help="ciudad o zona, ej: Aguachica")
    ap.add_argument("--debug", action="store_true", help="muestra el navegador")
    a = ap.parse_args()

    negocio = a.negocio or input('ingrese el tipo de negocio = ')
    lugar = a.lugar or input('ingrese el lugar = ')
    scraping(negocio, lugar, headless=not a.debug)

