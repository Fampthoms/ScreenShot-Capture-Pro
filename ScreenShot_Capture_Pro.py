"""
ScreenShot Capture Pro - Versión Mejorada
Aplicación profesional para capturas de pantalla con detección confiable de Print Screen
"""

import sys
import os
import datetime
import tempfile
import threading
import time
import traceback
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import io
import win32api
import win32con
import win32clipboard
import win32gui
import datetime

# ==================== IMPORTS DE PYSIDE6 ====================
from PySide6.QtCore import (
    Qt, QRect, QPoint, QTimer, Signal, Slot, QSize, QSettings
)
from PySide6.QtGui import (
    QAction, QPainter, QPen, QBrush, QColor, QFont, QPixmap, 
    QGuiApplication, QClipboard, QIcon, QCursor, QImage
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSystemTrayIcon, QMenu, QFileDialog,
    QMessageBox, QDialog, QDialogButtonBox, QGroupBox, QCheckBox,
    QSpinBox, QComboBox, QSlider, QLineEdit, QFrame, QGridLayout,
    QProgressBar, QListWidget, QListWidgetItem, QScrollArea, QSizePolicy,
)

from PIL import ImageGrab, Image, ImageQt

# ==================== IMPORTS PARA HOTKEYS ====================
# Intentar importar pynput
PYNPUT_AVAILABLE = False
try:
    from pynput import keyboard as pynput_keyboard
    PYNPUT_AVAILABLE = True
except ImportError:
    pass

# Intentar importar keyboard como respaldo
KEYBOARD_AVAILABLE = False
try:
    import keyboard
    KEYBOARD_AVAILABLE = True
except ImportError:
    pass

# Variables globales para control de captura
_capture_in_progress = False
_last_capture_time = 0
CAPTURE_COOLDOWN = 0.5  # Segundos entre capturas

# ==================== EJECUTAR COMO ADMINISTRADOR ====================

def is_admin():
    """Verificar si el programa se ejecuta como administrador"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Reiniciar el programa como administrador"""
    try:
        # Obtener la ruta completa del script actual
        script_path = os.path.abspath(sys.argv[0])
        
        # Construir los argumentos
        args = [script_path]
        if len(sys.argv) > 1:
            args.extend(sys.argv[1:])
        
        # Ejecutar con permisos de administrador
        ctypes.windll.shell32.ShellExecuteW(
            None,           # hwnd
            "runas",        # operación
            sys.executable, # archivo a ejecutar (python.exe)
            " ".join(args), # argumentos
            None,           # directorio
            1               # ventana normal
        )
        print("✅ Solicitando permisos de administrador...")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error al solicitar permisos de administrador: {e}")
        input("Presiona Enter para salir...")
        sys.exit(1)

# ==================== FUNCIÓN GLOBAL PARA BOTONES ====================
def init_adaptive_buttons(app, padding_h=20, padding_v=12):
    """
    Inicializa todos los botones de la aplicación para que se adapten al texto.
    Colocar esta función al inicio del main(), después de crear QApplication.
    
    Parámetros:
    - app: QApplication instance
    - padding_h: Padding horizontal en píxeles
    - padding_v: Padding vertical en píxeles
    """
    from PySide6.QtWidgets import QPushButton
    from PySide6.QtCore import QTimer
    
    # Aplicar estilo base
    app.setStyleSheet(f"""
        QPushButton {{
            padding: {padding_v}px {padding_h}px;
            border: none;
            border-radius: 6px;
            font-weight: bold;
        }}
    """)
    
    # Función para ajustar un botón específico
    def adjust_button(button):
        def do_adjust():
            if not button or not button.text():
                return
            try:
                fm = button.fontMetrics()
                text_width = fm.horizontalAdvance(button.text())
                text_height = fm.height()
                button.setFixedSize(
                    max(100, text_width + padding_h * 2),
                    max(40, text_height + padding_v * 2)
                )
            except Exception as e:
                # Si hay error, usar tamaño por defecto
                button.setFixedSize(120, 40)
        QTimer.singleShot(0, do_adjust)
    
    # Función para procesar todos los botones de un widget
    def process_widget(widget):
        try:
            buttons = widget.findChildren(QPushButton)
            for button in buttons:
                adjust_button(button)
        except Exception as e:
            print(f"Error procesando botones: {e}")
        return adjust_button
    
    return process_widget

# ============== Funcion para la Licencia de la APP =======================

