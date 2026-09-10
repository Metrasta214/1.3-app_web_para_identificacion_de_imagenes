// =====================================================
// CONFIGURACIÓN
// =====================================================

const API_URL =
  "https://1-3-app-web-para-identificacion-de-imagenes.vercel.app/api/chat";

// =====================================================
// ELEMENTOS
// =====================================================

const imageInput = document.getElementById("imageInput");

const uploadZone = document.getElementById("uploadZone");

const imageUrl = document.getElementById("imageUrl");

const loadUrlButton = document.getElementById("loadUrlButton");

const previewSection = document.getElementById("previewSection");

const previewImage = document.getElementById("previewImage");

const removeImageButton = document.getElementById("removeImageButton");

const questionSection = document.getElementById("questionSection");

const targetInput = document.getElementById("targetInput");

const analyzeButton = document.getElementById("analyzeButton");

const resultSection = document.getElementById("resultSection");

const resultCount = document.getElementById("resultCount");

const resultObject = document.getElementById("resultObject");

const annotatedImage = document.getElementById("annotatedImage");

const markersLayer = document.getElementById("markersLayer");

const detectionsList = document.getElementById("detectionsList");

const resultObservation = document.getElementById("resultObservation");

const loading = document.getElementById("loading");

const errorMessage = document.getElementById("errorMessage");

const newAnalysisButton = document.getElementById("newAnalysisButton");

// =====================================================
// ESTADO
// =====================================================

let currentImage = {
  type: null,

  value: null,
};

// =====================================================
// MOSTRAR ELEMENTO
// =====================================================

function show(element) {
  element.classList.remove("hidden");
}

// =====================================================
// OCULTAR ELEMENTO
// =====================================================

function hide(element) {
  element.classList.add("hidden");
}

// =====================================================
// ERROR
// =====================================================

function showError(message) {
  errorMessage.textContent = message;

  show(errorMessage);
}

function hideError() {
  hide(errorMessage);
}

// =====================================================
// CARGAR ARCHIVO
// =====================================================

imageInput.addEventListener("change", () => {
  const file = imageInput.files[0];

  if (!file) {
    return;
  }

  if (!file.type.startsWith("image/")) {
    showError("El archivo seleccionado no es una imagen válida.");

    return;
  }

  const reader = new FileReader();

  reader.onload = () => {
    currentImage = {
      type: "data",

      value: reader.result,
    };

    previewImage.src = reader.result;

    showPreview();

    hideError();
  };

  reader.onerror = () => {
    showError("No fue posible leer la imagen.");
  };

  reader.readAsDataURL(file);
});

// =====================================================
// CARGAR URL
// =====================================================

loadUrlButton.addEventListener("click", () => {
  const url = imageUrl.value.trim();

  if (!url) {
    showError("Escribe una URL de imagen.");

    return;
  }

  if (!url.startsWith("http://") && !url.startsWith("https://")) {
    showError("La URL debe comenzar con http:// o https://.");

    return;
  }

  const testImage = new Image();

  testImage.onload = () => {
    currentImage = {
      type: "url",

      value: url,
    };

    previewImage.src = url;

    showPreview();

    hideError();
  };

  testImage.onerror = () => {
    showError("No fue posible cargar la imagen desde esa URL.");
  };

  testImage.src = url;
});

// =====================================================
// SHOW PREVIEW
// =====================================================

function showPreview() {
  show(previewSection);

  show(questionSection);

  hide(resultSection);

  targetInput.value = "";

  targetInput.focus();

  previewSection.scrollIntoView({
    behavior: "smooth",

    block: "start",
  });
}

// =====================================================
// CAMBIAR IMAGEN
// =====================================================

removeImageButton.addEventListener("click", () => {
  resetImage();

  window.scrollTo({
    top: 0,

    behavior: "smooth",
  });
});

// =====================================================
// ANALIZAR
// =====================================================

analyzeButton.addEventListener("click", analizarImagen);

