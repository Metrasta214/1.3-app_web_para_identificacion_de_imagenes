import json
import os

from http.server import BaseHTTPRequestHandler
from openai import OpenAI


# =========================================================
# CONFIGURACIÓN
# =========================================================

ALLOWED_ORIGIN = os.environ.get(
    "ALLOWED_ORIGIN",
    ""
).rstrip("/")


MODEL = "gpt-4o-mini"

MAX_MESSAGE_LENGTH = 500

MAX_BODY_SIZE = 12000000


INSTRUCTIONS = """
Eres un sistema de análisis visual especializado
en identificación y conteo de objetos presentes
en una imagen.

Tu función es analizar la imagen proporcionada por
el usuario y determinar cuántos elementos corresponden
a lo que el usuario solicita contar.

Debes responder exclusivamente con JSON válido.

No inventes objetos.

Solo cuenta elementos que sean visualmente identificables.

Para cada objeto identificado debes proporcionar
una posición aproximada dentro de la imagen.

La posición debe utilizar coordenadas normalizadas
entre 0 y 1000.

x = posición horizontal.
y = posición vertical.
w = ancho aproximado.
h = alto aproximado.

La esquina superior izquierda corresponde aproximadamente
a x=0, y=0.

La esquina inferior derecha corresponde aproximadamente
a x=1000, y=1000.
"""


# =========================================================
# HANDLER
# =========================================================

class handler(BaseHTTPRequestHandler):

    # =====================================================
    # CORS
    # =====================================================

    def add_cors_headers(self):

        origin = self.headers.get(
            "Origin",
            ""
        )

        if (
            ALLOWED_ORIGIN
            and origin == ALLOWED_ORIGIN
        ):

            self.send_header(
                "Access-Control-Allow-Origin",
                origin
            )

            self.send_header(
                "Vary",
                "Origin"
            )

    # =====================================================
    # JSON RESPONSE
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

        if (
            ALLOWED_ORIGIN
            and origin != ALLOWED_ORIGIN
        ):

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

        self.send_header(
            "Access-Control-Allow-Methods",
            "POST, OPTIONS"
        )

        self.send_header(
            "Access-Control-Allow-Headers",
            "Content-Type"
        )

        self.end_headers()

    # =====================================================
    # GET
    # =====================================================

    def do_GET(self):

        self.send_json(
            405,
            {
                "error":
                    "Este endpoint solamente acepta POST."
            }
        )

    # =====================================================
    # POST
    # =====================================================

    def do_POST(self):

        try:

            # ----------------------------------------------
            # CORS
            # ----------------------------------------------

            origin = self.headers.get(
                "Origin",
                ""
            )

            if (
                ALLOWED_ORIGIN
                and origin != ALLOWED_ORIGIN
            ):

                self.send_json(
                    403,
                    {
                        "error":
                            "Origen no autorizado."
                    }
                )

                return


            # ----------------------------------------------
            # TAMAÑO
            # ----------------------------------------------

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
                            "La imagen o petición es demasiado grande."
                    }
                )

                return


            # ----------------------------------------------
            # BODY
            # ----------------------------------------------

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


            # ----------------------------------------------
            # OBJETO A CONTAR
            # ----------------------------------------------

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
                            "Indica qué quieres contar."
                    }
                )

                return


            if len(target) > MAX_MESSAGE_LENGTH:

                self.send_json(
                    400,
                    {
                        "error":
                            "La instrucción es demasiado larga."
                    }
                )

                return


            # ----------------------------------------------
            # IMAGEN
            # ----------------------------------------------

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


            # No aceptar simultáneamente ambas.
            if image_url and image_data:

                self.send_json(
                    400,
                    {
                        "error":
                            "Envía una URL o una imagen, no ambas."
                    }
                )

                return


            # ----------------------------------------------
            # API KEY
            # ----------------------------------------------

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


            # ----------------------------------------------
            # CLIENTE
            # ----------------------------------------------

            client = OpenAI(
                api_key=api_key
            )


            # ----------------------------------------------
            # FUENTE DE IMAGEN
            # ----------------------------------------------

            if image_url:

                image_source = image_url

            else:

                image_source = image_data


            # ----------------------------------------------
            # PROMPT VISUAL
            # ----------------------------------------------

            prompt = f"""
Cuenta los elementos que correspondan a:

"{target}"

Analiza cuidadosamente toda la imagen.

Devuelve exclusivamente este JSON:

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

1. Cuenta únicamente los elementos visibles
   que correspondan a la solicitud.

2. No inventes elementos.

3. Cada elemento debe aparecer una sola vez.

4. La cantidad debe coincidir exactamente con
   la cantidad de elementos de detecciones.

5. Las coordenadas x, y, w, h deben estar
   entre 0 y 1000.

6. x e y representan el centro aproximado del objeto.

7. w y h representan el tamaño aproximado del objeto.

8. confianza puede ser:
   "alta", "media" o "baja".

9. Si no puedes identificar suficientemente
   los objetos, devuelve cantidad 0.

10. Devuelve únicamente JSON.
"""


            # ----------------------------------------------
            # RESPONSES API
            # ----------------------------------------------

            response = client.responses.create(

                model=MODEL,

                instructions=INSTRUCTIONS,

                input=[
                    {
                        "role": "user",

                        "content": [

                            {
                                "type": "input_text",

                                "text":
                                    prompt
                            },

                            {
                                "type": "input_image",

                                "image_url":
                                    image_source,

                                "detail":
                                    "low"
                            }

                        ]
                    }
                ],

                max_output_tokens=1500
            )


            # ----------------------------------------------
            # RESULTADO
            # ----------------------------------------------

            output_text = (
                response.output_text
            ).strip()


            try:

                resultado = json.loads(
                    output_text
                )

            except json.JSONDecodeError:

                self.send_json(
                    500,
                    {
                        "error":
                            "El modelo no devolvió un JSON válido.",
                        "raw":
                            output_text
                    }
                )

                return


            # ----------------------------------------------
            # VALIDACIÓN
            # ----------------------------------------------

            if not isinstance(
                resultado,
                dict
            ):

                self.send_json(
                    500,
                    {
                        "error":
                            "La respuesta del modelo no tiene un formato válido."
                    }
                )

                return


            detecciones = resultado.get(
                "detecciones",
                []
            )


            if not isinstance(
                detecciones,
                list
            ):

                detecciones = []


            # Asegurar que cantidad corresponda
            # con las detecciones recibidas.

            resultado["cantidad"] = len(
                detecciones
            )


            resultado["objeto"] = target


            # ----------------------------------------------
            # RESPONDER
            # ----------------------------------------------

            self.send_json(
                200,
                {
                    "result":
                        resultado
                }
            )


        except Exception as error:

            print(
                "ERROR EN /api/chat:"
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