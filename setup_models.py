from pathlib import Path
import requests, zipfile
from concurrent.futures import ThreadPoolExecutor
ROOT = Path(__file__).resolve().parent

def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists(): return
    print('Downloading', path.name, flush=True)
    temp = path.with_suffix(path.suffix + '.part')
    probe = requests.get(url, headers={'Range': 'bytes=0-0'}, timeout=(20, 60))
    probe.raise_for_status()
    size = int(probe.headers['Content-Range'].split('/')[-1])
    with temp.open('wb') as f: f.truncate(size)
    block = (1 if 'github.com' in url else 8) * 1024 * 1024
    def part(start):
        end = min(start + block, size) - 1
        for attempt in range(3):
            try:
                r = requests.get(url, headers={'Range': f'bytes={start}-{end}'}, timeout=(20, 90))
                r.raise_for_status()
                if r.status_code != 206 or len(r.content) != end-start+1 or not r.headers.get('Content-Range', '').startswith(f'bytes {start}-{end}/'):
                    raise ValueError('Invalid partial download')
                with temp.open('r+b') as f:
                    f.seek(start)
                    f.write(r.content)
                return
            except Exception:
                if attempt == 2: raise
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, _ in enumerate(pool.map(part, range(0, size, block))):
            if i % 20 == 0: print(path.name, round(min((i+1)*block/size, 1)*100), '%', flush=True)
    temp.replace(path)
    print('Ready', path.name, flush=True)

def runtime():
    marker = ROOT / 'runtime' / 'llama' / '.ready'
    if marker.exists(): return
    for name in ['llama-b11435-bin-win-cuda-13.4-x64.zip', 'cudart-llama-bin-win-cuda-13.4-x64.zip']:
        path = ROOT / 'runtime' / name
        download('https://github.com/ggml-org/llama.cpp/releases/download/b11435/' + name, path)
        with zipfile.ZipFile(path) as z: z.extractall(ROOT / 'runtime' / 'llama')
    marker.touch()

def ocr_models():
    for name, tag, weight in [('craft_mlt_25k.zip', 'pre-v1.1.6', 'craft_mlt_25k.pth'), ('english_g2.zip', 'v1.3', 'english_g2.pth')]:
        path = ROOT / 'models' / 'easyocr' / name
        if (path.parent / weight).exists(): continue
        download('https://github.com/JaidedAI/EasyOCR/releases/download/' + tag + '/' + name, path)
        with zipfile.ZipFile(path) as z: z.extractall(path.parent)

if __name__ == '__main__':
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(runtime), pool.submit(download, 'https://huggingface.co/typhoon-ai/typhoon-translate1.5-4b-gguf/resolve/main/typhoon-translate1.5-4b-q4_k_m.gguf', ROOT / 'models' / 'typhoon-translate1.5-4b-q4_k_m.gguf')]
        for task in tasks: task.result()
    ocr_models()
