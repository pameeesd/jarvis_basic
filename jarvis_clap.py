#!/usr/bin/env python3
"""
JARVIS-clap: detecta DOS aplausos y lanza tu rutina personalizada.

Con dos aplausos, de forma SIMULTANEA:
  - Dice una frase con voz tipo JARVIS (voz neuronal de Microsoft, via edge-tts)
  - Reproduce una cancion (TU propio archivo de audio)
  - Abre los programas / paginas que elijas

Mientras suena la cancion, pulsa ENTER para detenerla (el asistente sigue
escuchando aplausos). Pulsa Ctrl+C para cerrar el programa del todo.

Requisitos:
    py -m pip install sounddevice numpy pygame edge-tts

  - La voz tipo JARVIS (edge-tts) necesita CONEXION A INTERNET (al menos al
    arrancar, que es cuando se genera el audio de la frase).
  - Windows: da permiso de microfono si te lo pide.

Uso:
    py jarvis_clap.py              # arranca el asistente
    py jarvis_clap.py --calibrar   # muestra el nivel del microfono
"""

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"   # oculta el banner de pygame

import sys
import time
import asyncio
import threading
import platform
import subprocess
import webbrowser

import numpy as np
import sounddevice as sd
import pygame
import edge_tts


# ============================ CONFIGURACION ============================

# 1) CANCION: ruta a TU PROPIO archivo de audio (.mp3 o .wav).
#    <-- PON AQUI LA RUTA DE TU CANCION (la que ya tenias funcionando).
RUTA_CANCION = r"C:\Users\pamel\Desktop\JARVIS\should_i_stay_or_should_i_go.mp3"

# 2) FRASE que dira la voz. OJO: la voz JARVIS habla en INGLES,
#    asi que escribe la frase en ingles para que suene bien.
FRASE = "Bienvenida  de nuevo, pame. Todos los sistemas están en línea"

# 3) VOZ tipo JARVIS (voces neuronales de Microsoft):
#      en-GB-RyanNeural        -> hombre britanico (la mas estilo JARVIS)
#      en-GB-ThomasNeural      -> hombre britanico, mas serio
#      en-US-GuyNeural         -> hombre estadounidense
#      en-US-ChristopherNeural -> hombre estadounidense, voz grave
#    (Ver todas las voces:  py -m edge_tts --list-voices )
VOZ = "es-ES-AlvaroNeural"

# 4) PROGRAMAS / PAGINAS que se abriran a la vez. Cada elemento puede ser:
#      - Una URL                       -> "https://claude.ai"
#      - La ruta a un .exe             -> r"C:\...\app.exe"
#      - La ruta a un acceso directo   -> r"C:\Users\pamel\Desktop\Claude.lnk"
#      - En macOS, el nombre de la app -> "Spotify"
APPS = [
    r"C:\Users\pamel\Desktop\Spotify.lnk",
    r"C:\Users\pamel\Desktop\Meta\Antigravity IDE.lnk",
    r"C:\Users\pamel\Desktop\Meta\Antigravity.lnk",
    r"C:\Users\pamel\Desktop\Meta\Codex.lnk",
]

# 5) DETECCION DE APLAUSOS.
UMBRAL_APLAUSO = 0.08   # 0.0-1.0  Sube si se activa solo; baja si no detecta.
GAP_MIN        = 0.10   # seg  separacion MINIMA entre los dos aplausos
GAP_MAX        = 1.00   # seg  separacion MAXIMA entre los dos aplausos
ENFRIAMIENTO   = 3.0    # seg  espera tras activarse antes de volver a escuchar

# Audio (no suele hacer falta tocarlo)
SAMPLE_RATE = 44100
BLOQUE      = 1024
VOZ_ARCHIVO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "_voz_jarvis.mp3")

# ======================================================================


pygame.mixer.init()

_estaba_fuerte   = False
_tiempos_aplauso = []
_ultimo_disparo  = 0.0
_ocupado         = False
_lock            = threading.Lock()
_voz             = None   # sonido de la voz ya cargado (o None si fallo)


def preparar_voz():
    """Genera el audio de la frase con edge-tts y lo deja listo para sonar."""
    global _voz
    print("Preparando la voz (necesita internet)...")
    try:
        async def _gen():
            com = edge_tts.Communicate(FRASE, VOZ, volume="+100%")
            await com.save(VOZ_ARCHIVO)
        asyncio.run(_gen())
        _voz = pygame.mixer.Sound(VOZ_ARCHIVO)
        print("Voz lista.\n")
    except Exception as e:
        _voz = None
        print(f"  [!] No pude preparar la voz (revisa tu internet): {e}")
        print("      El resto (cancion y apps) funcionara igual.\n")


