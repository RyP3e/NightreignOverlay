"""OCR. Preferência: Windows OCR nativo (WinRT) — sem modelo, sem GPU, baixo custo.
Fallback: Tesseract (se instalado). Cada instância deve viver na thread que a usa."""
import asyncio
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np


class WinOcr:
    name = "Windows OCR"

    def __init__(self, languages):
        from winrt.windows.media.ocr import OcrEngine
        from winrt.windows.globalization import Language
        from winrt.windows.graphics.imaging import SoftwareBitmap, BitmapPixelFormat
        from winrt.windows.storage.streams import DataWriter
        self._SB, self._BPF, self._DW = SoftwareBitmap, BitmapPixelFormat, DataWriter
        self.engines = []
        for tag in languages:
            try:
                e = OcrEngine.try_create_from_language(Language(tag))
                if e is not None:
                    self.engines.append((tag, e))
            except Exception:
                pass
        if not self.engines:
            e = OcrEngine.try_create_from_user_profile_languages()
            if e is not None:
                self.engines.append(("perfil", e))
        if not self.engines:
            raise RuntimeError("Nenhum idioma de OCR instalado no Windows")
        self.loop = asyncio.new_event_loop()
        self.langs = [t for t, _ in self.engines]

    def _bitmap(self, gray):
        h, w = gray.shape
        bgra = np.empty((h, w, 4), np.uint8)
        bgra[..., 0] = bgra[..., 1] = bgra[..., 2] = gray
        bgra[..., 3] = 255
        wr = self._DW()
        wr.write_bytes(bytearray(bgra.tobytes()))
        return self._SB.create_copy_from_buffer(wr.detach_buffer(), self._BPF.BGRA8, w, h)

    async def _run(self, engine, bmp):
        res = await engine.recognize_async(bmp)
        return [ln.text for ln in res.lines]

    def read(self, gray, first_only=False):
        """Retorna linhas de texto. Tenta o 1º idioma; se vier vazio, tenta os demais."""
        bmp = self._bitmap(gray)
        out = []
        for _, eng in self.engines:
            try:
                out += self.loop.run_until_complete(self._run(eng, bmp))
            except Exception:
                continue
            if first_only and out:
                break
        return out


class TesseractOcr:
    name = "Tesseract"

    def __init__(self, languages):
        exe = shutil.which("tesseract")
        if not exe:
            for p in (r"C:\Program Files\Tesseract-OCR\tesseract.exe",
                      r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"):
                if os.path.exists(p):
                    exe = p
        if not exe:
            raise RuntimeError("Tesseract não encontrado")
        self.exe = exe
        have = subprocess.run([exe, "--list-langs"], capture_output=True, text=True,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
        want = [l for l in ("por", "eng") if l in have.split()]
        self.lang = "+".join(want) or "eng"
        self.langs = [self.lang]

    def read(self, gray, first_only=False):
        from PIL import Image
        f = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        f.close()
        try:
            Image.fromarray(gray).save(f.name)
            out = subprocess.run([self.exe, f.name, "-", "--psm", "6", "-l", self.lang],
                                 capture_output=True, text=True,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
            return [l for l in out.splitlines() if l.strip()]
        finally:
            try:
                os.remove(f.name)
            except OSError:
                pass


def create(languages):
    """Retorna (engine|None, mensagem)."""
    errs = []
    for cls in (WinOcr, TesseractOcr):
        try:
            e = cls(languages)
            return e, "%s (%s)" % (e.name, ", ".join(e.langs))
        except Exception as ex:
            errs.append("%s: %s" % (cls.__name__, ex))
    return None, " | ".join(errs)
