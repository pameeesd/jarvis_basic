#!/usr/bin/env python3
"""
JARVIS-clap: detecta DOS aplausos y lanza tu rutina personalizada.

Con dos aplausos:
  1) Dice una frase por voz (text-to-speech)
  2) Reproduce una cancion (TU propio archivo de audio)
  3) Abre los programas / paginas que elijas (a la vez)

Requisitos:
    pip install sounddevice numpy pygame pyttsx3

Notas por sistema operativo:
  - Windows: funciona tal cual. La voz usa las voces de Windows (SAPI5).
  - macOS:   la voz usa la del sistema. Da permiso de microfono a la Terminal
             en  Ajustes del Sistema > Privacidad y seguridad > Microfono.
  - Linux:   instala ademas  ->  sudo apt install espeak libportaudio2

Uso:
    python jarvis_clap.py              # arranca el asistente
    python jarvis_clap.py --calibrar   # muestra el nivel del microfono
                                        # para afinar UMBRAL_APLAUSO
"""

import os
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"   # oculta el banner de pygame

import sys
import time
import threading
import platform
import subprocess
import webbrowser

import numpy as np
import sounddevice as sd
import pyttsx3
import pygame


# ============================ CONFIGURACION ============================

# 1) CANCION: ruta a TU PROPIO archivo de audio (.mp3 o .wav).
#    Usa tu copia legal de "Should I Stay or Should I Go".
RUTA_CANCION = r"C:\Users\pamel\Desktop\JARVIS\should_i_stay_or_should_i_go.mp3"

# 2) FRASE que dira la voz al activarse.
FRASE = "Bienvenida  de nuevo, pame. Todos los sistemas están en línea"

# 3) PROGRAMAS / PAGINAS que se abriran. Cada elemento puede ser:
#      - Una URL            -> se abre en el navegador.   ej: "https://claude.ai"
#      - La ruta a un .exe  -> ej: r"C:\Program Files\App\app.exe"
#      - Un nombre de app   -> en macOS:  "Spotify"  (equivale a:  open -a Spotify)
APPS = [
    r"C:\Users\pamel\Desktop\Spotify.lnk",
    r"C:\Users\pamel\Desktop\Meta\Antigravity IDE.lnk",
    r"C:\Users\pamel\Desktop\Meta\Antigravity.lnk",
    r"C:\Users\pamel\Desktop\Meta\Codex.lnk",
]

# 4) DETECCION DE APLAUSOS (ajusta si hace falta).
UMBRAL_APLAUSO = 0.08   # 0.0–1.0  Sube si se activa solo; baja si no detecta.
GAP_MIN        = 0.10   # seg  separacion MINIMA entre los dos aplausos
GAP_MAX        = 1.00   # seg  separacion MAXIMA entre los dos aplausos
ENFRIAMIENTO   = 3.0    # seg  espera tras activarse antes de volver a escuchar

# 5) ORDEN: ¿decir la frase ANTES de la musica?
#    True  = estilo JARVIS: primero habla, luego suena la cancion.
HABLAR_PRIMERO = True

# Audio (no suele hacer falta tocarlo)
SAMPLE_RATE = 44100
BLOQUE      = 1024

# ======================================================================


# --- Inicializacion de audio ---
pygame.mixer.init()

# --- Estado interno de la deteccion ---
_estaba_fuerte   = False
_tiempos_aplauso = []
_ultimo_disparo  = 0.0
_ocupado         = False
_lock            = threading.Lock()


def lanzar_app(objetivo: str):
    """Abre una URL, un ejecutable o una app segun el sistema operativo."""
    objetivo = objetivo.strip()
    try:
        if objetivo.startswith(("http://", "https://")):
            webbrowser.open(objetivo)
            return

        sistema = platform.system()
        if sistema == "Windows":
            os.startfile(objetivo)                 # ruta a .exe o documento
        elif sistema == "Darwin":                  # macOS
            if "/" in objetivo:                    # parece una ruta
                subprocess.Popen(["open", objetivo])
            else:                                  # nombre de app
                subprocess.Popen(["open", "-a", objetivo])
        else:                                      # Linux
            try:
                subprocess.Popen([objetivo])       # binario o ruta ejecutable
            except (FileNotFoundError, OSError):
                subprocess.Popen(["xdg-open", objetivo])
    except Exception as e:
        print(f"  [!] No pude abrir '{objetivo}': {e}")


def reproducir_cancion():
    try:
        pygame.mixer.music.load(RUTA_CANCION)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"  [!] No pude reproducir la cancion: {e}")


def decir_frase():
    # Se crea un motor nuevo en cada llamada: es lo mas estable cuando
    # se invoca desde un hilo varias veces.
    try:
        motor = pyttsx3.init()
        motor.setProperty("rate", 175)   # velocidad de la voz
        # Para elegir otra voz (p. ej. una en ingles para mas estilo JARVIS):
        #   for v in motor.getProperty("voices"): print(v.id, v.name)
        #   motor.setProperty("voice", "<id de la voz que quieras>")
        motor.say(FRASE)
        motor.runAndWait()
        motor.stop()
    except Exception as e:
        print(f"  [!] Error con la voz: {e}")


def rutina_doble_aplauso():
    """Todo lo que ocurre al detectar dos aplausos."""
    global _ocupado
    print(">>> ¡Dos aplausos detectados! Activando...")

    if HABLAR_PRIMERO:
        decir_frase()
        reproducir_cancion()
    else:
        reproducir_cancion()
        decir_frase()

    # Las apps se lanzan una tras otra casi de inmediato (no bloquean),
    # asi que se abren practicamente a la vez.
    for app in APPS:
        lanzar_app(app)

    print(">>> Listo.\n")
    with _lock:
        _ocupado = False


def callback_audio(indata, frames, time_info, status):
    global _estaba_fuerte, _ultimo_disparo, _ocupado

    # Mientras suena la cancion, ignoramos el micro para que la propia
    # musica no dispare la rutina por error.
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
                # Conservar solo los aplausos recientes.
                while _tiempos_aplauso and ahora - _tiempos_aplauso[0] > GAP_MAX:
                    _tiempos_aplauso.pop(0)
                # ¿Hay dos aplausos con la separacion correcta?
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
    print("Pon UMBRAL_APLAUSO un poco por DEBAJO del pico de tus aplausos,")
    print("pero por ENCIMA del ruido normal de la sala.")
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
    print("JARVIS-clap activo. Da DOS aplausos para activar.")
    print("(Ctrl+C para salir)\n")
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