def check_license():
    """Verificar si la licencia ha expirado"""
    # FECHA DE EXPIRACIÓN (cámbiala cuando quieras)
    EXPIRATION_DATE = datetime.date(2033, 12, 31)
    
    today = datetime.date.today()
    
    if today > EXPIRATION_DATE:
        # Mostrar mensaje de error
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("🔒 Licencia Expirada")
        msg.setText(f"❌ La licencia expiró el {EXPIRATION_DATE.strftime('%d/%m/%Y')}\n\n")
        msg.setInformativeText(
            "Esta versión del software ya no es válida.\n\n"
            "Por favor contacta al desarrollador para renovar:\n"
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        sys.exit(1)
    
    # Mostrar días restantes (opcional)
    days_left = (EXPIRATION_DATE - today).days
    if days_left <= 30 and days_left > 0:
        print(f"⚠️ Atención: Tu licencia expira en {days_left} días")
    
    return True

def is_frozen_application():
    """Detectar si la app está empaquetada con PyInstaller"""
    return getattr(sys, 'frozen', False)

def get_settings_path():
    """Obtener ruta segura para guardar configuraciones"""
    if is_frozen_application():
        # Usar archivo local en AppData para ejecutables
        app_data = os.path.join(os.environ.get('APPDATA', ''), 'ScreenShotCapturePro')
        os.makedirs(app_data, exist_ok=True)
        return os.path.join(app_data, 'config.ini')
    else:
        # Modo desarrollo - usar QSettings normal
        return None

def safe_settings(org_name="ScreenShotPro", app_name="Settings"):
    """Wrapper seguro para QSettings que no deja basura en el registro"""
    if is_frozen_application():
        # Usar archivo INI en lugar de registro
        from PySide6.QtCore import QSettings as QSettingsQt
        config_path = get_settings_path()
        if config_path:
            settings = QSettingsQt(config_path, QSettingsQt.Format.IniFormat)
            settings.setValue("_version", "1.0")
            return settings
    # Modo normal o fallback
    from PySide6.QtCore import QSettings
    return QSettings(org_name, app_name)

@dataclass
class AppConfig:
    """Configuración de la aplicación"""
    save_folder: str = os.path.join(os.path.expanduser('~'), 'Documents', 'ScreenCaptures')
    default_format: str = 'PNG'
    quality: int = 95
    auto_open: bool = False
    backup_count: int = 100
    min_capture_size: int = 5
    show_preview: bool = True
    copy_to_clipboard: bool = False
    sound_effect: bool = False
    dark_mode: bool = False
    hotkey: str = 'print_screen'  # print_screen, ctrl+shift+s, f12


class ThemeManager:
    """Gestor de temas con detección automática de color"""
    
    @staticmethod
    def is_dark_mode() -> bool:
        """Detectar si el sistema está en modo oscuro"""
        try:
            if sys.platform == 'win32':
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(registry, r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize')
                value, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return value == 0
        except:
            pass
        return False
    
    @staticmethod
    def get_theme_colors(dark: bool = None) -> dict:
        """Obtener colores basados en el tema"""
        if dark is None:
            dark = ThemeManager.is_dark_mode()
        
        if dark:
            return {
                'bg_primary': '#1e1e2f',
                'bg_secondary': '#2d2d3a',
                'bg_tertiary': '#3a3a4a',
                'text_primary': '#ffffff',
                'text_secondary': '#b0b0c0',
                'accent': '#4c9aff',
                'accent_hover': '#5ca8ff',
                'success': '#4caf50',
                'warning': '#ff9800',
                'error': '#f44336',
                'border': '#4a4a5a',
                'selection': '#4c9aff80'
            }
        else:
            return {
                'bg_primary': '#f5f5f7',
                'bg_secondary': '#ffffff',
                'bg_tertiary': '#e8e8ec',
                'text_primary': '#2c2c34',
                'text_secondary': '#5a5a66',
                'accent': '#2196f3',
                'accent_hover': '#42a5f5',
                'success': '#4caf50',
                'warning': '#ff9800',
                'error': '#f44336',
                'border': '#d0d0d8',
                'selection': '#2196f380'
            }


class HotkeyManager:
    """Gestor centralizado de hotkeys con múltiples métodos"""
    
    def __init__(self, callback):
        self.callback = callback
        self.listener = None
        self.keyboard_thread = None
        self.running = False
        
    def start(self):
        """Iniciar el gestor de hotkeys"""
        self.running = True
        
        # Método 1: Usar pynput (más confiable)
        if PYNPUT_AVAILABLE:
            self._start_pynput()
        
        # Método 2: Usar keyboard como respaldo
        if KEYBOARD_AVAILABLE:
            self._start_keyboard()
        
        # Método 3: Hook global de Windows (como último recurso)
        if sys.platform == 'win32':
            self._start_win32_hook()
    
    def _start_pynput(self):
        """Iniciar listener con pynput"""
        try:
            def on_press(key):
                global _capture_in_progress, _last_capture_time
                
                try:
                    # Detectar Print Screen
                    if key == pynput_keyboard.Key.print_screen:
                        print("🎯 [pynput] Print Screen detectado!")
                        self._trigger_capture()
                    # Detectar Ctrl+Shift+S
                    elif hasattr(key, 'char') and key.char == 'S':
                        if self._ctrl_pressed and self._shift_pressed:
                            print("🎯 [pynput] Ctrl+Shift+S detectado!")
                            self._trigger_capture()
                except Exception as e:
                    print(f"Error en pynput: {e}")
            
            def on_release(key):
                try:
                    if key == pynput_keyboard.Key.ctrl_l or key == pynput_keyboard.Key.ctrl_r:
                        self._ctrl_pressed = False
                    elif key == pynput_keyboard.Key.shift_l or key == pynput_keyboard.Key.shift_r:
                        self._shift_pressed = False
                except:
                    pass
            
            def on_press_full(key):
                try:
                    # Actualizar estado de teclas modificadoras
                    if key == pynput_keyboard.Key.ctrl_l or key == pynput_keyboard.Key.ctrl_r:
                        self._ctrl_pressed = True
                    elif key == pynput_keyboard.Key.shift_l or key == pynput_keyboard.Key.shift_r:
                        self._shift_pressed = True
                    # Detectar Print Screen
                    elif key == pynput_keyboard.Key.print_screen:
                        print("🎯 [pynput] Print Screen detectado!")
                        self._trigger_capture()
                    # Detectar Ctrl+Shift+S
                    elif hasattr(key, 'char') and key.char == 's':
                        if self._ctrl_pressed and self._shift_pressed:
                            print("🎯 [pynput] Ctrl+Shift+S detectado!")
                            self._trigger_capture()
                except Exception as e:
                    print(f"Error en pynput: {e}")
            
            self._ctrl_pressed = False
            self._shift_pressed = False
            
            self.listener = pynput_keyboard.Listener(on_press=on_press_full, on_release=on_release)
            self.listener.daemon = True
            self.listener.start()
            print("✅ [pynput] Listener iniciado correctamente")
        except Exception as e:
            print(f"❌ Error iniciando pynput: {e}")
    
    def _start_keyboard(self):
        """Iniciar listener con keyboard"""
        try:
            import keyboard
            
            # Registrar hotkey para Print Screen
            keyboard.add_hotkey('print screen', self._trigger_capture, suppress=True)
            keyboard.add_hotkey('ctrl+shift+s', self._trigger_capture, suppress=True)
            
            # Iniciar thread
            self.keyboard_thread = threading.Thread(target=keyboard.wait, daemon=True)
            self.keyboard_thread.start()
            print("✅ [keyboard] Hotkeys registrados correctamente")
        except Exception as e:
            print(f"❌ Error iniciando keyboard: {e}")
    
    def _start_win32_hook(self):
        """Iniciar hook global de Windows (como último recurso)"""
        try:
            import ctypes
            from ctypes import wintypes
            
            user32 = ctypes.windll.user32
            
            # Definir constantes
            WH_KEYBOARD_LL = 13
            WM_KEYDOWN = 0x0100
            VK_SNAPSHOT = 0x2C  # Print Screen
            
            # Callback del hook
            HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            
            self._hook_callback = None
            
            def keyboard_hook(nCode, wParam, lParam):
                if nCode >= 0 and wParam == WM_KEYDOWN:
                    # Verificar si es Print Screen
                    if lParam and ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong)).contents.value == VK_SNAPSHOT:
                        print("🎯 [Win32] Print Screen detectado!")
                        self._trigger_capture()
                        return 1  # Bloquear la tecla
                return user32.CallNextHookExW(None, nCode, wParam, lParam)
            
            self._hook_callback = HOOKPROC(keyboard_hook)
            hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, self._hook_callback, None, 0)
            
            # Iniciar thread para el message loop
            def message_loop():
                msg = wintypes.MSG()
                while self.running:
                    user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            
            self.win32_thread = threading.Thread(target=message_loop, daemon=True)
            self.win32_thread.start()
            print("✅ [Win32] Hook global iniciado correctamente")
        except Exception as e:
            print(f"❌ Error iniciando hook Win32: {e}")
    
    def _trigger_capture(self):
        """Disparar la captura con cooldown"""
        global _capture_in_progress, _last_capture_time
        
        current_time = time.time()
        
        # Verificar cooldown
        if current_time - _last_capture_time < CAPTURE_COOLDOWN:
            print("⏱️ Captura ignorada (cooldown activo)")
            return
        
        if _capture_in_progress:
            print("⏱️ Captura ignorada (ya hay una en progreso)")
            return
        
        _capture_in_progress = True
        _last_capture_time = current_time
        
        # Disparar callback en el hilo principal
        QTimer.singleShot(0, self._safe_callback)
    
    def _safe_callback(self):
        """Ejecutar callback de forma segura"""
        try:
            self.callback()
        except Exception as e:
            print(f"Error en callback: {e}")
            traceback.print_exc()
        finally:
            global _capture_in_progress
            _capture_in_progress = False
    
    def stop(self):
        """Detener todos los listeners"""
        self.running = False
        
        if self.listener:
            try:
                self.listener.stop()
            except:
                pass
        
        if KEYBOARD_AVAILABLE:
            try:
                import keyboard
                keyboard.unhook_all()
            except:
                pass


