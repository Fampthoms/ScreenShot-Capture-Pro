# ==================== PARCHE ULTRA TEMPRANO ====================
import sys
import types

class FixedSixImporter(types.ModuleType):
    def __init__(self, name):
        super().__init__(name)
        self._path = []
        self.path = []
        self.__path__ = []
    
    def find_module(self, fullname, path=None):
        return None
    
    def find_spec(self, fullname, path, target=None):
        return None

sys.modules['_SixMetaPathImporter'] = FixedSixImporter('_SixMetaPathImporter')

if 'six' not in sys.modules:
    import six
if not hasattr(six, 'moves'):
    six.moves = types.ModuleType('six.moves')
    sys.modules['six.moves'] = six.moves

import os
os.environ['SHIBOKEN_DISABLE_FEATURE'] = '1'
# ================================================================

import multiprocessing
import os
import atexit
import winreg
import traceback

# ==================== PARCHE CRÍTICO MEJORADO ====================
try:
    # Crear un mock más completo para _SixMetaPathImporter
    class MockSixImporter(types.ModuleType):
        def __init__(self, name):
            super().__init__(name)
            self._path = []  # Atributo requerido
            self.path = []   # Compatibilidad
            self.__path__ = []  # Para el sistema de importación
            
        def find_module(self, fullname, path=None):
            return None
            
        def find_spec(self, fullname, path, target=None):
            return None

    if '_SixMetaPathImporter' in sys.modules:
        original = sys.modules['_SixMetaPathImporter']
        if hasattr(original, '_path'):
            mock = MockSixImporter('_SixMetaPathImporter')
            mock._path = original._path if original._path else []
            sys.modules['_SixMetaPathImporter'] = mock
    else:
        mock = MockSixImporter('_SixMetaPathImporter')
        sys.modules['_SixMetaPathImporter'] = mock
        
    print("✅ Parche para _SixMetaPathImporter aplicado")
except Exception as e:
    print(f"⚠️ Parche no aplicado: {e}")

# Deshabilitar características
os.environ['SHIBOKEN_DISABLE_FEATURE'] = '1'
os.environ['PYTHONHASHSEED'] = '0'
os.environ['QT_QUICK_BACKEND'] = 'software'  # Forzar software renderer
os.environ['QT_QPA_PLATFORM'] = 'windows'     # Forzar plataforma Windows
# ========================================================

def cleanup_resources():
    """Limpiar recursos de QSettings al desinstalar"""
    try:
        if getattr(sys, 'frozen', False):
            if '--uninstall' in sys.argv or 'uninstall' in sys.argv:
                print("🧹 Limpiando configuración para desinstalación...")
                keys_to_delete = [r"Software\ScreenShotPro"]
                for key_path in keys_to_delete:
                    try:
                        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
                        print(f"✅ Eliminada clave: {key_path}")
                    except WindowsError as e:
                        if e.winerror != 2:
                            print(f"⚠️ Error: {e}")
    except Exception as e:
        print(f"Error en cleanup: {e}")

atexit.register(cleanup_resources)

# ==================== DIAGNÓSTICO INICIAL ====================
print("=" * 60)
print("🚀 Iniciando ScreenShot Capture Pro...")
print("=" * 60)
print(f"📁 Directorio actual: {os.getcwd()}")
print(f"🐍 Python: {sys.version}")
print(f"📦 Modo empaquetado: {getattr(sys, 'frozen', False)}")
print(f"📝 Argumentos: {sys.argv}")

# Listar archivos en el directorio actual
print("\n📂 Archivos en el directorio:")
for file in os.listdir('.'):
    if file.endswith('.pyd') or file.endswith('.exe') or file == 'run_app.py':
        print(f"   • {file}")

# ==================== IMPORTACIÓN SEGURA ====================
try:
    print("\n🔍 Intentando importar módulo ofuscado...")
    
    # Verificar que el archivo .pyd existe
    import glob
    pyd_files = glob.glob("ScreenShot_Capture_Pro*.pyd")
    if pyd_files:
        print(f"✅ Encontrado .pyd: {pyd_files[0]}")
        # Cambiar el nombre si es necesario
        if pyd_files[0] != "ScreenShot_Capture_Pro.pyd":
            try:
                # Crear un enlace simbólico o copiar
                import shutil
                if not os.path.exists("ScreenShot_Capture_Pro.pyd"):
                    shutil.copy(pyd_files[0], "ScreenShot_Capture_Pro.pyd")
                    print(f"📋 Copiado a: ScreenShot_Capture_Pro.pyd")
            except:
                pass
    
    # Intentar importar
    import ScreenShot_Capture_Pro
    print("✅ Módulo ofuscado importado correctamente")
    
except ImportError as e:
    print(f"❌ Error de importación: {e}")
    print(traceback.format_exc())
    print("\n🔧 Soluciones:")
    print("   1. Asegúrate de incluir el .pyd en el --add-data de PyInstaller")
    print("   2. Copia manualmente el .pyd al directorio del .exe")
    print("   3. Usa el .spec correctamente configurado")
    
    input("\nPresiona Enter para salir...")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ Error inesperado: {e}")
    print(traceback.format_exc())
    input("\nPresiona Enter para salir...")
    sys.exit(1)

# ==================== EJECUCIÓN PRINCIPAL ====================
if __name__ == "__main__":
    multiprocessing.freeze_support()
    
    if '--uninstall' in sys.argv:
        print("🗑️ Modo desinstalación activado")
        cleanup_resources()
        sys.exit(0)
    
    print("\n🎯 Iniciando aplicación principal...")
    try:
        ScreenShot_Capture_Pro.main()
    except Exception as e:
        print(f"❌ Error en main(): {e}")
        print(traceback.format_exc())
        input("\nPresiona Enter para salir...")
        sys.exit(1)
