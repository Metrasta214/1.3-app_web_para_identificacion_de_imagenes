// =====================================================
// CONFIGURACIÓN
// =====================================================

const API_URL = "https://1-3-app-web-para-identificacion-de-two.vercel.app/api";

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
// UTILIDADES
// =====================================================

function show(element) {
  if (element) {
    element.classList.remove("hidden");
  }
}

function hide(element) {
  if (element) {
    element.classList.add("hidden");
  }
}

function showError(message) {
  if (!errorMessage) {
    return;
  }

  errorMessage.textContent = message;

  show(errorMessage);
}

function hideError() {
  hide(errorMessage);
}

// =====================================================
// IMAGEN LOCAL
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
// IMAGEN POR URL
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

  hideError();

  const testImage = new Image();

  testImage.onload = () => {
    currentImage = {
      type: "url",

      value: url,
    };

    previewImage.src = url;

    showPreview();
  };

  testImage.onerror = () => {
    showError("No fue posible cargar la imagen desde esa URL.");
  };

  testImage.src = url;
});

// =====================================================
// MOSTRAR PREVIEW
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

  // -----------------------------------------------
  // VALIDAR IMAGEN
  // -----------------------------------------------

  if (!currentImage.value) {
    showError("Primero selecciona una imagen.");

    return;
  }

  // -----------------------------------------------
  // VALIDAR OBJETO
  // -----------------------------------------------

  if (!target) {
    showError("Indica qué quieres que cuente.");

    targetInput.focus();

    return;
  }

  if (target.length > 500) {
    showError("La instrucción supera los 500 caracteres.");

    return;
  }

  // -----------------------------------------------
  // LOADING
  // -----------------------------------------------

  showLoading();

  try {
    const payload = {
      target: target,
    };

    // ---------------------------------------------
    // IMAGEN URL
    // ---------------------------------------------

    if (currentImage.type === "url") {
      payload.image_url = currentImage.value;
    }

    // ---------------------------------------------
    // IMAGEN LOCAL
    // ---------------------------------------------
    else {
      payload.image_data = currentImage.value;
    }

    console.log("================================");

    console.log("TIC VISION");

    console.log("API:", API_URL);

    console.log("OBJETO:", target);

    console.log("TIPO IMAGEN:", currentImage.type);

    console.log("================================");

    // ---------------------------------------------
    // REQUEST
    // ---------------------------------------------

    const response = await fetch(API_URL, {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify(payload),
    });

    // ---------------------------------------------
    // LEER JSON
    // ---------------------------------------------

    let data = {};

    try {
      data = await response.json();
    } catch (jsonError) {
      console.error("No se pudo convertir la respuesta a JSON:", jsonError);

      data = {};
    }

    hideLoading();

    // ---------------------------------------------
    // ERROR HTTP
    // ---------------------------------------------

    if (!response.ok) {
      console.error("RESPUESTA DEL SERVIDOR:", data);

      let mensaje = data.error || `Error HTTP ${response.status}.`;

      if (data.tipo) {
        mensaje += `\nTipo: ${data.tipo}`;
      }

      if (data.detalle) {
        mensaje += `\nDetalle: ${data.detalle}`;
      }

      throw new Error(mensaje);
    }

    // ---------------------------------------------
    // VALIDAR RESULTADO
    // ---------------------------------------------

    if (!data.result) {
      throw new Error("El servidor no devolvió un resultado válido.");
    }

    // ---------------------------------------------
    // MOSTRAR RESULTADO
    // ---------------------------------------------

    mostrarResultado(data.result);
  } catch (error) {
    hideLoading();

    console.error("ERROR AL ANALIZAR:", error);

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
// MARCADORES
// =====================================================

function dibujarMarcadores(detecciones) {
  detecciones.forEach((deteccion, index) => {
    const marker = document.createElement("div");

    marker.classList.add("marker");

    const id = deteccion.id || index + 1;

    marker.innerHTML = `
        <span>
          ${id}
        </span>
      `;

    const x = Number(deteccion.x);

    const y = Number(deteccion.y);

    const safeX = Math.max(0, Math.min(1000, x));

    const safeY = Math.max(0, Math.min(1000, y));

    marker.style.left = `${safeX / 10}%`;

    marker.style.top = `${safeY / 10}%`;

    marker.title = `Elemento ${id}`;

    marker.dataset.number = id;

    markersLayer.appendChild(marker);
  });
}

// =====================================================
// LISTA DE DETECCIONES
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
      return "Acceso denegado. " + "El origen no está autorizado.";

    case 413:
      return "La imagen o solicitud es demasiado grande.";

    case 500:
      return serverMessage || "El servidor tuvo un error interno.";

    case 405:
      return "El endpoint no acepta esta solicitud.";

    default:
      return serverMessage || `Error HTTP ${status}.`;
  }
}

// =====================================================
// NUEVO ANÁLISIS
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


// =========================================================
// AUTO-SCROLL ESTILO CHATGPT
// =========================================================

const workspace = document.querySelector(".workspace");

function scrollToBottom(smooth = true) {
    if (!workspace) return;

    workspace.scrollTo({
        top: workspace.scrollHeight,
        behavior: smooth ? "smooth" : "auto"
    });
}

// Detecta cuando aparecen:
// - vista previa
// - pregunta
// - loading
// - resultado
// - errores
const observer = new MutationObserver(() => {
    requestAnimationFrame(() => {
        scrollToBottom(true);
    });
});

if (workspace) {
    observer.observe(workspace, {
        subtree: true,
        attributes: true,
        attributeFilter: ["class", "style"],
        childList: true
    });
}