class SelectionOverlay(QWidget):
    """Ventana de selección de área con overlay"""
    
    selection_completed = Signal(QRect)
    cancelled = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Variables de selección
        self.start_pos: Optional[QPoint] = None
        self.end_pos: Optional[QPoint] = None
        self.selection_rect: Optional[QRect] = None
        self.dragging = False
        
        # Capturar pantalla completa
        self.screen_pixmap = None
        self.capture_fullscreen()
        
        # Configurar cursor
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        
        # Colores
        self.overlay_color = QColor(0, 0, 0, 150)
        self.selection_color = QColor(76, 154, 255, 80)
        self.border_color = QColor(76, 154, 255)
        
        # Configurar tamaño
        self.showFullScreen()
        
        # Etiqueta de información
        self.info_label = QLabel("🔍 Arrastra para seleccionar | ESC para cancelar | Click derecho = pantalla completa", self)
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0,0,0,0.7);
                color: white;
                padding: 8px 16px;
                border-radius: 8px;
                font-size: 12px;
                font-weight: bold;
            }
        """)
        self.info_label.move(20, 20)
        self.info_label.adjustSize()
        
        # Zoom label
        self.zoom_label = QLabel(self)
        self.zoom_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0,0,0,0.6);
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-family: monospace;
                font-size: 11px;
            }
        """)
        self.zoom_label.hide()
        
    def capture_fullscreen(self):
        """Capturar pantalla completa"""
        try:
            from PIL import ImageGrab
            
            # Capturar toda la pantalla con Pillow
            img = ImageGrab.grab(all_screens=True)
            
            # Convertir a QPixmap
            from PIL.ImageQt import ImageQt
            qimage = ImageQt(img)
            self.screen_pixmap = QPixmap.fromImage(qimage)
            
            print(f"✅ Overlay - Pantalla capturada: {self.screen_pixmap.width()}x{self.screen_pixmap.height()}")
            
        except Exception as e:
            print(f"Error capturando pantalla para overlay: {e}")
            # Método alternativo con Qt
            try:
                screen = QGuiApplication.primaryScreen()
                if screen:
                    self.screen_pixmap = screen.grabWindow(0)
                    print(f"✅ Overlay - Pantalla capturada con Qt: {self.screen_pixmap.width()}x{self.screen_pixmap.height()}")
            except Exception as e2:
                print(f"Error también con Qt: {e2}")
    
    def paintEvent(self, event):
        """Dibujar el overlay y la selección"""
        painter = QPainter(self)
        
        # Dibujar fondo semi-transparente
        painter.fillRect(self.rect(), self.overlay_color)
        
        # Si hay selección, dibujar el área seleccionada
        if self.selection_rect and self.screen_pixmap:
            # Mostrar el área de la pantalla dentro de la selección
            painter.drawPixmap(self.selection_rect, self.screen_pixmap, self.selection_rect)
            
            # Borde de selección
            painter.setPen(QPen(self.border_color, 2, Qt.PenStyle.SolidLine))
            painter.drawRect(self.selection_rect)
            
            # Dibujar tamaño
            painter.setPen(QPen(Qt.GlobalColor.white, 1))
            painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
            
            size_text = f"📐 {self.selection_rect.width()} × {self.selection_rect.height()}"
            text_rect = painter.boundingRect(QRect(), Qt.AlignmentFlag.AlignLeft, size_text)
            
            text_x = self.selection_rect.x()
            text_y = self.selection_rect.y() - text_rect.height() - 5
            
            if text_y < 0:
                text_y = self.selection_rect.y() + self.selection_rect.height() + 5
            
            painter.fillRect(
                text_x - 5, text_y - 2, text_rect.width() + 10, text_rect.height() + 4,
                QColor(0, 0, 0, 180)
            )
            painter.drawText(text_x, text_y, size_text)
    
    def mousePressEvent(self, event):
        """Inicio de selección"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_pos = event.position().toPoint()  # Cambiar pos() por position().toPoint()
            self.dragging = True
            self.selection_rect = None
        elif event.button() == Qt.MouseButton.RightButton:
            # Click derecho = captura de pantalla completa
            self.selection_completed.emit(QRect(0, 0, self.width(), self.height()))
            self.close()

    def mouseMoveEvent(self, event):
        """Actualizar selección"""
        if self.dragging and self.start_pos:
            self.end_pos = event.position().toPoint()  # Cambiar pos() por position().toPoint()
            self.selection_rect = QRect(self.start_pos, self.end_pos).normalized()
            
            # Mostrar zoom
            if self.screen_pixmap:
                cursor_pos = event.position().toPoint()  # Cambiar pos() por position().toPoint()
                self.show_zoom(cursor_pos)
            
            self.update()
    
    def show_zoom(self, pos: QPoint):
        """Mostrar zoom en la posición del cursor"""
        zoom_size = 100
        zoom_rect = QRect(
            pos.x() - zoom_size//2,
            pos.y() - zoom_size//2,
            zoom_size, zoom_size
        ).intersected(self.rect())
        
        if zoom_rect.width() > 0 and zoom_rect.height() > 0:
            zoom_pixmap = self.screen_pixmap.copy(zoom_rect)
            if not zoom_pixmap.isNull():
                zoom_pixmap = zoom_pixmap.scaled(
                    zoom_size * 2, zoom_size * 2,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                self.zoom_label.setPixmap(zoom_pixmap)
                self.zoom_label.adjustSize()
                
                label_x = pos.x() + 15
                label_y = pos.y() + 15
                
                if label_x + self.zoom_label.width() > self.width():
                    label_x = pos.x() - self.zoom_label.width() - 15
                if label_y + self.zoom_label.height() > self.height():
                    label_y = pos.y() - self.zoom_label.height() - 15
                
                self.zoom_label.move(label_x, label_y)
                self.zoom_label.show()
    
    def mouseReleaseEvent(self, event):
        """Finalizar selección"""
        if event.button() == Qt.MouseButton.LeftButton and self.dragging and self.selection_rect:
            if self.selection_rect.width() > 5 and self.selection_rect.height() > 5:
                self.selection_completed.emit(self.selection_rect)
            else:
                self.cancelled.emit()
            self.close()
        elif event.button() == Qt.MouseButton.LeftButton:
            self.cancelled.emit()
            self.close()
    
    def keyPressEvent(self, event):
        """Manejar teclas"""
        if event.key() == Qt.Key.Key_Escape:
            self.cancelled.emit()
            self.close()


class PreviewDialog(QDialog):
    """Diálogo de vista previa de captura"""
    
    def __init__(self, pixmap: QPixmap, filepath: str, parent=None, dark_mode: bool = False):
        super().__init__(parent)
        self.pixmap = pixmap
        self.filepath = filepath
        self.dark_mode = dark_mode
        
        self.setWindowTitle("📸 Vista Previa - ScreenShot Capture Pro By FampThoms")
        self.setModal(True)
        self.resize(800, 600)
        
        self.setup_ui()
        self.apply_theme()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        # Scroll area para la imagen
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        scaled = self.pixmap.scaled(
            750, 500,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        scroll.setWidget(self.image_label)
        
        layout.addWidget(scroll)
        
        # Información
        info_frame = QFrame()
        info_layout = QHBoxLayout(info_frame)
        
        file_size = os.path.getsize(self.filepath) / 1024
        info_text = QLabel(f"📏 {self.pixmap.width()}×{self.pixmap.height()} px | 📦 {file_size:.1f} KB | 📁 {os.path.basename(self.filepath)}")
        info_layout.addWidget(info_text)
        
        info_layout.addStretch()
        layout.addWidget(info_frame)
        
        # Botones
        buttons = QHBoxLayout()
        
        btn_open = QPushButton("🖼️ Abrir")
        btn_open.clicked.connect(self.open_image)
        buttons.addWidget(btn_open)
        
        btn_folder = QPushButton("📁 Abrir Carpeta")
        btn_folder.clicked.connect(self.open_folder)
        buttons.addWidget(btn_folder)
        
        btn_copy = QPushButton("📋 Copiar")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        buttons.addWidget(btn_copy)
        
        btn_close = QPushButton("✅ Cerrar")
        btn_close.clicked.connect(self.accept)
        buttons.addWidget(btn_close)
        
        layout.addLayout(buttons)
    
    def apply_theme(self):
        """Aplicar tema"""
        colors = ThemeManager.get_theme_colors(self.dark_mode)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg_primary']};
                color: {colors['text_primary']};
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QFrame {{
                background-color: {colors['bg_secondary']};
                border: none;
            }}
            QPushButton {{
                background-color: {colors['accent']};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
        """)
    
    def open_image(self):
        """Abrir imagen con programa predeterminado"""
        try:
            os.startfile(self.filepath)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la imagen:\n{str(e)}")
    
    def open_folder(self):
        """Abrir carpeta contenedora"""
        try:
            os.startfile(os.path.dirname(self.filepath))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la carpeta:\n{str(e)}")
    
    def copy_to_clipboard(self):
        """Copiar imagen al portapapeles"""
        clipboard = QGuiApplication.clipboard()
        clipboard.setPixmap(self.pixmap)
        
        QMessageBox.information(
            self, "✅ Copiado",
            "📋 La imagen ha sido copiada al portapapeles."
        )