async function analizarImagen() {
  hideError();

  const target = targetInput.value.trim();

  if (!currentImage.value) {
    showError("Primero selecciona una imagen.");

    return;
  }

  if (!target) {
    showError("Indica qué quieres que cuente.");

    targetInput.focus();

    return;
  }

  if (target.length > 500) {
    showError("La instrucción supera los 500 caracteres.");

    return;
  }

  showLoading();

  try {
    const payload = {
      target: target,
    };

    if (currentImage.type === "url") {
      payload.image_url = currentImage.value;
    } else {
      payload.image_data = currentImage.value;
    }

    const response = await fetch(API_URL, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(payload),
    });

    let data = {};

    try {
      data = await response.json();
    } catch {
      data = {};
    }

    hideLoading();

    if (!response.ok) {
      throw new Error(getErrorMessage(response.status, data.error));
    }

    if (!data.result) {
      throw new Error("El servidor no devolvió un resultado válido.");
    }

    mostrarResultado(data.result);
  } catch (error) {
    hideLoading();

    showError(error.message || "No fue posible analizar la imagen.");
  }
}

// =====================================================
// RESULTADO
// =====================================================

function mostrarResultado(result) {
  const detecciones = Array.isArray(result.detecciones)
    ? result.detecciones
    : [];

  resultCount.textContent = result.cantidad ?? detecciones.length;

  resultObject.textContent = result.objeto || targetInput.value;

  resultObservation.textContent = result.observacion || "";

  annotatedImage.src = previewImage.src;

  markersLayer.innerHTML = "";

  detectionsList.innerHTML = "";

  dibujarMarcadores(detecciones);

  crearListaDetecciones(detecciones);

  show(resultSection);

  resultSection.scrollIntoView({
    behavior: "smooth",

    block: "start",
  });
}

// =====================================================
// DIBUJAR MARCADORES
// =====================================================

function dibujarMarcadores(detecciones) {
  detecciones.forEach((deteccion, index) => {
    const marker = document.createElement("div");

    marker.classList.add("marker");

    const id = deteccion.id || index + 1;

    marker.textContent = id;

    /*
     * x e y vienen normalizados
     * entre 0 y 1000.
     */

    const x = Number(deteccion.x);

    const y = Number(deteccion.y);

    const safeX = Math.max(0, Math.min(1000, x));

    const safeY = Math.max(0, Math.min(1000, y));

    marker.style.left = `${safeX / 10}%`;

    marker.style.top = `${safeY / 10}%`;

    marker.title = `Elemento ${id}`;

    markersLayer.appendChild(marker);
  });
}

// =====================================================
// LISTA
// =====================================================

function crearListaDetecciones(detecciones) {
  if (!detecciones.length) {
    const empty = document.createElement("div");

    empty.classList.add("empty-detections");

    empty.textContent = "No se identificaron elementos suficientes.";

    detectionsList.appendChild(empty);

    return;
  }

  detecciones.forEach((deteccion, index) => {
    const item = document.createElement("div");

    item.classList.add("detection-item");

    const id = deteccion.id || index + 1;

    const confianza = deteccion.confianza || "No especificada";

    item.innerHTML = `

                <span class="detection-number">
                    ${id}
                </span>

                <div>

                    <strong>
                        Elemento ${id}
                    </strong>

                    <span>
                        Confianza: ${confianza}
                    </span>

                </div>

            `;

    detectionsList.appendChild(item);
  });
}

// =====================================================
// LOADING
// =====================================================

function showLoading() {
  show(loading);

  analyzeButton.disabled = true;
}

function hideLoading() {
  hide(loading);

  analyzeButton.disabled = false;
}

// =====================================================
// ERRORES HTTP
// =====================================================

function getErrorMessage(status, serverMessage) {
  switch (status) {
    case 400:
      return serverMessage || "La solicitud no es válida.";

    case 403:
      return "Acceso denegado. " + "El origen de la página no está autorizado.";

    case 413:
      return (
        "La imagen es demasiado grande. " +
        "Selecciona una imagen de menor tamaño."
      );

    case 500:
      return "El servidor no pudo analizar la imagen.";

    default:
      return serverMessage || "Ocurrió un error inesperado.";
  }
}

// =====================================================
// RESET
// =====================================================

newAnalysisButton.addEventListener("click", resetImage);

function resetImage() {
  currentImage = {
    type: null,

    value: null,
  };

  imageInput.value = "";

  imageUrl.value = "";

  targetInput.value = "";

  previewImage.src = "";

  annotatedImage.src = "";

  markersLayer.innerHTML = "";

  detectionsList.innerHTML = "";

  resultObservation.textContent = "";

  resultCount.textContent = "0";

  resultObject.textContent = "—";

  hide(previewSection);

  hide(questionSection);

  hide(resultSection);

  hide(loading);

  hideError();

  window.scrollTo({
    top: 0,

    behavior: "smooth",
  });
}