def lanzar_app(objetivo: str):
    """Abre una URL, un ejecutable, un acceso directo o una app del sistema."""
    objetivo = objetivo.strip()
    try:
        if objetivo.startswith(("http://", "https://")):
            webbrowser.open(objetivo)
            return
        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(objetivo)                 # .exe, .lnk o documento
        elif sistema == "Darwin":                  # macOS
            if "/" in objetivo:
                subprocess.Popen(["open", objetivo])
            else:
                subprocess.Popen(["open", "-a", objetivo])
        else:                                      # Linux
            try:
                subprocess.Popen([objetivo])
            except (FileNotFoundError, OSError):
                subprocess.Popen(["xdg-open", objetivo])
    except Exception as e:
        print(f"  [!] No pude abrir '{objetivo}': {e}")


def rutina_doble_aplauso():
    """Lanza voz + cancion + apps A LA VEZ (ninguna espera a la otra)."""
    global _ocupado
    print(">>> ¡Dos aplausos! Activando (Enter para parar la cancion)...")

    # Voz: suena en su propio canal y se mezcla con la cancion (no bloquea).
    if _voz is not None:
        try:
            _voz.play()
        except Exception as e:
            print(f"  [!] Error al reproducir la voz: {e}")

    # Cancion (no bloquea).
    try:
        pygame.mixer.music.load(RUTA_CANCION)
        pygame.mixer.music.set_volume(0.3)  
        pygame.mixer.music.play()
    except Exception as e:
        print(f"  [!] No pude reproducir la cancion: {e}")

    # Apps: cada una se abre al instante -> practicamente simultaneas.
    for app in APPS:
        lanzar_app(app)

    with _lock:
        _ocupado = False


def escuchar_tecla():
    """Hilo aparte: ENTER detiene la cancion; el programa sigue escuchando."""
    while True:
        try:
            input()
        except (EOFError, KeyboardInterrupt):
            return
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
            print(">>> Cancion detenida. Sigo escuchando aplausos.\n")


def callback_audio(indata, frames, time_info, status):
    global _estaba_fuerte, _ultimo_disparo, _ocupado

    # Mientras suena la cancion, ignoramos el micro (la musica haria picos).
    if pygame.mixer.music.get_busy():
        _estaba_fuerte = False
        return

    pico = float(np.abs(indata).max())
    es_fuerte = pico > UMBRAL_APLAUSO
    ahora = time.monotonic()

    # Flanco de subida (silencio -> fuerte) = inicio de un aplauso.
    if es_fuerte and not _estaba_fuerte:
        with _lock:
            if not _ocupado and (ahora - _ultimo_disparo) > ENFRIAMIENTO:
                _tiempos_aplauso.append(ahora)
                while _tiempos_aplauso and ahora - _tiempos_aplauso[0] > GAP_MAX:
                    _tiempos_aplauso.pop(0)
                if len(_tiempos_aplauso) >= 2:
                    gap = _tiempos_aplauso[-1] - _tiempos_aplauso[-2]
                    if GAP_MIN <= gap <= GAP_MAX:
                        _ultimo_disparo = ahora
                        _ocupado = True
                        _tiempos_aplauso.clear()
                        threading.Thread(target=rutina_doble_aplauso,
                                         daemon=True).start()
    _estaba_fuerte = es_fuerte


def calibrar():
    print("Modo calibracion. Aplaude y mira el 'pico'.")
    print("Pon UMBRAL_APLAUSO entre tu silencio y tus aplausos.")
    print("(Ctrl+C para salir)\n")

    def cb(indata, frames, t, status):
        pico = float(np.abs(indata).max())
        barra = "#" * int(pico * 50)
        print(f"\rpico: {pico:0.3f} |{barra:<50}|", end="")

    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                        blocksize=BLOQUE, callback=cb):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nSaliendo de calibracion.")


def main():
    preparar_voz()
    threading.Thread(target=escuchar_tecla, daemon=True).start()
    print("JARVIS-clap activo. Da DOS aplausos para activar.")
    print("Enter = parar la cancion   |   Ctrl+C = salir\n")
    with sd.InputStream(channels=1, samplerate=SAMPLE_RATE,
                        blocksize=BLOQUE, callback=callback_audio):
        try:
            while True:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\nApagando. Hasta luego.")


if __name__ == "__main__":
    if "--calibrar" in sys.argv:
        calibrar()
    else:
        main()
