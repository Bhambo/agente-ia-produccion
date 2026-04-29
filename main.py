"""
06 — Agente en Producción

Servidor FastAPI que expone el agente operativo (del proyecto 04)
como una API web con streaming de respuestas.

El frontend (index.html) se conecta a este servidor y muestra
el chat en el navegador, con las letras apareciendo en tiempo real.

Endpoints:
  GET  /          → sirve el frontend (index.html)
  POST /chat      → envía un mensaje y recibe respuesta en streaming
  POST /reset     → limpia el historial de conversación
  GET  /health    → comprueba que el servidor está vivo
"""

import os
import json
import datetime
import urllib.request
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from anthropic import Anthropic

load_dotenv()

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

app = FastAPI(title="Agente IA en Producción")
cliente = Anthropic()
historial = []  # Memoria de conversación (en memoria — se reinicia al parar)

CARPETA_NOTAS = Path("./notas")
CARPETA_NOTAS.mkdir(exist_ok=True)

# ============================================================================
# TOOLS (igual que en el proyecto 04)
# ============================================================================

def obtener_clima(ciudad: str) -> dict:
    try:
        ciudad_encoded = urllib.parse.quote(ciudad)
        url = f"https://wttr.in/{ciudad_encoded}?format=j1"
        req = urllib.request.Request(url, headers={"User-Agent": "agente-ia/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        current = data["current_condition"][0]
        return {
            "ciudad": ciudad,
            "temperatura_c": current["temp_C"],
            "sensacion_c": current["FeelsLikeC"],
            "descripcion": current["weatherDesc"][0]["value"],
            "humedad": current["humidity"],
            "viento_kmh": current["windspeedKmph"],
        }
    except Exception as e:
        return {"error": str(e)}


def buscar_wikipedia(termino: str) -> dict:
    try:
        termino_encoded = urllib.parse.quote(termino.replace(" ", "_"))
        url = f"https://es.wikipedia.org/api/rest_v1/page/summary/{termino_encoded}"
        req = urllib.request.Request(url, headers={"User-Agent": "agente-ia/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode())
        return {
            "titulo": data.get("title", termino),
            "resumen": data.get("extract", "Sin resumen disponible"),
            "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
        }
    except Exception as e:
        return {"error": str(e)}


def guardar_nota(titulo: str, contenido: str) -> dict:
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre = f"{timestamp}_{titulo[:30].replace(' ', '_')}.txt"
        ruta = CARPETA_NOTAS / nombre
        with open(ruta, "w", encoding="utf-8") as f:
            f.write(f"# {titulo}\n\n{contenido}")
        return {"ok": True, "archivo": nombre}
    except Exception as e:
        return {"error": str(e)}


def listar_notas() -> dict:
    try:
        archivos = sorted(CARPETA_NOTAS.glob("*.txt"))
        notas = [{"archivo": f.name,
                  "modificado": datetime.datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")}
                 for f in archivos]
        return {"notas": notas, "total": len(notas)}
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    {
        "name": "obtener_clima",
        "description": "Obtiene el clima actual de una ciudad.",
        "input_schema": {
            "type": "object",
            "properties": {"ciudad": {"type": "string"}},
            "required": ["ciudad"],
        },
    },
    {
        "name": "buscar_wikipedia",
        "description": "Busca información sobre un tema en Wikipedia en español.",
        "input_schema": {
            "type": "object",
            "properties": {"termino": {"type": "string"}},
            "required": ["termino"],
        },
    },
    {
        "name": "guardar_nota",
        "description": "Guarda una nota en disco.",
        "input_schema": {
            "type": "object",
            "properties": {
                "titulo": {"type": "string"},
                "contenido": {"type": "string"},
            },
            "required": ["titulo", "contenido"],
        },
    },
    {
        "name": "listar_notas",
        "description": "Lista todas las notas guardadas.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

SYSTEM = """Eres un asistente operativo inteligente accesible desde la web.
Tienes tools para consultar el clima, buscar en Wikipedia y gestionar notas.
Úsalas cuando sean útiles. Responde siempre en español.
Sé conciso y útil."""


def ejecutar_tool(nombre: str, inputs: dict) -> str:
    if nombre == "obtener_clima":
        return json.dumps(obtener_clima(**inputs), ensure_ascii=False)
    elif nombre == "buscar_wikipedia":
        return json.dumps(buscar_wikipedia(**inputs), ensure_ascii=False)
    elif nombre == "guardar_nota":
        return json.dumps(guardar_nota(**inputs), ensure_ascii=False)
    elif nombre == "listar_notas":
        return json.dumps(listar_notas(), ensure_ascii=False)
    return json.dumps({"error": f"Tool desconocida: {nombre}"})


# ============================================================================
# MODELOS DE REQUEST
# ============================================================================

class MensajeRequest(BaseModel):
    mensaje: str


# ============================================================================
# GENERADOR DE STREAMING
# ============================================================================

def generar_respuesta_streaming(mensaje: str):
    """
    Genera la respuesta del agente como un stream de eventos SSE.
    Maneja el loop de tools internamente y hace streaming del texto final.
    """
    global historial
    historial.append({"role": "user", "content": mensaje})

    # Loop de tools (igual que en el 04, pero con streaming al final)
    while True:
        # ¿Necesita usar tools? Llamada normal (sin streaming)
        respuesta = cliente.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM,
            tools=TOOLS,
            messages=historial,
        )

        historial.append({"role": "assistant", "content": respuesta.content})

        if respuesta.stop_reason == "end_turn":
            # Extrae el texto y lo envía como stream simulado
            for bloque in respuesta.content:
                if hasattr(bloque, "text"):
                    # Envía el texto en chunks para simular streaming
                    texto = bloque.text
                    chunk_size = 10
                    for i in range(0, len(texto), chunk_size):
                        chunk = texto[i:i+chunk_size]
                        yield f"data: {json.dumps({'tipo': 'texto', 'contenido': chunk})}\n\n"
            yield f"data: {json.dumps({'tipo': 'fin'})}\n\n"
            break

        if respuesta.stop_reason == "tool_use":
            resultados_tools = []
            for bloque in respuesta.content:
                if bloque.type == "tool_use":
                    # Notifica al frontend que está usando una tool
                    yield f"data: {json.dumps({'tipo': 'tool', 'nombre': bloque.name})}\n\n"
                    resultado = ejecutar_tool(bloque.name, bloque.input)
                    resultados_tools.append({
                        "type": "tool_result",
                        "tool_use_id": bloque.id,
                        "content": resultado,
                    })
            historial.append({"role": "user", "content": resultados_tools})


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/", response_class=HTMLResponse)
async def frontend():
    """Sirve el frontend."""
    ruta = Path(__file__).parent / "index.html"
    return HTMLResponse(content=ruta.read_text(encoding="utf-8"))


@app.post("/chat")
async def chat(req: MensajeRequest):
    """Recibe un mensaje y devuelve la respuesta en streaming (SSE)."""
    return StreamingResponse(
        generar_respuesta_streaming(req.mensaje),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@app.post("/reset")
async def reset():
    """Limpia el historial de conversación."""
    global historial
    historial = []
    return {"ok": True, "mensaje": "Conversación reiniciada"}


@app.get("/health")
async def health():
    """Comprueba que el servidor está vivo."""
    return {"ok": True, "mensajes_en_historial": len(historial)}
