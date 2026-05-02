# 📸 ScreenShot Capture Pro

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.8+-green)
![License](https://img.shields.io/badge/license-Commercial-red)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)

**La herramienta profesional para capturas de pantalla con detección instantánea de Print Screen**

[✨ Características](#-características) •
[📥 Instalación](#-instalación) •
[🎮 Uso](#-uso) •
[⚙️ Configuración](#️-configuración) •
[📞 Contacto](#-contacto)

</div>

---

## 🎯 ¿Qué es ScreenShot Capture Pro?

Es una aplicación **profesional y ligera** para Windows que te permite capturar tu pantalla con **precisión milimétrica** y flujo de trabajo optimizado. A diferencia de otras herramientas, **detecta la tecla IMPR PANT al instante** mediante múltiples métodos para que nunca te pierdas una captura.

### ¿Por qué elegir esta?

| Característica | ScreenShot Capture Pro | Otras herramientas |
|:---|:---:|:---:|
| Detección instantánea de Print Screen | ✅ | ❌ (requieren clics) |
| Overlay con zoom y medidas | ✅ | ❌ |
| Captura de múltiples monitores | ✅ | ⚠️ (limitado) |
| Modo oscuro/claro automático | ✅ | ❌ |
| Vista previa integrada | ✅ | ⚠️ |
| Bandeja del sistema | ✅ | ✅ |
| Limpieza automática de archivos | ✅ | ❌ |

---

## ✨ Características Principales

### 🚀 Captura Ultra Rápida
- **Detección triple**: Windows API + pynput + keyboard (siempre funciona)
- **Cooldown inteligente**: Evita capturas duplicadas
- **Captura con un clic**: Botón central o tecla IMPR PANT

### 🎨 Overlay Profesional
- **Selección de área con arrastre**: Precisa y fluida
- **Zoom en tiempo real**: Muestra ampliación de la zona del cursor
- **Mediciones dinámicas**: Te muestra el tamaño exacto de la selección
- **Click derecho**: Captura de pantalla completa inmediata
- **ESC**: Cancela la selección

### 🖼️ Formatos y Calidad
- **Formatos soportados**: PNG, JPEG, BMP
- **Calidad ajustable**: Del 1% al 100% (para JPEG)
- **Compresión optimizada**: Máxima calidad con mínimo tamaño

### 📁 Organización Inteligente
- **Carpeta personalizable**: Elige dónde guardar tus capturas
- **Nombrado automático**: `screenshot_YYYYMMDD_HHMMSS.jpg`
- **Limpieza automática**: Mantén solo las últimas X capturas
- **Estadísticas**: Total de capturas y espacio usado

### 🎛️ Interfaz Completa
- **Modo oscuro/claro**: Se adapta automáticamente a Windows
- **Bandeja del sistema**: Sigue funcionando en segundo plano
- **Vista previa**: Mira la captura antes de decidir qué hacer
- **Copiar al portapapeles**: Pega directamente donde necesites

### 🔒 Seguridad y Licencia
- **Código abierto y auditable**: Todo el código está disponible
- **Licencia hasta 2033**: Sin preocupaciones por años
- **Permisos de administrador**: Detecta la tecla Print Screen en todo el sistema

---

## 📥 Instalación

### Requisitos del Sistema
- **SO**: Windows 10 / 11 (también funciona en Windows 7/8)
- **Python**: 3.8 o superior (si instalas desde código)
- **RAM**: ~100 MB
- **Espacio**: ~50 MB

### Opción 1: Ejecutable (Recomendado para usuarios finales)

Contáctame a: **famp.25333@gmail.com**

### Opción 2: Desde el código fuente (para desarrolladores)

```bash
# 1. Clonar el repositorio
git clone https://github.com/Fampthoms/ScreenShot-Capture-Pro.git
cd ScreenShot-Capture-Pro

# 2. Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python ScreenShot_Capture_Pro.py
