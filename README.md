# ScrapMap

Scraper de negocios en Google Maps que genera, con IA (Groq), un mensaje de primer contacto distinto para cada negocio y lo deja listo en un link de `wa.me`.

El script **no envía nada**: tú abres cada link y das enviar a mano.

## Qué hace

1. Busca `"<tipo de negocio> en <lugar>"` en Google Maps con Playwright y carga todos los resultados.
2. Extrae nombre, teléfono y sitio web.
3. Se queda solo con celulares colombianos (descarta fijos) y los normaliza con indicativo `57`.
4. Clasifica la presencia online: tiene web, solo red social, o nada.
5. Guarda los contactos en un CSV, sin duplicar al re-ejecutar.
6. Le pide a Groq un mensaje corto por negocio, según su nombre, tipo y presencia online.
7. Escribe en `linkswame.txt` una línea por negocio: `Nombre -> https://wa.me/57...?text=...`

## Requisitos

- Python 3.10 o superior
- Una API key de Groq (tier gratis)

## Instalación

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

## API key

El script lee la key de la variable de entorno `GROQ_API_KEY`:

```bash
export GROQ_API_KEY="gsk_tu_key"
```

Para dejarla permanente, agrégala a `~/.bashrc` o `~/.zshrc`. Nunca la pegues dentro del código si vas a subirlo a GitHub.

Si no hay key, el script no se cae: usa un mensaje fijo de respaldo.

## Uso

```bash
python scraping.py restaurantes Aguachica
python scraping.py                      # te pregunta tipo de negocio y lugar
python scraping.py ferreterias Aguachica --debug   # muestra el navegador
```

## Salida

| Archivo | Contenido |
|---|---|
| `<lugar>_<negocio>.csv` | Nombre, Teléfono, Web, Red social |
| `linkswame.txt` | Un link `wa.me` con mensaje ya escrito por negocio |
| `error_debug.png` | Captura si el scraping falla |

Los dos primeros se acumulan entre ejecuciones. Si cambias el prompt y quieres regenerar los mensajes, borra `linkswame.txt` y el CSV correspondiente, porque los teléfonos ya guardados se saltan.

## Configuración

Al inicio de `scraping.py`:

- `MI_NOMBRE`: cómo te presentas en el mensaje.
- `OFERTA`: qué ofreces. Va dentro del prompt y del mensaje de respaldo.
- `SISTEMA`: el prompt con las reglas del mensaje (longitud, tono, salida amable, etc.).
- `PAUSA_API`: segundos entre llamadas a Groq, para respetar el límite del tier gratis.

### Cambiar de modelo

Sin tocar el código:

```bash
export GROQ_MODEL="openai/gpt-oss-20b"
```

Para ver qué modelos tiene tu cuenta:

```bash
curl -s https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"
```

Elige uno de texto. Los modelos de razonamiento (`gpt-oss`, `qwen3`, etc.) gastan tokens "pensando", así que `max_tokens` en `generar_mensaje` debe ser holgado (800 o más), o devolverán el mensaje vacío y se usará el de respaldo.

## Solución de problemas

- **Todos los mensajes salen iguales y genéricos:** es el mensaje de respaldo. Revisa que `GROQ_API_KEY` esté definida (`echo $GROQ_API_KEY`) y mira en la terminal el error que imprime Groq.
- **`model_not_found`:** ese modelo ya no existe en tu cuenta. Consulta la lista con el `curl` de arriba.
- **Salida vacía (`finish_reason=length`):** sube `max_tokens`.
- **No encuentra resultados o falla el scraping:** Google cambia las clases CSS de Maps (`div.qBF1Pd`, `span.UsdlK`). Corre con `--debug`, inspecciona y actualiza los selectores.

## Uso responsable

- **Envía tú mismo, no automatices el envío.** WhatsApp bloquea por comportamiento (muchos desconocidos, pocas respuestas, reportes de spam), no por el texto.
- Mantente en unos 20-30 mensajes al día y usa un número que no sea tu principal.
- Preséntate, haz una pregunta simple y respeta el "no". No le escribas de nuevo a quien lo diga.
- En Colombia aplica la Ley 1581 de 2012 (habeas data). Los datos son públicos de Google Maps, pero identifícate y ofrece salida clara.
- Revisa los mensajes antes de enviarlos: la IA puede equivocarse.

## .gitignore recomendado

Los CSV y `linkswame.txt` contienen datos de terceros, no los subas:

```
venv/
__pycache__/
*.csv
linkswame.txt
error_debug.png
.env
```
