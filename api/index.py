import json
import os

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# =========================================================
# CONFIGURACIÓN
# =========================================================

MODEL = "gpt-4.1-nano"

MAX_TARGET_LENGTH = 500

MAX_BODY_SIZE = 10_000_000

ALLOWED_ORIGIN = os.environ.get(
    "ALLOWED_ORIGIN",
    "https://metrasta214.github.io"
).rstrip("/")


# =========================================================
# INSTRUCCIONES
# =========================================================

INSTRUCTIONS = """
Eres un sistema de análisis visual especializado
en identificación y conteo de objetos en imágenes.

Tu tarea es analizar la imagen proporcionada y contar
únicamente los elementos que el usuario solicite.

No inventes objetos.

No supongas objetos que no sean claramente visibles.

Cada objeto detectado debe aparecer una sola vez.

Debes proporcionar una ubicación aproximada para cada objeto
usando coordenadas normalizadas entre 0 y 1000.

x = posición horizontal del centro del objeto.
y = posición vertical del centro del objeto.
w = ancho aproximado del objeto.
h = alto aproximado del objeto.

La esquina superior izquierda es aproximadamente:
x=0, y=0.

La esquina inferior derecha es aproximadamente:
x=1000, y=1000.
"""


# =========================================================
# HANDLER
# =========================================================

