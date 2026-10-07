import tkinter as tk
import time
import mss
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from local_models import create_reader
from game_translator import App, read_text, translate

image = Image.new('RGB', (1000, 180), 'white')
draw = ImageDraw.Draw(image)
draw.text((30, 45), 'Hello, welcome to the game!', fill='black', font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf', 42))
reader = create_reader()
started = time.monotonic()
text = read_text(reader, np.array(image)[:, :, ::-1].copy())
assert 'welcome' in text.lower(), repr(text)
print('OCR PASS:', text)
print('OCR seconds:', round(time.monotonic() - started, 2))
started = time.monotonic()
thai = translate(text)
assert any('\u0e00' <= char <= '\u0e7f' for char in thai), repr(thai)
print('TRANSLATION PASS:', ascii(thai))
print('Cold translation seconds:', round(time.monotonic() - started, 2))
started = time.monotonic()
second = translate('We must find the key before the guards return.')
assert any('\u0e00' <= c <= '\u0e7f' for c in second)
print('Warm translation seconds:', round(time.monotonic() - started, 2), ascii(second))
with mss.mss() as screen:
    shot = screen.grab(dict(left=0, top=0, width=100, height=100))
    assert shot.size.width == 100
print('CAPTURE PASS')
root = tk.Tk()
root.withdraw()
app = App(root)
root.update()
app.region = dict(left=0, top=0, width=100, height=100)
app.toggle()
old_generation = app.generation
app.toggle()
app.events.put(('result', old_generation, app.revision, ('STALE', 0)))
app.poll()
assert 'STALE' not in app.thai.get('1.0', 'end')
app.show_selector()
root.update()
selector = next(w for w in root.winfo_children() if isinstance(w, tk.Toplevel))
canvas = selector.winfo_children()[0]
canvas.event_generate('<ButtonPress-1>', x=100, y=100)
canvas.event_generate('<B1-Motion>', x=500, y=300)
canvas.event_generate('<ButtonRelease-1>', x=500, y=300)
root.update()
assert app.region['width'] == 400 and app.region['height'] == 200
print('REGION SELECTION PASS')
app.close()
print('UI AND STALE RESULT PASS')
