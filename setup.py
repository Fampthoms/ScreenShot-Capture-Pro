# setup.py - Genera archivo .pyd ofuscado con Cython
import sys
import os
import shutil
import glob
import subprocess

def clean_build():
    """Limpiar archivos anteriores"""
    print("\n🧹 Limpiando archivos anteriores...")
    
    dirs_to_remove = ['build', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name, ignore_errors=True)
            print(f"   ✓ Eliminado: {dir_name}/")
    
    files_to_remove = [
        'ScreenShot_Capture_Pro.c', 
        'ScreenShot_Capture_Pro.pyd',
        'ScreenShot_Capture_Pro.so',
        'ScreenShot_Capture_Pro.html',
        '*.exp', 
        '*.lib',
        'ScreenShot_Capture_Pro.cp39-win_amd64.pyd',
        'ScreenShot_Capture_Pro.cp310-win_amd64.pyd',
        'ScreenShot_Capture_Pro.cp311-win_amd64.pyd',
    ]
    
    for pattern in files_to_remove:
        for f in glob.glob(pattern):
            try:
                if os.path.exists(f):
                    os.remove(f)
                    print(f"   ✓ Eliminado: {f}")
            except:
                pass

def install_cython():
    """Instalar Cython si no está disponible"""
    try:
        import Cython
        print(f"✅ Cython {Cython.__version__} ya está instalado")
        return True
    except ImportError:
        print("📦 Instalando Cython...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "--upgrade", "cython"])
            import Cython
            print(f"✅ Cython {Cython.__version__} instalado")
            return True
        except Exception as e:
            print(f"❌ Error instalando Cython: {e}")
            return False

def get_python_version_tag():
    """Obtener el tag de versión de Python para el .pyd"""
    import sysconfig
    import platform
    
    # Obtener información de la versión
    version = f"{sys.version_info.major}{sys.version_info.minor}"
    arch = 'amd64' if platform.machine().endswith('64') else 'win32'
    
    return f".cp{version}-{arch}.pyd"

def main():
    print("\n" + "=" * 70)
    print("🔒 OFUSCANDO ScreenShot_Capture_Pro con Cython")
    print("=" * 70)
    
    # Limpiar compilaciones anteriores
    clean_build()
    
    # Instalar Cython
    if not install_cython():
        print("❌ No se pudo instalar Cython")
        input("Presiona Enter para salir...")
        return 1
    
    # Verificar archivo fuente
    source_file = "ScreenShot_Capture_Pro.py"
    if not os.path.exists(source_file):
        print(f"❌ No se encuentra {source_file}")
        print("   Asegúrate de que el archivo existe en el directorio actual")
        input("Presiona Enter para salir...")
        return 1
    
    print(f"\n📄 Archivo fuente: {source_file}")
    print(f"📏 Tamaño: {os.path.getsize(source_file) / 1024:.1f} KB")
    
    # Importar Cython
    from Cython.Build import cythonize
    from setuptools import setup, Extension
    
    # Configuración OFUSCADA - Directivas agresivas
    compiler_directives = {
        'boundscheck': False,        # Desactivar verificación de límites
        'wraparound': False,         # Desactivar wraparound
        'initializedcheck': False,   # Desactivar verificación de inicialización
        'nonecheck': False,          # Desactivar verificación de None
        'overflowcheck': False,      # Desactivar verificación de overflow
        'embedsignature': False,     # NO incrustar firmas (más ofuscado)
        'language_level': '3',       # Python 3
        'binding': False,            # Desactivar binding dinámico
        'cdivision': True,           # División estilo C
        'profile': False,            # Desactivar profiling
        'linetrace': False,          # Desactivar linetrace
    }
    
    print("\n🔧 Directivas de ofuscación:")
    for key, value in compiler_directives.items():
        print(f"   • {key}: {value}")
    
    # Crear extensión
    extension = Extension(
        name="ScreenShot_Capture_Pro",
        sources=[source_file],
        # Opciones de compilación para máxima ofuscación
        extra_compile_args=[
            '/O2',           # Optimización máxima
            '/MT',           # Enlazado estático
            '/Gy',           # Habilitar funciones en paquetes
            '/GS-',          # Deshabilitar verificaciones de seguridad
            '/GL',           # Optimización completa del programa
        ] if sys.platform == 'win32' else [
            '-O3',           # Optimización máxima
            '-fomit-frame-pointer',
            '-fno-stack-protector',
            '-ffast-math',
        ],
    )
    
    print("\n🚀 Compilando a código C...")
    
    try:
        # Cythonizar
        ext_modules = cythonize(
            extension,
            compiler_directives=compiler_directives,
            force=True,
            verbose=True,
            annotate=False,  # No generar HTML
            nthreads=4,      # Usar múltiples núcleos
        )
        
        # Construir
        print("\n🔨 Generando archivo .pyd...")
        setup(
            name="ScreenShot_Capture_Pro",
            ext_modules=ext_modules,
            script_args=['build_ext', '--inplace', '--force'],
            zip_safe=False,
        )
        
        print("\n" + "=" * 70)
        print("✅ ¡OFUSCACIÓN COMPLETADA!")
        print("=" * 70)
        
        # Buscar el archivo .pyd generado
        pyd_files = []
        
        # Buscar en diferentes ubicaciones
        search_patterns = [
            "ScreenShot_Capture_Pro*.pyd",
            "ScreenShot_Capture_Pro*.so",
            "build/**/*.pyd",
            "build/**/*.so",
        ]
        
        for pattern in search_patterns:
            for f in glob.glob(pattern, recursive=True):
                if f not in pyd_files and os.path.exists(f):
                    pyd_files.append(f)
        
        # Mostrar resultados
        if pyd_files:
            print("\n📦 Archivos generados:")
            for f in pyd_files:
                size = os.path.getsize(f) / 1024
                print(f"\n   ✅ {f}")
                print(f"      Tamaño: {size:.1f} KB")
                
                # Si está en build/, copiarlo al directorio actual
                if 'build' in f and not os.path.exists(os.path.basename(f)):
                    try:
                        dest = os.path.basename(f)
                        shutil.copy2(f, dest)
                        print(f"      ✓ Copiado a: {dest}")
                    except Exception as e:
                        print(f"      ⚠️ No se pudo copiar: {e}")
            
            # Verificar que el archivo principal existe
            main_pyd = None
            for f in glob.glob("ScreenShot_Capture_Pro*.pyd"):
                main_pyd = f
                break
            
            if main_pyd:
                print(f"\n✨ Archivo ofuscado listo: {main_pyd}")
                print(f"\n📝 Prueba rápida:")
                print(f"   python -c \"import {main_pyd.replace('.pyd', '')}\"")
            else:
                print("\n⚠️ No se encontró el archivo .pyd en el directorio actual")
                print("   Revisa la carpeta 'build/'")
        else:
            print("\n❌ ERROR: No se generó ningún archivo .pyd")
            print("   Posibles causas:")
            print("   1. Error de compilación")
            print("   2. Faltan dependencias (Visual C++ Build Tools)")
            print("   3. Python no compatible")
            
            print("\n🔍 Diagnóstico:")
            print(f"   Python: {sys.version}")
            print(f"   Plataforma: {sys.platform}")
            
            input("\nPresiona Enter para salir...")
            return 1
        
        # Limpiar archivos intermedios (pero mantener el .pyd)
        print("\n🧹 Limpiando archivos temporales...")
        temp_files = ['ScreenShot_Capture_Pro.c', 'build', '__pycache__']
        for item in temp_files:
            if os.path.exists(item):
                try:
                    if os.path.isdir(item):
                        shutil.rmtree(item, ignore_errors=True)
                        print(f"   ✓ Eliminado: {item}/")
                    else:
                        os.remove(item)
                        print(f"   ✓ Eliminado: {item}")
                except:
                    pass
        
        print("\n" + "=" * 70)
        print("🎯 ¡TODO LISTO!")
        print("=" * 70)
        print("\nPara crear el ejecutable con PyInstaller:")
        print("   pyinstaller --onefile --windowed run_app.py")
        print("\n   O con consola visible (para depuración):")
        print("   pyinstaller --onefile run_app.py")
        print("=" * 70)
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error durante la ofuscación: {e}")
        import traceback
        traceback.print_exc()
        
        print("\n🔧 Posibles soluciones:")
        print("   1. Instala Visual C++ Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("   2. Ejecuta como administrador")
        print("   3. Verifica que no hay errores de sintaxis en ScreenShot_Capture_Pro.py")
        
        input("\nPresiona Enter para salir...")
        return 1

if __name__ == "__main__":
    sys.exit(main())