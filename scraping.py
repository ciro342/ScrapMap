from playwright.sync_api import sync_playwright
import time
import urllib.parse
import csv
import os
import re
import subprocess

def wame(tel,name):
    print('creando los wa.me para whatsapp....')
    url=f"https://wa.me/{tel}?text=Hola%20{name}%20como%20estas"
    urlreplace=url.replace(" ","%20")
    print('guardando url de contacto....')
    with open("linkswame.txt","a") as f:
         f.write(urlreplace + '\n')
#def enviartxt():
 #       print('------Enviando archivo a mi mismo -------')
  #      with open('linkswame.txt') as f:
   #          contenido = f.read()
    #    if contenido.strip():
     #       subprocess.run(['wacli','send','text','--to','573125270787','--message',f'*links para contactar------------------* \n\n{contenido}'])

scrap = input('ingrese el tipo de negocio = ')
lugar = input('ingrese el lugar = ')

def scraping(servicio):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={'width': 1280, 'height': 720})
        page = context.new_page()

        query = f"{servicio} en {lugar}"
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/maps/search/{encoded_query}"
        print(f" Navegando a: {url}")

        try:
            page.goto(url, timeout=60000)
            print("---Esperando resultados...")
            page.wait_for_selector('div[role="feed"]', timeout=30000)

            ultima_altura = 0
            while True:
                page.evaluate('document.querySelector(\'div[role="feed"]\').scrollBy(0, 3000)')
                time.sleep(2)
                altura_actual = page.evaluate('document.querySelector(\'div[role="feed"]\').scrollHeight')
                if altura_actual == ultima_altura:
                    print("Esperando 3 segundos antes de continuar ....")
                    time.sleep(3)
                    altura_retry = page.evaluate('document.querySelector(\'div[role="feed"]\').scrollHeight')
                    if altura_retry == ultima_altura:
                                print('NO HAY MAS RESULTADOS')
                                break
                    else:
                         ultima_altura=altura_retry
                         print('Cargando mas....')
                         continue
                ultima_altura = altura_actual
                print(f"Cargando más...")

            articulos = page.locator('div[role="article"]').all()
            print(f"🔍 Artículos encontrados: {len(articulos)}")

            archivo = f"{lugar}_{servicio}.csv"
            archivo_nuevo = not os.path.exists(archivo)

            with open(archivo, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if archivo_nuevo:
                    writer.writerow(["Nombre", "Teléfono"])

                encontrados = 0
                for art in articulos:
                    try:
                        nombre = art.locator('div.qBF1Pd').inner_text()
                        telefono_els = art.locator('span.UsdlK').all()
                        telefono = next((t.inner_text() for t in telefono_els if t.inner_text().strip()), None)
                        if telefono:
                            telefono_limpio = re.sub(r'\D', '', telefono) 
                            writer.writerow([nombre, telefono_limpio])
                            print(f"Guardado: {nombre}")
                            encontrados += 1
                            wame(telefono_limpio,nombre)
                    except Exception as e:
                            print(f'ERROR : {e}')

            print(f"\n !Terminado :3 ! Se extrajeron {encontrados} contactos en '{archivo}'.")

        except Exception as e:
            print(f" Error: {e}")
            page.screenshot(path="error_debug.png")
        finally:
            browser.close()

if __name__ == "__main__":
    scraping(scrap)

#enviartxt()
