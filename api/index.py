import json
import os

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# =========================================================
# CONFIGURACIÓN
# =========================================================

MODEL = "gpt-4o-mini"

MAX_TARGET_LENGTH = 500

MAX_BODY_SIZE = 12_000_000

ALLOWED_ORIGIN = os.environ.get(
    "ALLOWED_ORIGIN",
    "https://metrasta214.github.io"
).rstrip("/")


# =========================================================
# INSTRUCCIONES DEL MODELO
# =========================================================

INSTRUCTIONS = """
Eres un sistema de análisis visual especializado
en identificación y conteo de objetos en imágenes.

Debes analizar exclusivamente la imagen proporcionada
y contar los elementos que el usuario solicite.

No inventes objetos.

Solo cuenta elementos que sean visualmente identificables.

Para cada objeto detectado proporciona una posición
aproximada utilizando coordenadas normalizadas de 0 a 1000.

x = posición horizontal del centro del objeto.
y = posición vertical del centro del objeto.
w = ancho aproximado.
h = alto aproximado.

La esquina superior izquierda es aproximadamente:
x=0, y=0

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

        self.wfile.write(body)

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
                    "error":
                        "Origen no autorizado."
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
            405,
            {
                "error":
                    "Este endpoint utiliza POST."
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
                            "Origen no autorizado."
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

            except json.JSONDecodeError:

                self.send_json(
                    400,
                    {
                        "error":
                            "El cuerpo no contiene JSON válido."
                    }
                )

                return

            # ---------------------------------------------
            # OBJETO A CONTAR
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
                            "La instrucción es demasiado larga."
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
                            "Envía una URL o una imagen."
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
                            "OPENAI_API_KEY no está configurada."
                    }
                )

                return

            # ---------------------------------------------
            # CLIENTE OPENAI
            # ---------------------------------------------

            client = OpenAI(
                api_key=api_key
            )

            # ---------------------------------------------
            # IMAGEN
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
Cuenta los elementos correspondientes a:

"{target}"

Analiza toda la imagen cuidadosamente.

Devuelve únicamente JSON válido:

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

1. Cuenta únicamente objetos visibles.

2. No inventes objetos.

3. No cuentes dos veces el mismo objeto.

4. La cantidad debe coincidir con el número
   de detecciones.

5. x, y, w y h deben estar entre 0 y 1000.

6. x e y representan el centro aproximado.

7. w y h representan el tamaño aproximado.

8. confianza puede ser:
   alta, media o baja.

9. Si no puedes identificar claramente
   los objetos, devuelve cantidad 0.

10. Devuelve exclusivamente JSON.
"""

            # ---------------------------------------------
            # RESPONSES API
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
            # TEXTO
            # ---------------------------------------------

            output_text = (
                response.output_text
            ).strip()

            # ---------------------------------------------
            # JSON
            # ---------------------------------------------

            try:

                resultado = json.loads(
                    output_text
                )

            except json.JSONDecodeError:

                self.send_json(
                    500,
                    {
                        "error":
                            "El modelo no devolvió JSON válido."
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

            resultado["cantidad"] = len(
                detecciones
            )

            resultado["objeto"] = target

            if "observacion" not in resultado:

                resultado["observacion"] = ""

            # ---------------------------------------------
            # RESPUESTA
            # ---------------------------------------------

            self.send_json(
                200,
                {
                    "result":
                        resultado
                }
            )

        except Exception as error:

            print(
                "ERROR:"
            )

            print(
                type(error).__name__
            )

            print(
                str(error)
            )

            self.send_json(
                500,
                {
                    "error":
                        "No fue posible analizar la imagen."
                }
            )