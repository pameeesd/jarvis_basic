# ⚡ JARVIS Basic (Clap Assistant)

Un mini asistente personal en Python inspirado en JARVIS de Iron Man para empezar el día o entrar en "modo productividad" con solo **dos aplausos**. 👏✨

---

## 🚀 ¿Qué hace este proyecto?

Básicamente, no quería tener que sentarme a abrir uno por uno todos mis programas cada vez que voy a programar o estudiar. Con este script, el micrófono escucha en segundo plano y, al detectar dos aplausos seguidos, activa automáticamente toda mi rutina:

1. 🎙️ **Saludo con voz:** Me da la bienvenida con voz personalizada tipo IA (*"Bienvenida de nuevo, pame. Todos los sistemas están en línea"*).
2. 🎸 **Banda sonora:** Reproduce automáticamente una canción de fondo para entrar en el mood (por defecto, *Should I Stay or Should I Go*).
3. 💻 **Apertura de herramientas:** Lanza de golpe mis programas de trabajo esenciales (Spotify, Antigravity IDE, Codex/ChatGPT, etc.) para dejar todo listo.

---

## 📂 Archivos clave

* **`jarvis_clap.py`**: Versión principal con voz neuronal realista (usando `edge-tts`). Soporta además pulsar `Enter` para pausar la música sin cerrar el asistente.
* **`jarvis.py`**: Versión alternativa que utiliza la voz local del sistema operativo (`pyttsx3`) sin necesidad de conexión a internet.
* **`should_i_stay_or_should_i_go.mp3`**: El tema que suena de fondo al activarse (¡puedes cambiarlo por tu canción favorita!).

---

## 🛠️ Instalación y Requisitos

Necesitas tener **Python 3.10+** instalado. Luego, instala las librerías necesarias con:

```bash
pip install sounddevice numpy pygame edge-tts pyttsx3
```

> **Nota:** En Windows solo necesitas asegurarte de darle permisos al micrófono en la terminal si el sistema te lo solicita.

---

## 🎯 ¿Cómo usarlo?

### 1. Calibrar el micrófono (Recomendado la primera vez)
Para no volverte loca si el micrófono está muy sensible o no detecta bien las palmadas, corre:

```bash
python jarvis_clap.py --calibrar
```
Aplaude un par de veces y fíjate en el valor del `pico`. Puedes ajustar la variable `UMBRAL_APLAUSO` dentro del código para que quede justo por encima del ruido ambiente de tu pieza/oficina.

### 2. Arrancar JARVIS
Una vez calibrado, déjalo corriendo:

```bash
python jarvis_clap.py
```

¡Da **dos aplausos** y mira la magia! 🎩✨

* Para detener solo la música mientras sigue escuchando: presiona `ENTER`.
* Para cerrar el programa completamente: `Ctrl + C`.

---

## ⚙️ Personalización

En la sección `# CONFIGURACION` de cada script puedes cambiar fácilmente:
* **`FRASE`**: Lo que quieras que diga tu JARVIS al iniciar.
* **`VOZ`**: La voz neuronal que prefieras (en español, inglés británico tipo Paul Bettany, etc.).
* **`APPS`**: Las rutas a tus propios accesos directos (`.lnk`), ejecutables (`.exe`) o páginas web (`https://...`).
* **`RUTA_CANCION`**: La ruta al audio que más te motive.

---

Hecho con ☕ y ganas de sentirse Tony Stark por un rato.