class SettingsDialog(QDialog):
    """Diálogo de configuración"""
    
    def __init__(self, config: AppConfig, parent=None, dark_mode: bool = False):
        super().__init__(parent)
        self.config = config
        self.dark_mode = dark_mode
        
        self.setWindowTitle("⚙️ Configuración - ScreenShot Capture Pro By FampThoms")
        self.setModal(True)
        self.resize(500, 600)
        
        self.setup_ui()
        self.load_config()
        self.apply_theme()
    
    def setup_ui(self):
        """Configurar interfaz"""
        layout = QVBoxLayout(self)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)
        
        # Carpeta de guardado
        folder_group = QGroupBox("📁 Carpeta de Guardado")
        folder_layout = QVBoxLayout(folder_group)
        
        folder_selector = QHBoxLayout()
        self.folder_edit = QLineEdit()
        folder_selector.addWidget(self.folder_edit)
        
        btn_browse = QPushButton("📂 Buscar")
        btn_browse.clicked.connect(self.browse_folder)
        folder_selector.addWidget(btn_browse)
        
        folder_layout.addLayout(folder_selector)
        content_layout.addWidget(folder_group)
        
        # Formato de imagen
        format_group = QGroupBox("🖼️ Formato de Imagen")
        format_layout = QGridLayout(format_group)
        
        format_layout.addWidget(QLabel("Formato:"), 0, 0)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "JPEG", "BMP"])
        format_layout.addWidget(self.format_combo, 0, 1)
        
        format_layout.addWidget(QLabel("Calidad (JPEG):"), 1, 0)
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 100)
        self.quality_slider.setTickInterval(10)
        self.quality_label = QLabel("95%")
        self.quality_slider.valueChanged.connect(lambda v: self.quality_label.setText(f"{v}%"))
        format_layout.addWidget(self.quality_slider, 1, 1)
        format_layout.addWidget(self.quality_label, 1, 2)
        
        content_layout.addWidget(format_group)
        
        # Opciones
        options_group = QGroupBox("⚙️ Opciones")
        options_layout = QVBoxLayout(options_group)
        
        self.auto_open_cb = QCheckBox("🚀 Abrir imagen automáticamente después de capturar")
        options_layout.addWidget(self.auto_open_cb)
        
        self.show_preview_cb = QCheckBox("👁️ Mostrar vista previa después de capturar")
        options_layout.addWidget(self.show_preview_cb)
        
        self.copy_clipboard_cb = QCheckBox("📋 Copiar al portapapeles automáticamente")
        options_layout.addWidget(self.copy_clipboard_cb)
        
        self.dark_mode_cb = QCheckBox("🌙 Modo oscuro")
        self.dark_mode_cb.toggled.connect(self.on_dark_mode_toggled)
        options_layout.addWidget(self.dark_mode_cb)
        
        content_layout.addWidget(options_group)
        
        # Limpieza automática
        cleanup_group = QGroupBox("🧹 Limpieza Automática")
        cleanup_layout = QGridLayout(cleanup_group)
        
        cleanup_layout.addWidget(QLabel("Mantener últimos:"), 0, 0)
        self.backup_spin = QSpinBox()
        self.backup_spin.setRange(10, 500)
        self.backup_spin.setSuffix(" archivos")
        cleanup_layout.addWidget(self.backup_spin, 0, 1)
        
        content_layout.addWidget(cleanup_group)
        
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Botones
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.Reset
        )
        buttons.accepted.connect(self.save_config)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(self.reset_config)
        
        layout.addWidget(buttons)
    
    def browse_folder(self):
        """Seleccionar carpeta de guardado"""
        folder = QFileDialog.getExistingDirectory(
            self, "Seleccionar Carpeta de Guardado",
            self.folder_edit.text() or self.config.save_folder
        )
        if folder:
            self.folder_edit.setText(folder)
    
    def load_config(self):
        """Cargar configuración actual"""
        self.folder_edit.setText(self.config.save_folder)
        self.format_combo.setCurrentText(self.config.default_format)
        self.quality_slider.setValue(self.config.quality)
        self.auto_open_cb.setChecked(self.config.auto_open)
        self.show_preview_cb.setChecked(self.config.show_preview)
        self.copy_clipboard_cb.setChecked(self.config.copy_to_clipboard)
        self.dark_mode_cb.setChecked(self.config.dark_mode)
        self.backup_spin.setValue(self.config.backup_count)
    
    def save_config(self):
        """Guardar configuración"""
        self.config.save_folder = self.folder_edit.text()
        self.config.default_format = self.format_combo.currentText()
        self.config.quality = self.quality_slider.value()
        self.config.auto_open = self.auto_open_cb.isChecked()
        self.config.show_preview = self.show_preview_cb.isChecked()
        self.config.copy_to_clipboard = self.copy_clipboard_cb.isChecked()
        self.config.dark_mode = self.dark_mode_cb.isChecked()
        self.config.backup_count = self.backup_spin.value()
        
        Path(self.config.save_folder).mkdir(parents=True, exist_ok=True)
        
        self.accept()
    
    def reset_config(self):
        """Resetear configuración por defecto"""
        self.folder_edit.setText(os.path.join(os.path.expanduser('~'), 'Documents', 'ScreenCaptures'))
        self.format_combo.setCurrentText("PNG")
        self.quality_slider.setValue(95)
        self.auto_open_cb.setChecked(False)
        self.show_preview_cb.setChecked(True)
        self.copy_clipboard_cb.setChecked(False)
        self.dark_mode_cb.setChecked(False)
        self.backup_spin.setValue(100)
    
    def on_dark_mode_toggled(self, checked: bool):
        """Cambiar modo oscuro en tiempo real"""
        self.dark_mode = checked
        self.config.dark_mode = checked
        self.apply_theme()
        # Forzar actualización completa
        self.update()
        self.repaint()
        # Actualizar el contenido del scroll area
        scroll = self.findChild(QScrollArea)
        if scroll:
            scroll.update()
            if scroll.widget():
                scroll.widget().update()
    
    def apply_theme(self):
        """Aplicar tema al diálogo"""
        colors = ThemeManager.get_theme_colors(self.dark_mode)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg_primary']};
                color: {colors['text_primary']};
            }}
            QGroupBox {{
                background-color: {colors['bg_secondary']};
                border: 2px solid {colors['border']};
                border-radius: 6px;
                margin-top: 10px;
                color: {colors['text_primary']};
            }}
            QGroupBox::title {{
                color: {colors['text_primary']};
                background-color: transparent;
            }}
            QLineEdit, QComboBox, QSpinBox {{
                background-color: {colors['bg_tertiary']};
                border: 1px solid {colors['border']};
                border-radius: 4px;
                padding: 4px;
                color: {colors['text_primary']};
            }}
            QPushButton {{
                background-color: {colors['accent']};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
            }}
            QCheckBox {{
                color: {colors['text_primary']};
                spacing: 8px;
                background-color: transparent;
            }}
            QCheckBox::indicator {{
                width: 16px;
                height: 16px;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QWidget {{
                background-color: {colors['bg_primary']};
                color: {colors['text_primary']};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {colors['border']};
                height: 6px;
                background: {colors['bg_tertiary']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {colors['accent']};
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }}
        """)
        
        # Forzar actualización del fondo del contenido
        content_widget = self.findChild(QWidget, "content_widget")
        if content_widget:
            content_widget.setStyleSheet(f"background-color: {colors['bg_primary']};")
        
        # Actualizar todos los widgets
        for widget in self.findChildren(QWidget):
            widget.update()

class ScreenShotCapturePro(QMainWindow):
    """Ventana principal de la aplicación"""
    
    def __init__(self):
        super().__init__()
        self.config = AppConfig()
        self.hotkey_manager = None
        self.tray_icon = None
        self.keyboard_running = False
        self.pynput_listener = None
        self.hook_handle = None
        self.hook_proc = None
        self.hook_thread = None
        self.check_timer = None  # Timer para verificar teclas
        self.last_print_screen_state = False
        self.last_state = False
        self.overlay = None
        
        self.setWindowTitle("📸 ScreenShot Capture Pro By FampThoms")
        self.setWindowIcon(self.create_icon())
        self.resize(400, 550)
        
        self.setup_ui()
        self.setup_tray()
        self.load_settings()
        
        # CONFIGURACIÓN DE HOTKEY
        self.setup_hotkey_corrected()
        
        self.apply_theme()
        self.update_hotkey_status()
    
    def create_icon(self) -> QIcon:
        """Crear ícono de la aplicación"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(QColor(76, 154, 255))
        
        painter = QPainter(pixmap)
        painter.setPen(QPen(Qt.GlobalColor.white, 3))
        painter.drawRect(10, 10, 44, 44)
        painter.drawLine(20, 30, 44, 30)
        painter.drawLine(32, 20, 32, 44)
        painter.end()
        
        return QIcon(pixmap)
    
    def setup_ui(self):
        """Configurar interfaz principal con scrollbars y centrado"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal con márgenes
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # ========== SCROLL AREA CON SCROLLBARS HORIZONTAL Y VERTICAL ==========
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget contenedor con tamaño adaptable
        content_widget = QWidget()
        content_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Layout principal del contenido (centrado)
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(25)
        
        # ========== CONTENEDOR CENTRAL ==========
        # Crear un widget central que centre todo el contenido
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        center_layout.setSpacing(20)
        
        # Título
        title = QLabel("📸 ScreenShot Capture Pro By FampThoms")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("""
            font-size: 24px; 
            font-weight: bold; 
            padding: 15px;
            margin: 10px;
        """)
        center_layout.addWidget(title)
        
        # Info de hotkey
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(76, 154, 255, 0.15);
                border-radius: 15px;
                padding: 20px;
                margin: 5px;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)
        info_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.hotkey_status = QLabel("🎯 Presiona 'IMPR PANT' para capturar")
        self.hotkey_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hotkey_status.setStyleSheet("font-size: 15px; font-weight: bold;")
        info_layout.addWidget(self.hotkey_status)
        
        # Lista de instrucciones
        instructions = [
            "• Arrastra para seleccionar el área deseada",
            "• Click derecho para captura de pantalla completa",
            "• ESC para cancelar la selección"
        ]
        for instr in instructions:
            lbl = QLabel(instr)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("font-size: 12px;")
            info_layout.addWidget(lbl)
        
        center_layout.addWidget(info_frame)
        
        # Estadísticas
        stats_group = QGroupBox("📊 Estadísticas")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                padding-top: 15px;
                margin-top: 5px;
            }
        """)
        stats_layout = QGridLayout(stats_group)
        stats_layout.setSpacing(15)
        stats_layout.setContentsMargins(25, 25, 25, 25)
        
        self.total_captures_label = QLabel("0")
        self.total_size_label = QLabel("0 KB")
        self.last_capture_label = QLabel("Nunca")
        
        label_style = "font-size: 13px;"
        value_style = "font-size: 14px; font-weight: bold; color: #4c9aff;"
        
        # Total capturas
        lbl_total = QLabel("📸 Total capturas:")
        lbl_total.setStyleSheet(label_style)
        stats_layout.addWidget(lbl_total, 0, 0, Qt.AlignmentFlag.AlignRight)
        self.total_captures_label.setStyleSheet(value_style)
        stats_layout.addWidget(self.total_captures_label, 0, 1, Qt.AlignmentFlag.AlignLeft)
        
        # Tamaño total
        lbl_size = QLabel("💾 Tamaño total:")
        lbl_size.setStyleSheet(label_style)
        stats_layout.addWidget(lbl_size, 1, 0, Qt.AlignmentFlag.AlignRight)
        self.total_size_label.setStyleSheet(value_style)
        stats_layout.addWidget(self.total_size_label, 1, 1, Qt.AlignmentFlag.AlignLeft)
        
        # Última captura
        lbl_last = QLabel("🕐 Última captura:")
        lbl_last.setStyleSheet(label_style)
        stats_layout.addWidget(lbl_last, 2, 0, Qt.AlignmentFlag.AlignRight)
        self.last_capture_label.setStyleSheet(value_style)
        stats_layout.addWidget(self.last_capture_label, 2, 1, Qt.AlignmentFlag.AlignLeft)
        
        center_layout.addWidget(stats_group)
        
        # Acciones rápidas
        actions_group = QGroupBox("🎮 Acciones Rápidas")
        actions_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                padding-top: 15px;
                margin-top: 5px;
            }
        """)
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(15)
        actions_layout.setContentsMargins(25, 25, 25, 25)
        actions_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Botón capturar (más grande y prominente)
        btn_capture = QPushButton("🎯 Capturar Ahora")
        btn_capture.clicked.connect(self.start_capture)
        btn_capture.setMinimumHeight(50)
        btn_capture.setStyleSheet("""
            QPushButton {
                font-size: 16px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 10px;
                min-width: 200px;
            }
        """)
        actions_layout.addWidget(btn_capture, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Botones secundarios en fila
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(15)
        buttons_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        btn_settings = QPushButton("⚙️ Configuración")
        btn_settings.clicked.connect(self.open_settings)
        btn_settings.setMinimumHeight(40)
        btn_settings.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px;")
        buttons_row.addWidget(btn_settings)
        
        btn_folder = QPushButton("📁 Abrir Carpeta")
        btn_folder.clicked.connect(self.open_capture_folder)
        btn_folder.setMinimumHeight(40)
        btn_folder.setStyleSheet("font-size: 13px; font-weight: bold; padding: 8px 16px;")
        buttons_row.addWidget(btn_folder)
        
        actions_layout.addLayout(buttons_row)
        
        center_layout.addWidget(actions_group)
        
        # Botón salir
        exit_btn = QPushButton("🚪 Salir")
        exit_btn.clicked.connect(self.quit_app)
        exit_btn.setMinimumHeight(45)
        exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                font-size: 14px;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 8px;
                min-width: 150px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        center_layout.addWidget(exit_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Agregar el centro al layout del contenido
        content_layout.addWidget(center_widget, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Agregar stretch para que el contenido no quede pegado al borde
        content_layout.addStretch()
        
        # Configurar el scroll area
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        # Barra de estado
        self.status_label = QLabel("✅ Listo - Esperando tecla IMPR PANT...")
        self.status_label.setStyleSheet("padding: 8px; font-size: 11px;")
        self.statusBar().addWidget(self.status_label)
        
        # Configurar tamaño mínimo de la ventana
        self.setMinimumSize(350, 500)
    
    def update_hotkey_status(self):
        """Actualizar el estado de los hotkeys en la UI"""
        status_text = "🎯 Presiona 'IMPR PANT' para capturar"
        
        if PYNPUT_AVAILABLE:
            status_text += " (Enjoy ✓)"
        elif KEYBOARD_AVAILABLE:
            status_text += " (keyboard ✓)"
        else:
            status_text += " ⚠️ (Usa el botón Capturar)"
        
        self.hotkey_status.setText(status_text)
    
    def setup_tray(self):
        """Configurar ícono en bandeja del sistema"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.create_icon())
        self.tray_icon.setToolTip("📸 ScreenShot Capture Pro By FampThoms")
        
        tray_menu = QMenu()
        
        capture_action = QAction("🎯 Capturar", self)
        capture_action.triggered.connect(self.start_capture)
        tray_menu.addAction(capture_action)
        
        tray_menu.addSeparator()
        
        settings_action = QAction("⚙️ Configuración", self)
        settings_action.triggered.connect(self.open_settings)
        tray_menu.addAction(settings_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("🚪 Salir", self)
        quit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.tray_icon.activated.connect(self.tray_activated)
    
    def tray_activated(self, reason):
        """Manejar clic en el ícono de la bandeja"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.start_capture()
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()
            self.raise_()
            self.activateWindow()
    
    def setup_hotkey_corrected(self):
        """Configuración de Print Screen - Prioridad a Windows API"""
        print("🔧 Configurando detección de Print Screen...")
        
        # MÉTODO 1: Usar Windows API GetAsyncKeyState
        if sys.platform == 'win32':
            try:
                import ctypes
                user32 = ctypes.windll.user32
                VK_SNAPSHOT = 0x2C  # Print Screen
                
                self.last_state = False
                self.check_count = 0
                
                def check_print_screen():
                    try:
                        # Verificar estado de Print Screen
                        state = user32.GetAsyncKeyState(VK_SNAPSHOT)
                        is_pressed = (state & 0x8000) != 0
                        
                        # Detectar transición de NO presionada a presionada
                        if is_pressed and not self.last_state:
                            self.check_count += 1
                            print(f"🎯🎯🎯 [INTENTO {self.check_count}] PRINT SCREEN DETECTADO POR Windows API! 🎯🎯🎯")
                            QTimer.singleShot(0, self.start_capture)
                        
                        self.last_state = is_pressed
                    except Exception as e:
                        print(f"Error en check: {e}")
                
                # Timer que verifica cada 30ms (más rápido = más responsivo)
                self.check_timer = QTimer()
                self.check_timer.timeout.connect(check_print_screen)
                self.check_timer.start(30)  # 30ms de intervalo
                
                self.status_label.setText("✅ Presiona IMPR PANT (Windows API)")
                print("✅ Timer de verificación Windows API iniciado (método principal)")
                return
                
            except Exception as e:
                print(f"❌ Error con Windows API: {e}")
                traceback.print_exc()
        
        # MÉTODO 2: Usar keyboard como respaldo
        if KEYBOARD_AVAILABLE:
            try:
                import keyboard
                
                def on_print_screen():
                    print("🎯🎯🎯 PRINT SCREEN DETECTADO POR KEYBOARD! 🎯🎯🎯")
                    QTimer.singleShot(0, self.start_capture)
                
                # Registrar hotkey
                keyboard.add_hotkey('print screen', on_print_screen, suppress=True)
                
                # También on_press_key
                keyboard.on_press_key('print screen', lambda _: on_print_screen())
                
                # Iniciar listener
                self.keyboard_running = True
                
                def keyboard_listener():
                    print("✅ Listener de keyboard ACTIVADO (respaldo)")
                    while self.keyboard_running:
                        try:
                            keyboard.wait(suppress=False, trigger_on_release=False)
                        except:
                            break
                        time.sleep(0.05)
                
                self.keyboard_thread = threading.Thread(target=keyboard_listener, daemon=True)
                self.keyboard_thread.start()
                
                print("✅ Hotkey keyboard configurado como respaldo")
                
            except Exception as e:
                print(f"❌ Error con keyboard: {e}")
        
        # MÉTODO 3: Usar pynput como último respaldo
        if PYNPUT_AVAILABLE:
            try:
                from pynput import keyboard as pynput_kb
                
                def on_press(key):
                    try:
                        if key == pynput_kb.Key.print_screen:
                            print("🎯🎯🎯 PRINT SCREEN DETECTADO! 🎯🎯🎯")
                            QTimer.singleShot(0, self.start_capture)
                            return False
                    except Exception as e:
                        print(f"Error en pynput: {e}")
                
                self.pynput_listener = pynput_kb.Listener(on_press=on_press)
                self.pynput_listener.daemon = True
                self.pynput_listener.start()
                print("✅ Listener pynput configurado como último respaldo")
                
            except Exception as e:
                print(f"❌ Error con pynput: {e}")
        
        if not hasattr(self, 'check_timer'):
            self.status_label.setText("⚠️ Usa el botón Capturar manualmente")
            print("❌ No se pudo configurar ningún método de detección")
    
    def keyPressEvent(self, event):
        """Manejar teclas - solo para depuración"""
        print(f"Tecla presionada en ventana: {event.key()}")
        
        if event.key() == Qt.Key.Key_Print:
            print("🎯 PRINT SCREEN detectado en keyPressEvent")
            QTimer.singleShot(0, self.start_capture)
            event.accept()
            return
        
        super().keyPressEvent(event)
    
    def start_capture(self):
        """Iniciar proceso de captura"""
        global _capture_in_progress, _last_capture_time
        
        current_time = time.time()
        if current_time - _last_capture_time < CAPTURE_COOLDOWN:
            print("⏱️ Captura ignorada (cooldown activo)")
            return
        
        if _capture_in_progress:
            print("⏱️ Captura ignorada (ya hay una en progreso)")
            return
        
        print("🔴 ========== INICIANDO PROCESO DE CAPTURA ==========")
        _capture_in_progress = True
        _last_capture_time = current_time
        
        try:
            self.status_label.setText("🎯 Iniciando captura...")
            self.hide()
            QTimer.singleShot(300, self.show_overlay)
        except Exception as e:
            print(f"❌ Error iniciando captura: {e}")
            traceback.print_exc()
            self.status_label.setText(f"❌ Error: {str(e)}")
            self.show()
            _capture_in_progress = False
    
    def show_overlay(self):
        """Mostrar overlay de selección"""
        global _capture_in_progress
        
        try:
            print("🖼️ Mostrando overlay de selección...")
            self.hide()
            QTimer.singleShot(150, self._create_overlay)
        except Exception as e:
            print(f"❌ Error mostrando overlay: {e}")
            traceback.print_exc()
            self.on_selection_cancelled()
    
    def _create_overlay(self):
        """Crear y mostrar el overlay"""
        try:
            self.overlay = SelectionOverlay()
            self.overlay.selection_completed.connect(self.on_selection_completed)
            self.overlay.cancelled.connect(self.on_selection_cancelled)
            self.overlay.show()
            print("✅ Overlay mostrado correctamente - AHORA PUEDES SELECCIONAR")
        except Exception as e:
            print(f"❌ Error creando overlay: {e}")
            traceback.print_exc()
            self.on_selection_cancelled()
    
    def on_selection_completed(self, rect: QRect):
        """Manejar selección completada"""
        global _capture_in_progress
        print(f"📐 Selección recibida: {rect.width()}x{rect.height()}")
        self.status_label.setText("📸 Capturando...")
        QTimer.singleShot(100, lambda: self.capture_area(rect))
    
    def on_selection_cancelled(self):
        """Manejar cancelación de selección"""
        global _capture_in_progress
        self.status_label.setText("❌ Captura cancelada")
        self.show()
        _capture_in_progress = False
    
    def capture_area(self, rect: QRect):
        """Capturar el área seleccionada"""
        try:
            print(f"📸 Capturando área: {rect.width()}x{rect.height()}")
            
            from PIL import ImageGrab
            
            x1 = rect.x()
            y1 = rect.y()
            x2 = rect.x() + rect.width()
            y2 = rect.y() + rect.height()
            
            x1 = max(0, x1)
            y1 = max(0, y1)
            x2 = max(x1 + 1, x2)
            y2 = max(y1 + 1, y2)
            
            print(f"📐 Coordenadas: ({x1}, {y1}) -> ({x2}, {y2})")
            
            bbox = (x1, y1, x2, y2)
            img = ImageGrab.grab(bbox=bbox, all_screens=True)
            
            if img and img.size[0] > 0 and img.size[1] > 0:
                Path(self.config.save_folder).mkdir(parents=True, exist_ok=True)
                
                now = datetime.datetime.now()
                timestamp = f"{now.strftime('%Y%m%d_%H%M%S')}{now.microsecond // 1000:03d}"
                ext = self.config.default_format.lower()
                if ext == 'jpeg':
                    ext = 'jpg'
                filename = os.path.join(
                    self.config.save_folder,
                    f"screenshot_{timestamp}.{ext}"
                )
                
                if self.config.default_format.upper() == 'PNG':
                    img.save(filename, "PNG", compress_level=1)
                elif self.config.default_format.upper() == 'JPEG':
                    img.convert("RGB").save(filename, "JPEG", quality=self.config.quality, optimize=True)
                else:
                    img.save(filename, "BMP")
                
                print(f"✅ Captura guardada: {filename}")
                
                self.cleanup_old_files()
                self.update_stats(filename, img)
                
                if self.config.copy_to_clipboard:
                    self.copy_to_clipboard(img)
                
                if self.config.show_preview:
                    QTimer.singleShot(200, lambda: self.show_preview(filename))
                elif self.config.auto_open:
                    QTimer.singleShot(200, lambda: self.open_image(filename))
                
                self.status_label.setText(f"✅ Captura guardada: {os.path.basename(filename)}")
            else:
                raise Exception("No se pudo capturar la imagen - tamaño inválido")
            
        except Exception as e:
            error_msg = f"❌ Error al capturar: {str(e)}"
            print(error_msg)
            traceback.print_exc()
            self.status_label.setText(error_msg)
            QMessageBox.critical(self, "Error de Captura", error_msg)
        finally:
            self.show()
            global _capture_in_progress
            _capture_in_progress = False
    
    def show_preview(self, filepath: str):
        """Mostrar vista previa de la captura"""
        try:
            pixmap = QPixmap(filepath)
            if not pixmap.isNull():
                dialog = PreviewDialog(pixmap, filepath, self, dark_mode=self.config.dark_mode)
                dialog.exec()
            elif self.config.auto_open:
                self.open_image(filepath)
        except Exception as e:
            print(f"Error mostrando preview: {e}")
    
    def copy_to_clipboard(self, img):
        """Copiar imagen al portapapeles"""
        try:
            from PIL.ImageQt import ImageQt
            qimage = ImageQt(img)
            pixmap = QPixmap.fromImage(qimage)
            clipboard = QGuiApplication.clipboard()
            clipboard.setPixmap(pixmap)
            print("📋 Imagen copiada al portapapeles")
        except Exception as e:
            print(f"Error copiando al portapapeles: {e}")
    
    def open_image(self, filepath: str):
        """Abrir imagen con programa predeterminado"""
        try:
            os.startfile(filepath)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la imagen:\n{str(e)}")
    
    def cleanup_old_files(self):
        """Limpiar archivos antiguos"""
        try:
            folder = Path(self.config.save_folder)
            files = list(folder.glob('screenshot_*.*'))
            files.sort(key=os.path.getmtime)
            
            if len(files) > self.config.backup_count:
                for file in files[:-self.config.backup_count]:
                    try:
                        file.unlink()
                        print(f"🗑️ Eliminado archivo antiguo: {file.name}")
                    except:
                        pass
        except Exception as e:
            print(f"Error limpiando archivos: {e}")
    
    def update_stats(self, filename: str, img):
        """Actualizar estadísticas"""
        try:
            folder = Path(self.config.save_folder)
            files = list(folder.glob('screenshot_*.*'))
            
            total_size = sum(os.path.getsize(f) for f in files) / (1024 * 1024)
            
            self.total_captures_label.setText(str(len(files)))
            self.total_size_label.setText(f"{total_size:.1f} MB")
            self.last_capture_label.setText(datetime.datetime.now().strftime('%H:%M:%S'))
            
            # ✅ usar safe_settings y guardar correctamente
            stats_settings = safe_settings("ScreenShotPro", "Stats")
            stats_settings.setValue("total_captures", len(files))
            stats_settings.setValue("total_size_mb", total_size)
            stats_settings.setValue("last_capture", datetime.datetime.now().isoformat())
        except Exception as e:
            print(f"Error actualizando stats: {e}")
    
    def load_settings(self):
        """Cargar configuración guardada"""
        try:
            settings = safe_settings("ScreenShotPro", "Settings")
            
            save_folder = settings.value("save_folder", self.config.save_folder)
            if save_folder:
                self.config.save_folder = save_folder
            
            self.config.default_format = settings.value("default_format", self.config.default_format)
            self.config.quality = int(settings.value("quality", self.config.quality))
            self.config.auto_open = settings.value("auto_open", self.config.auto_open, type=bool)
            self.config.show_preview = settings.value("show_preview", self.config.show_preview, type=bool)
            self.config.copy_to_clipboard = settings.value("copy_to_clipboard", self.config.copy_to_clipboard, type=bool)
            self.config.dark_mode = settings.value("dark_mode", self.config.dark_mode, type=bool)
            self.config.backup_count = int(settings.value("backup_count", self.config.backup_count))
            
            Path(self.config.save_folder).mkdir(parents=True, exist_ok=True)
            
            stats_settings = safe_settings("ScreenShotPro", "Stats")
            total_captures = stats_settings.value("total_captures", "0")
            self.total_captures_label.setText(str(total_captures))
            
            total_size = stats_settings.value("total_size_mb", 0)
            self.total_size_label.setText(f"{float(total_size):.1f} MB")
            
            last = stats_settings.value("last_capture", "")
            if last:
                try:
                    dt = datetime.datetime.fromisoformat(str(last))
                    self.last_capture_label.setText(dt.strftime('%H:%M:%S'))
                except:
                    self.last_capture_label.setText("Nunca")
            else:
                self.last_capture_label.setText("Nunca")

            self.apply_theme()
            self.update()
        except Exception as e:
            print(f"Error cargando settings: {e}")
    
    def save_settings(self):
        """Guardar configuración"""
        try:
            settings = safe_settings("ScreenShotPro", "Settings")
            settings.setValue("save_folder", self.config.save_folder)
            settings.setValue("default_format", self.config.default_format)
            settings.setValue("quality", self.config.quality)
            settings.setValue("auto_open", self.config.auto_open)
            settings.setValue("show_preview", self.config.show_preview)
            settings.setValue("copy_to_clipboard", self.config.copy_to_clipboard)
            settings.setValue("dark_mode", self.config.dark_mode)
            settings.setValue("backup_count", self.config.backup_count)
        except Exception as e:
            print(f"Error guardando settings: {e}")
    
    def open_settings(self):
        """Abrir diálogo de configuración"""
        dialog = SettingsDialog(self.config, self, self.config.dark_mode)
        if dialog.exec():
            self.save_settings()
            self.apply_theme()
            self.update()
            self.status_label.setText("⚙️ Configuración guardada")
    
    def open_capture_folder(self):
        """Abrir carpeta de capturas"""
        try:
            Path(self.config.save_folder).mkdir(parents=True, exist_ok=True)
            os.startfile(self.config.save_folder)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"No se pudo abrir la carpeta:\n{str(e)}")
    
    def apply_theme(self):
        """Aplicar tema a la ventana principal"""
        colors = ThemeManager.get_theme_colors(self.config.dark_mode)
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {colors['bg_primary']};
                color: {colors['text_primary']};
            }}
            QWidget {{
                background-color: {colors['bg_primary']};
                color: {colors['text_primary']};
            }}
            QMenuBar {{
                background-color: {colors['bg_secondary']};
            }}
            QMenuBar::item:selected {{
                background-color: {colors['accent']};
            }}
            QMenu {{
                background-color: {colors['bg_secondary']};
                border: 1px solid {colors['border']};
            }}
            QMenu::item:selected {{
                background-color: {colors['accent']};
            }}
            QStatusBar {{
                background-color: {colors['bg_secondary']};
                color: {colors['text_secondary']};
            }}
            QGroupBox {{
                background-color: {colors['bg_secondary']};
                border: 2px solid {colors['border']};
                border-radius: 8px;
                margin-top: 12px;
                font-weight: bold;
                font-size: 13px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: {colors['text_primary']};
                background-color: transparent;
            }}
            QPushButton {{
                background-color: {colors['accent']};
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['accent']};
            }}
            QLabel {{
                color: {colors['text_primary']};
                background-color: transparent;
            }}
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {colors['bg_secondary']};
                width: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {colors['accent']};
                border-radius: 6px;
                min-height: 20px;
            }}
            QScrollBar:horizontal {{
                background-color: {colors['bg_secondary']};
                height: 12px;
                border-radius: 6px;
            }}
            QScrollBar::handle:horizontal {{
                background-color: {colors['accent']};
                border-radius: 6px;
                min-width: 20px;
            }}
            QFrame {{
                background-color: transparent;
            }}
        """)
    
    def quit_app(self):
        """Salir de la aplicación y limpiar recursos"""
        print("🛑 Cerrando aplicación...")
        self.save_settings()
        
        if self.check_timer:
            self.check_timer.stop()
        
        self.keyboard_running = False
        
        if self.hook_handle:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                user32.UnhookWindowsHookEx(self.hook_handle)
                print("✅ Hook removido")
            except Exception as e:
                print(f"Error removiendo hook: {e}")
        
        if KEYBOARD_AVAILABLE:
            try:
                import keyboard
                keyboard.unhook_all()
            except:
                pass
        
        if hasattr(self, 'pynput_listener') and self.pynput_listener:
            try:
                self.pynput_listener.stop()
            except:
                pass
        
        if self.tray_icon:
            self.tray_icon.hide()
        
        QApplication.quit()
    
    def closeEvent(self, event):
        """Manejar cierre de ventana"""
        event.ignore()
        self.hide()
        self.tray_icon.showMessage(
            "ScreenShot Capture Pro",
            "📸 La aplicación sigue ejecutándose en la bandeja del sistema.\nPresiona IMPR PANT para capturar.",
            QSystemTrayIcon.MessageIcon.Information,
            3000
        )

def main():
    """Función principal"""
    # Verificar licencia ANTES de cualquier cosa
    check_license()

     # Verificar si ya se intentó elevar permisos
    if not is_admin():
        # Evitar bucle infinito
        if '--admin-requested' in sys.argv:
            print("❌ No se pudieron obtener permisos de administrador")
            print("Por favor, ejecuta manualmente como administrador")
            input("Presiona Enter para salir...")
            sys.exit(1)
        
        print("⚠️ ScreenShot Capture Pro necesita permisos de administrador")
        print("🔄 Solicitando elevación de permisos...")
        
        # Agregar flag para evitar bucle
        sys.argv.append('--admin-requested')
        run_as_admin()
        return
    
    # ===== VERIFICAR PERMISOS DE ADMINISTRADOR =====
    # Si NO es administrador, solicitar elevación y salir
    if not is_admin():
        print("⚠️ ScreenShot Capture Pro necesita permisos de administrador")
        print("🔄 Solicitando elevación de permisos...")
        run_as_admin()
        return  # Importante: salir de esta instancia

    # ===== SI LLEGA AQUÍ, ES ADMINISTRADOR =====
    print("✅ Ejecutando con permisos de administrador")
    
    # Configurar DPI awareness (después de tener admin)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass
    
    # Crear la aplicación
    app = QApplication(sys.argv)
    
    # ===== INICIALIZAR BOTONES ADAPTABLES =====
    process_buttons = init_adaptive_buttons(app, padding_h=20, padding_v=10)
    # ==========================================
    
    app.setApplicationName("ScreenShot Capture Pro By FampThoms")
    app.setApplicationDisplayName("📸 ScreenShot Capture Pro By FampThoms")
    app.setQuitOnLastWindowClosed(False)
    
    # Crear ventana principal
    window = ScreenShotCapturePro()
    
    # Aplicar a todos los botones de la ventana
    process_buttons(window)
    
    # Mostrar ventana
    window.show()
    
    # Mensaje de bienvenida en la consola
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║     📸 ScreenShot Capture Pro - Iniciado correctamente   ║
    ║                                                          ║
    ║     ✅ Permisos de administrador: ACTIVADOS              ║
    ║     🎯 Presiona 'IMPR PANT' para capturar                ║
    ║     🔍 Arrastra para seleccionar área                    ║
    ║     🖱️ Click derecho para pantalla completa              ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    
    # Ejecutar la aplicación
    sys.exit(app.exec())


if __name__ == "__main__":
    main()