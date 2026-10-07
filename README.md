# Screen Translate: EasyOCR + Typhoon

Windows English-to-Thai game translator. Run **Start Translator.bat**, select a dialogue region, move the app outside that region, then start. Use Windowed/Borderless games.

## Local models
- EasyOCR 1.7.2 English on CPU (4 threads).
- typhoon-ai/typhoon-translate1.5-4b-gguf Q4_K_M (~2.5 GB).
- Portable llama.cpp b11435 CUDA 13.4 runs Typhoon on NVIDIA GPU, bound to localhost only. It exits with the app. Set TYPHOON_GPU_LAYERS=0 for slower CPU operation.

The first launch downloads the runtime and models. No API key is required. Once downloaded, OCR and translation run locally without sending text or images to a translation service. Model loading adds latency to the first translation. GPU memory is shared with the game.

The app waits 0.12 seconds plus OCR time per scan and requires two matching reads. It caches 300 translations and discards stale results. Streaming requests are closed when dialogue changes. Select short dialogue blocks; long text can exceed model limits. Actual game performance has not yet been measured.

## Setup and testing
Run `.venv/Scripts/python.exe setup_models.py` to download the runtime/model. EasyOCR downloads its models on first use.
Run `.venv/Scripts/python.exe smoke_test.py` to test synthetic OCR, real local translation, capture, selection and stale results. Model diagnostics: `typhoon-server.log`.

Sources:
- https://github.com/JaidedAI/EasyOCR
- https://huggingface.co/typhoon-ai/typhoon-translate1.5-4b
- https://huggingface.co/typhoon-ai/typhoon-translate1.5-4b-gguf
- https://github.com/ggml-org/llama.cpp

## Verified on this machine
RTX 5050 Laptop 8 GB, RAM 16 GB. Synthetic screenshot: EasyOCR 1.19 s (misread final ! as l); Typhoon cold start plus translation 13.13 s, second short sentence 0.31 s. These are individual stage timings, not end-to-end game latency. Screen capture, drag selection and stale-result tests passed. No live-game benchmark yet.
