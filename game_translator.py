"""English to Thai screen-region translator for Windows."""
import ctypes
from ctypes import wintypes
import queue
import threading
import time
import tkinter as tk
from collections import OrderedDict
from tkinter import ttk

import mss
import numpy as np
from PIL import Image, ImageTk


from local_models import create_reader, translator


def translate(text):
    return translator.translate(text)


def read_text(engine, image):
    result = engine.readtext(image, decoder='greedy', detail=1, paragraph=False, workers=0)
    return ' '.join(t.strip() for _, t, score in result if score >= 0.5).strip()


class App:
    def __init__(self, root):
        self.root = root
        self.lock = threading.Lock()
        self.region = None
        self.running = False
        self.generation = 0
        self.revision = 0
        self.latest = ''
        self.closed = threading.Event()
        self.events = queue.Queue()
        self.jobs = queue.Queue(maxsize=1)
        root.title('Screen Translate • English → ไทย')
        root.geometry('620x560')
        root.minsize(520, 480)
        root.configure(bg='#101827')
        root.attributes('-topmost', True)
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('Segoe UI', 11), padding=9)
        frame = tk.Frame(root, bg='#101827', padx=22, pady=20)
        frame.pack(fill='both', expand=True)
        tk.Label(frame, text='SCREEN TRANSLATE', fg='#67e8c3', bg='#101827', font=('Segoe UI', 11, 'bold')).pack(anchor='w')
        tk.Label(frame, text='แปลเกม อังกฤษ → ไทย', fg='white', bg='#101827', font=('Leelawadee UI', 23, 'bold')).pack(anchor='w', pady=(4, 12))
        controls = tk.Frame(frame, bg='#101827')
        controls.pack(fill='x')
        ttk.Button(controls, text='① เลือกบริเวณ', command=self.select_region).pack(side='left', padx=(0, 8))
        self.start_button = ttk.Button(controls, text='② เริ่มแปล', command=self.toggle)
        self.start_button.pack(side='left')
        self.area_label = tk.Label(frame, text='ยังไม่ได้เลือกพื้นที่ • ลากครอบเฉพาะบทสนทนา', fg='#aabbd0', bg='#101827', anchor='w')
        self.area_label.pack(fill='x', pady=10)
        tk.Label(frame, text='ENGLISH', fg='#aabbd0', bg='#101827').pack(anchor='w')
        self.english = self.text_box(frame, 4, 12)
        tk.Label(frame, text='คำแปลภาษาไทย', fg='#67e8c3', bg='#101827', font=('Leelawadee UI', 11)).pack(anchor='w', pady=(12, 0))
        self.thai = self.text_box(frame, 5, 19)
        self.status = tk.Label(frame, text='พร้อมเลือกพื้นที่', fg='#facc75', bg='#101827', anchor='w', wraplength=560)
        self.status.pack(fill='x', pady=(12, 4))
        tk.Label(frame, text='EasyOCR + Typhoon Translate 1.5 • ทำงานบนเครื่อง\nดาวน์โหลดโมเดลครั้งแรก • ไม่ส่งข้อความไปบริการแปลออนไลน์ • ใช้เกมโหมด Borderless/Windowed', fg='#94a3b8', bg='#101827', justify='left', wraplength=570, font=('Leelawadee UI', 9)).pack(anchor='w')
        root.protocol('WM_DELETE_WINDOW', self.close)
        root.after(100, self.poll)
        threading.Thread(target=self.ocr_worker, daemon=True).start()
        threading.Thread(target=self.translation_worker, daemon=True).start()

    def text_box(self, parent, height, size):
        box = tk.Text(parent, height=height, wrap='word', bg='#1c293d', fg='white', relief='flat', padx=12, pady=10, font=('Leelawadee UI', size), state='disabled')
        box.pack(fill='both', expand=True)
        return box

    @staticmethod
    def set_text(box, value):
        box.config(state='normal')
        box.delete('1.0', 'end')
        box.insert('1.0', value)
        box.config(state='disabled')

    def toggle(self):
        if not self.region:
            self.select_region()
            return
        with self.lock:
            self.running = not self.running
            self.generation += 1
            self.latest = ''
        self.start_button.config(text='หยุดชั่วคราว' if self.running else '② เริ่มแปล')
        self.status.config(text='กำลังอ่านพื้นที่ที่เลือก…' if self.running else 'หยุดแล้ว')

    def select_region(self):
        with self.lock:
            self.running = False
            self.generation += 1
        self.start_button.config(text='② เริ่มแปล')
        self.root.withdraw()
        self.root.after(250, self.show_selector)

    def show_selector(self):
        try:
            with mss.mss() as screen:
                monitor = screen.monitors[0]
                shot = screen.grab(monitor)
                image = Image.frombytes('RGB', shot.size, shot.rgb)
            selector = tk.Toplevel(self.root)
            selector.overrideredirect(True)
            selector.attributes('-topmost', True)
            selector.geometry(f'{monitor["width"]}x{monitor["height"]}+0+0')
            canvas = tk.Canvas(selector, highlightthickness=0, cursor='crosshair')
            canvas.pack(fill='both', expand=True)
            canvas.photo = ImageTk.PhotoImage(image)
            canvas.create_image(0, 0, image=canvas.photo, anchor='nw')
            canvas.create_rectangle(15, 15, 610, 65, fill='#101827', outline='')
            canvas.create_text(30, 40, text='ลากเลือกพื้นที่บทสนทนา • ปล่อยเมาส์เพื่อยืนยัน • Esc ยกเลิก', fill='white', anchor='w', font=('Leelawadee UI', 14))
            selector.update_idletasks()
            user32 = ctypes.windll.user32
            user32.GetParent.argtypes = [wintypes.HWND]
            user32.GetParent.restype = wintypes.HWND
            user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, wintypes.UINT]
            hwnd = user32.GetParent(selector.winfo_id())
            user32.SetWindowPos(hwnd, -1, monitor['left'], monitor['top'], monitor['width'], monitor['height'], 0x0040)
            start = []
            rectangle = [None]

            def cancel(event=None):
                selector.destroy()
                self.root.deiconify()

            def down(event):
                start[:] = [event.x, event.y]
                if rectangle[0]:
                    canvas.delete(rectangle[0])
                rectangle[0] = canvas.create_rectangle(event.x, event.y, event.x, event.y, outline='#34f5b5', width=3)

            def drag(event):
                if start:
                    canvas.coords(rectangle[0], *start, event.x, event.y)

            def up(event):
                if not start:
                    return
                x1, x2 = sorted((start[0], max(0, min(event.x, monitor['width']))))
                y1, y2 = sorted((start[1], max(0, min(event.y, monitor['height']))))
                if x2 - x1 < 30 or y2 - y1 < 20:
                    return
                with self.lock:
                    self.region = dict(left=x1 + monitor['left'], top=y1 + monitor['top'], width=x2-x1, height=y2-y1)
                self.area_label.config(text=f'พื้นที่ {x2-x1} × {y2-y1} px • เลือกใหม่ได้ตลอด')
                cancel()
                self.status.config(text='เลือกพื้นที่แล้ว • ย้ายหน้าต่างนี้ออกจากพื้นที่ที่เลือก แล้วกดเริ่มแปล')

            canvas.bind('<ButtonPress-1>', down)
            canvas.bind('<B1-Motion>', drag)
            canvas.bind('<ButtonRelease-1>', up)
            selector.bind('<Escape>', cancel)
            selector.focus_force()
        except Exception as exc:
            self.root.deiconify()
            self.status.config(text=f'จับภาพไม่ได้: {exc}')

    def ocr_worker(self):
        engine = None
        previous = None
        previous_generation = -1
        with mss.mss() as screen:
            while not self.closed.wait(0.12):
                with self.lock:
                    running, region, generation = self.running, self.region, self.generation
                if not running or not region:
                    continue
                try:
                    if engine is None:
                        self.events.put(('status', generation, None, 'กำลังโหลดโมเดล OCR ครั้งแรก อาจต้องดาวน์โหลด…'))
                        engine = create_reader()
                    if generation != previous_generation:
                        previous = None
                        previous_generation = generation
                    shot = np.array(screen.grab(region))[:, :, :3].copy()
                    text = read_text(engine, shot)
                    with self.lock:
                        if generation != self.generation or not self.running:
                            continue
                        if text != self.latest:
                            self.revision += 1
                            self.latest = text
                            self.events.put(('pending', generation, self.revision, text))
                        revision = self.revision
                    if text != previous:
                        previous = text
                        continue  # Require two matching reads before sending text.
                    if not text:
                        continue
                    job = (generation, revision, text)
                    if getattr(self, '_submitted', None) == job:
                        continue
                    self._submitted = job
                    try:
                        self.jobs.get_nowait()
                    except queue.Empty:
                        pass
                    self.jobs.put_nowait(job)
                except Exception as exc:
                    self.events.put(('status', generation, None, f'OCR ผิดพลาด: {str(exc)[:180]}'))
                    self.closed.wait(2)

    def translation_worker(self):
        cache = OrderedDict()
        while not self.closed.is_set():
            try:
                generation, revision, text = self.jobs.get(timeout=0.5)
            except queue.Empty:
                continue
            with self.lock:
                if generation != self.generation or revision != self.revision or not self.running:
                    continue
            started = time.monotonic()
            try:
                if text not in cache:
                    self.events.put(('status', generation, revision, 'Typhoon กำลังแปล / โหลดโมเดลครั้งแรก…'))
                    result = translator.translate(text, cancelled=lambda: self.closed.is_set() or generation != self.generation or revision != self.revision or not self.running)
                    if result is None:
                        continue
                    cache[text] = result
                    if len(cache) > 300:
                        cache.popitem(last=False)
                self.events.put(('result', generation, revision, (cache[text], time.monotonic()-started)))
            except Exception as exc:
                self.events.put(('status', generation, revision, f'Typhoon ผิดพลาด ลองหยุดแล้วเริ่มใหม่: {str(exc)[:100]}'))

    def poll(self):
        try:
            while True:
                kind, generation, revision, payload = self.events.get_nowait()
                if generation != self.generation or (revision is not None and revision != self.revision):
                    continue
                if kind == 'pending':
                    self.set_text(self.english, payload)
                    self.set_text(self.thai, '')
                    self.status.config(text='รอข้อความนิ่งแล้วแปล…' if payload else 'รอข้อความภาษาอังกฤษในพื้นที่ที่เลือก…')
                elif kind == 'result':
                    self.set_text(self.thai, payload[0])
                    self.status.config(text=f'แปลแล้ว • ขั้นตอนแปล {payload[1]:.1f} วินาที • กำลังติดตามข้อความใหม่')
                else:
                    self.status.config(text=payload)
        except queue.Empty:
            pass
        self.root.after(100, self.poll)

    def close(self):
        self.closed.set()
        self.root.destroy()


if __name__ == '__main__':
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass
    root = tk.Tk()
    app = App(root)
    root.mainloop()
