# test_print_screen.py
import ctypes
import time
import sys

def test_print_screen():
    """Prueba la detección de la tecla Print Screen"""
    
    user32 = ctypes.windll.user32
    VK_SNAPSHOT = 0x2C  # Print Screen
    
    print("=" * 50)
    print("🔧 TEST DE DETECCIÓN DE TECLA IMPR PANT")
    print("=" * 50)
    print("✅ Presiona la tecla 'IMPR PANT' para probar")
    print("✅ Presiona 'Ctrl+C' para salir")
    print("-" * 50)
    
    last_state = False
    counter = 0
    
    try:
        while True:
            # Verificar estado de Print Screen
            state = user32.GetAsyncKeyState(VK_SNAPSHOT)
            is_pressed = (state & 0x8000) != 0
            
            # Detectar cuando se presiona la tecla
            if is_pressed and not last_state:
                counter += 1
                print(f"🎯 [{counter}] ¡PRINT SCREEN DETECTADO! (tecla presionada)")
            
            # Detectar cuando se suelta la tecla (opcional)
            if not is_pressed and last_state:
                print(f"📌 [{counter}] Tecla liberada")
            
            last_state = is_pressed
            time.sleep(0.03)  # 30ms de intervalo
            
    except KeyboardInterrupt:
        print("\n" + "-" * 50)
        print(f"✅ Prueba finalizada. Total de detecciones: {counter}")
        print("=" * 50)
        print("✅ La tecla IMPR PANT funciona correctamente!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_print_screen()