class handler(BaseHTTPRequestHandler):

    # =====================================================
    # CORS
    # =====================================================

    def add_cors_headers(self):

        self.send_header(
            "Access-Control-Allow-Origin",
            ALLOWED_ORIGIN
        )

        self.send_header(
            "Access-Control-Allow-Methods",
            "POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.send_header(
            "Access-Control-Max-Age",
            "86400"
        )

        self.send_header(
            "Vary",
            "Origin"
        )

    # =====================================================
    # RESPUESTA JSON
    # =====================================================

    def send_json(
        self,
        status_code,
        data
    ):

        body = json.dumps(
            data,
            ensure_ascii=False
        ).encode("utf-8")

        self.send_response(
            status_code
        )

        self.send_header(
            "Content-Type",
            "application/json; charset=utf-8"
        )

        self.add_cors_headers()

        self.send_header(
            "Content-Length",
            str(len(body))
        )

        self.end_headers()

        self.wfile.write(
            body
        )

    # =====================================================
    # OPTIONS
    # =====================================================

    def do_OPTIONS(self):

        origin = self.headers.get(
            "Origin",
            ""
        )

        if origin != ALLOWED_ORIGIN:

            self.send_json(
                403,
                {
                    "error": "Origen no autorizado.",
                    "origin_recibido": origin,
                    "origin_esperado": ALLOWED_ORIGIN
                }
            )

            return

        self.send_response(
            204
        )

        self.add_cors_headers()

        self.end_headers()

    # =====================================================
    # GET
    # =====================================================

    def do_GET(self):

        self.send_json(
            200,
            {
                "status": "ok",
                "message":
                    "TIC Vision API funcionando correctamente.",
                "model": MODEL
            }
        )

    # =====================================================
    # POST
    # =====================================================

    def do_POST(self):

        try:

            # ---------------------------------------------
            # CORS
            # ---------------------------------------------

            origin = self.headers.get(
                "Origin",
                ""
            )

            if origin != ALLOWED_ORIGIN:

                self.send_json(
                    403,
                    {
                        "error":
                            "Origen no autorizado.",
                        "origin_recibido":
                            origin,
                        "origin_esperado":
                            ALLOWED_ORIGIN
                    }
                )

                return

            # ---------------------------------------------
            # CONTENT LENGTH
            # ---------------------------------------------

            try:

                content_length = int(
                    self.headers.get(
                        "Content-Length",
                        "0"
                    )
                )

            except ValueError:

                self.send_json(
                    400,
                    {
                        "error":
                            "Content-Length no válido."
                    }
                )

                return

            if (
                content_length <= 0
                or content_length > MAX_BODY_SIZE
            ):

                self.send_json(
                    413,
                    {
                        "error":
                            "La solicitud es demasiado grande."
                    }
                )

                return

            # ---------------------------------------------
            # BODY
            # ---------------------------------------------

            body = self.rfile.read(
                content_length
            )

            try:

                data = json.loads(
                    body.decode("utf-8")
                )

            except Exception as error:

                self.send_json(
                    400,
                    {
                        "error":
                            "El cuerpo no contiene JSON válido.",
                        "detalle":
                            str(error)
                    }
                )

                return

            # ---------------------------------------------
            # TARGET
            # ---------------------------------------------

            target = str(
                data.get(
                    "target",
                    ""
                )
            ).strip()

            if not target:

                self.send_json(
                    400,
                    {
                        "error":
                            "Indica qué quieres que cuente."
                    }
                )

                return

            if len(target) > MAX_TARGET_LENGTH:

                self.send_json(
                    400,
                    {
                        "error":
                            "La instrucción supera el límite permitido."
                    }
                )

                return

            # ---------------------------------------------
            # IMAGEN
            # ---------------------------------------------

            image_url = str(
                data.get(
                    "image_url",
                    ""
                )
            ).strip()

            image_data = str(
                data.get(
                    "image_data",
                    ""
                )
            ).strip()

            if not image_url and not image_data:

                self.send_json(
                    400,
                    {
                        "error":
                            "No se recibió ninguna imagen."
                    }
                )

                return

            if image_url and image_data:

                self.send_json(
                    400,
                    {
                        "error":
                            "Envía una URL o una imagen, no ambas."
                    }
                )

                return

            # ---------------------------------------------
            # API KEY
            # ---------------------------------------------

            api_key = os.environ.get(
                "OPENAI_API_KEY"
            )

            if not api_key:

                self.send_json(
                    500,
                    {
                        "error":
                            "OPENAI_API_KEY no está configurada en Vercel."
                    }
                )

                return

            # ---------------------------------------------
            # CLIENTE
            # ---------------------------------------------

            client = OpenAI(
                api_key=api_key
            )

            # ---------------------------------------------
            # FUENTE DE IMAGEN
            # ---------------------------------------------

            image_source = (
                image_url
                if image_url
                else image_data
            )

            # ---------------------------------------------
            # PROMPT
            # ---------------------------------------------

            prompt = f"""
Analiza la imagen proporcionada.

El usuario quiere contar:

"{target}"

Devuelve exclusivamente un objeto JSON con esta estructura:

{{
    "objeto": "{target}",
    "cantidad": 0,
    "detecciones": [
        {{
            "id": 1,
            "x": 0,
            "y": 0,
            "w": 0,
            "h": 0,
            "confianza": "alta"
        }}
    ],
    "observacion": "string"
}}

REGLAS:

1. Cuenta únicamente los objetos visibles que
   correspondan a la solicitud.

2. No inventes objetos.

3. No cuentes dos veces el mismo objeto.

4. La cantidad debe coincidir exactamente con
   el número de detecciones.

5. Las coordenadas x, y, w y h deben estar
   entre 0 y 1000.

6. x e y representan el centro aproximado
   del objeto.

7. w y h representan el tamaño aproximado
   del objeto.

8. confianza puede ser:
   "alta", "media" o "baja".

9. Si no puedes identificar con suficiente claridad
   el objeto, devuelve cantidad 0.

10. Responde únicamente con JSON válido.
"""

            # ---------------------------------------------
            # REQUEST OPENAI
            # ---------------------------------------------

            response = client.responses.create(

                model=MODEL,

                instructions=INSTRUCTIONS,

                input=[
                    {
                        "role": "user",

                        "content": [
                            {
                                "type": "input_text",
                                "text": prompt
                            },
                            {
                                "type": "input_image",
                                "image_url": image_source,
                                "detail": "low"
                            }
                        ]
                    }
                ],

                max_output_tokens=1500
            )

            # ---------------------------------------------
            # RESPUESTA DEL MODELO
            # ---------------------------------------------

            output_text = (
                response.output_text
            ).strip()

            # ---------------------------------------------
            # CONVERTIR JSON
            # ---------------------------------------------

            try:

                resultado = json.loads(
                    output_text
                )

            except json.JSONDecodeError as error:

                self.send_json(
                    500,
                    {
                        "error":
                            "El modelo no devolvió JSON válido.",
                        "tipo":
                            "JSONDecodeError",
                        "detalle":
                            str(error),
                        "respuesta_modelo":
                            output_text
                    }
                )

                return

            # ---------------------------------------------
            # DETECCIONES
            # ---------------------------------------------

            detecciones = resultado.get(
                "detecciones",
                []
            )

            if not isinstance(
                detecciones,
                list
            ):

                detecciones = []

            # ---------------------------------------------
            # NORMALIZAR DETECCIONES
            # ---------------------------------------------

            detecciones_validas = []

            for index, deteccion in enumerate(
                detecciones,
                start=1
            ):

                if not isinstance(
                    deteccion,
                    dict
                ):

                    continue

                try:

                    x = float(
                        deteccion.get(
                            "x",
                            0
                        )
                    )

                    y = float(
                        deteccion.get(
                            "y",
                            0
                        )
                    )

                    w = float(
                        deteccion.get(
                            "w",
                            0
                        )
                    )

                    h = float(
                        deteccion.get(
                            "h",
                            0
                        )
                    )

                except (
                    TypeError,
                    ValueError
                ):

                    continue

                detecciones_validas.append(
                    {
                        "id":
                            index,

                        "x":
                            max(
                                0,
                                min(
                                    1000,
                                    x
                                )
                            ),

                        "y":
                            max(
                                0,
                                min(
                                    1000,
                                    y
                                )
                            ),

                        "w":
                            max(
                                0,
                                min(
                                    1000,
                                    w
                                )
                            ),

                        "h":
                            max(
                                0,
                                min(
                                    1000,
                                    h
                                )
                            ),

                        "confianza":
                            deteccion.get(
                                "confianza",
                                "no especificada"
                            )
                    }
                )

            # ---------------------------------------------
            # RESULTADO FINAL
            # ---------------------------------------------

            resultado_final = {

                "objeto":
                    target,

                "cantidad":
                    len(
                        detecciones_validas
                    ),

                "detecciones":
                    detecciones_validas,

                "observacion":
                    resultado.get(
                        "observacion",
                        ""
                    )
            }

            # ---------------------------------------------
            # RESPUESTA EXITOSA
            # ---------------------------------------------

            self.send_json(
                200,
                {
                    "result":
                        resultado_final
                }
            )

        except Exception as error:

            # =============================================
            # ERROR REAL
            # =============================================

            print(
                "================================"
            )

            print(
                "ERROR REAL EN TIC VISION"
            )

            print(
                "TIPO:",
                type(error).__name__
            )

            print(
                "DETALLE:",
                str(error)
            )

            print(
                "================================"
            )

            self.send_json(
                500,
                {
                    "error":
                        "Error interno al analizar la imagen.",
                    "tipo":
                        type(error).__name__,
                    "detalle":
                        str(error)
                }
            )