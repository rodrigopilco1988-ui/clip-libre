# Licencias de componentes

El código original se entrega bajo MIT. Esta lista no relicencia dependencias ni pesos. No se incluyen ejecutables ni modelos de terceros.

- **streamlit 1.67.0**: Apache-2.0.
- **faster-whisper 1.2.1**: MIT.
- **ctranslate2 4.9.0**: MIT.
- **opencv-python-headless 4.14.0.94**: Apache 2.0.
- **numpy 2.5.5**: BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0.
- **requests 2.34.2**: Apache-2.0.
- **yt-dlp 2026.10.26**: Unlicense.
- **psutil 7.2.2**: BSD-3-Clause.
- **av 19.0.2**: BSD-3-Clause.
- **onnxruntime 1.32.0**: MIT License.

## Modelos y herramientas externas

- Whisper (pesos originales) y faster-whisper: MIT. Los modelos convertidos se descargan de https://huggingface.co/Systran (revisar la ficha específica del tamaño elegido).
- Qwen3 4B: Apache 2.0 según https://huggingface.co/Qwen/Qwen3-4B. Se elige este modelo; no se recomienda Qwen2.5 3B, cuya licencia difiere de otros tamaños de Qwen2.5.
- Ollama: MIT, https://github.com/ollama/ollama/blob/main/LICENSE. Los modelos conservan su propia licencia.
- OpenCV y datos Haar de su distribución: conservar avisos incluidos en el paquete. Detección, no identificación facial.
- FFmpeg: LGPL 2.1+ en su base; las compilaciones con libx264 suelen ser GPL 2+. Algunas opciones añaden GPLv3. Se invoca como ejecutable separado, sin redistribuirlo ni enlazar su código a esta aplicación. Consulta https://ffmpeg.org/legal.html y la licencia de tu binario antes de redistribuir.
- CUDA/cuDNN son bibliotecas propietarias gratuitas del fabricante, opcionales para GPU. No son componentes abiertos ni se redistribuyen aquí. El modo CPU usa bibliotecas abiertas y funciona sin ellas. Esto es una excepción necesaria para usar la GPU NVIDIA con CTranslate2; no se presenta CUDA como software abierto.
- Voz Flite: motor con licencia permisiva, https://github.com/festvox/flite. El video de ejemplo y su texto se generaron para este proyecto y se ofrecen bajo CC0. No se distribuye el motor.

Antes de redistribuir ejecutables o modelos, conserva sus licencias y avisos completos. El ZIP de esta entrega contiene solo código, documentación y material de prueba propio.
