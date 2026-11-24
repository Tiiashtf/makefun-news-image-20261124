#!/usr/bin/env python3
"""Draws the front page of THE WORLD TODAY for Tuesday 24 November 2026.

Pure Python 3.13 standard library: a small framebuffer, vector drawing
primitives, a hand-made 5x7 bitmap font, and a PNG encoder built on zlib.
Writes /output/entry.png (or $MAKEFUN_OUTPUT_DIR/entry.png). Deterministic:
the same bytes on every run. Clears only the CONTENTS of the output
directory, never the directory itself.
"""

import os
import struct
import sys
import zlib

W, H = 1024, 1024
PAPER = (248, 244, 233)
INK = (20, 20, 20)
RED = (158, 27, 27)
GREEN = (30, 107, 52)
GOLD = (176, 132, 30)
BLUE = (31, 78, 121)
GREY = (110, 105, 95)
LIGHT = (232, 226, 210)

# 5x7 bitmap font. Each glyph is 7 rows; each row is a 5-bit number,
# bit 4 (16) is the leftmost pixel. Only capitals, digits and punctuation:
# all copy is set in capitals, like a classic broadsheet headline face.
FONT = {
    "A": (14, 17, 17, 31, 17, 17, 17),
    "B": (30, 17, 17, 30, 17, 17, 30),
    "C": (14, 17, 16, 16, 16, 17, 14),
    "D": (30, 17, 17, 17, 17, 17, 30),
    "E": (31, 16, 16, 30, 16, 16, 31),
    "F": (31, 16, 16, 30, 16, 16, 16),
    "G": (14, 17, 16, 23, 17, 17, 15),
    "H": (17, 17, 17, 31, 17, 17, 17),
    "I": (14, 4, 4, 4, 4, 4, 14),
    "J": (7, 2, 2, 2, 2, 18, 12),
    "K": (17, 18, 20, 24, 20, 18, 17),
    "L": (16, 16, 16, 16, 16, 16, 31),
    "M": (17, 27, 21, 21, 17, 17, 17),
    "N": (17, 25, 21, 19, 17, 17, 17),
    "O": (14, 17, 17, 17, 17, 17, 14),
    "P": (30, 17, 17, 30, 16, 16, 16),
    "Q": (14, 17, 17, 17, 21, 18, 13),
    "R": (30, 17, 17, 30, 20, 18, 17),
    "S": (15, 16, 16, 14, 1, 1, 30),
    "T": (31, 4, 4, 4, 4, 4, 4),
    "U": (17, 17, 17, 17, 17, 17, 14),
    "V": (17, 17, 17, 17, 17, 10, 4),
    "W": (17, 17, 17, 21, 21, 27, 17),
    "X": (17, 17, 10, 4, 10, 17, 17),
    "Y": (17, 17, 10, 4, 4, 4, 4),
    "Z": (31, 1, 2, 4, 8, 16, 31),
    "0": (14, 17, 19, 21, 25, 17, 14),
    "1": (4, 12, 4, 4, 4, 4, 14),
    "2": (14, 17, 1, 6, 8, 16, 31),
    "3": (31, 2, 4, 2, 1, 17, 14),
    "4": (2, 6, 10, 18, 31, 2, 2),
    "5": (31, 16, 30, 1, 1, 17, 14),
    "6": (6, 8, 16, 30, 17, 17, 14),
    "7": (31, 1, 2, 4, 8, 8, 8),
    "8": (14, 17, 17, 14, 17, 17, 14),
    "9": (14, 17, 17, 15, 1, 2, 12),
    " ": (0, 0, 0, 0, 0, 0, 0),
    ".": (0, 0, 0, 0, 0, 12, 12),
    ",": (0, 0, 0, 0, 12, 4, 8),
    ":": (0, 12, 12, 0, 12, 12, 0),
    ";": (0, 12, 12, 0, 12, 4, 8),
    "'": (4, 4, 8, 0, 0, 0, 0),
    "-": (0, 0, 0, 14, 0, 0, 0),
    "\u2014": (0, 0, 0, 31, 0, 0, 0),
    "!": (4, 4, 4, 4, 4, 0, 4),
    "?": (14, 17, 1, 6, 4, 0, 4),
    "(": (2, 4, 8, 8, 8, 4, 2),
    ")": (8, 4, 2, 2, 2, 4, 8),
    "%": (25, 26, 2, 4, 8, 11, 19),
    "$": (4, 15, 20, 14, 5, 30, 4),
    "+": (0, 4, 4, 31, 4, 4, 0),
    "/": (1, 2, 2, 4, 8, 8, 16),
    "&": (12, 18, 20, 8, 21, 18, 13),
    "=": (0, 0, 31, 0, 31, 0, 0),
    '"': (10, 10, 0, 0, 0, 0, 0),
    "\u2022": (0, 0, 12, 12, 12, 0, 0),
    "*": (0, 21, 14, 31, 14, 21, 0),
    "#": (10, 10, 31, 10, 31, 10, 10),
    "@": (14, 17, 23, 21, 22, 16, 14),
    "_": (0, 0, 0, 0, 0, 0, 31),
    "[": (14, 8, 8, 8, 8, 8, 14),
    "]": (14, 2, 2, 2, 2, 2, 14),
    "\u00b0": (12, 18, 12, 0, 0, 0, 0),
}

BLANK = (0, 0, 0, 0, 0, 0, 0)


def normalise(text):
    """Uppercase the copy and fold fancy punctuation onto font glyphs."""
    return (
        text.upper()
        .replace("\u2019", "'")
        .replace("\u2018", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2013", "\u2014")
        .replace("\u2026", "...")
    )


class Page:
    """An RGB framebuffer with small vector drawing helpers."""

    def __init__(self, w=W, h=H, bg=PAPER):
        self.w, self.h = w, h
        self.px = bytearray(bg[0] for _ in range(w * h * 3))
        for i in range(w * h):
            self.px[i * 3 : i * 3 + 3] = bytes(bg)

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i : i + 3] = bytes(c)

    def rect(self, x, y, w, h, c, fill=True):
        if fill:
            for yy in range(y, y + h):
                for xx in range(x, x + w):
                    self.set(xx, yy, c)
        else:
            for xx in range(x, x + w):
                self.set(xx, y, c)
                self.set(xx, y + h - 1, c)
            for yy in range(y, y + h):
                self.set(x, yy, c)
                self.set(x + w - 1, yy, c)

    def hline(self, x, y, w, c, t=1):
        for yy in range(y, y + t):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def vline(self, x, y, h, c, t=1):
        for xx in range(x, x + t):
            for yy in range(y, y + h):
                self.set(xx, yy, c)

    def line(self, x0, y0, x1, y1, c, t=1):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            for ox in range(t):
                for oy in range(t):
                    self.set(x0 + ox, y0 + oy, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, c, fill=True):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                d2 = (xx - cx) ** 2 + (yy - cy) ** 2
                if fill:
                    if d2 <= r * r:
                        self.set(xx, yy, c)
                else:
                    if r * r - 2 * r <= d2 <= r * r:
                        self.set(xx, yy, c)

    def poly(self, pts, c):
        """Scanline-fill a polygon given as [(x, y), ...]."""
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            n = len(pts)
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                for x in range(int(xs[i]), int(xs[i + 1]) + 1):
                    self.set(x, y, c)

    def glyph(self, x, y, ch, s, c):
        rows = FONT.get(ch, BLANK)
        for r, bits in enumerate(rows):
            for col in range(5):
                if bits & (16 >> col):
                    for dy in range(s):
                        for dx in range(s):
                            self.set(x + col * s + dx, y + r * s + dy, c)

    def text(self, x, y, s, c, txt, align="left", width=None):
        """Draw text at scale s; returns the width in pixels."""
        txt = normalise(txt)
        total = len(txt) * 6 * s - s
        if align == "center" and width is not None:
            x = x + (width - total) // 2
        elif align == "right" and width is not None:
            x = x + width - total
        cx = x
        for ch in txt:
            self.glyph(cx, y, ch, s, c)
            cx += 6 * s
        return total

    def text_width(self, s, txt):
        return len(normalise(txt)) * 6 * s - s


def wrap(txt, max_chars):
    """Greedy word wrap on the normalised text; returns a list of lines."""
    words = normalise(txt).split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def para(page, x, y, w, s, c, txt, leading=None):
    """Draw a wrapped paragraph; returns the y just below the last line."""
    if leading is None:
        leading = 9 * s
    max_chars = max(1, w // (6 * s))
    for line in wrap(txt, max_chars):
        page.text(x, y, s, c, line)
        y += leading
    return y


def png_bytes(page):
    """Encode the framebuffer as a PNG (filter None on every scanline)."""
    raw = bytearray()
    stride = page.w * 3
    for y in range(page.h):
        raw.append(0)
        raw += page.px[y * stride : (y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    ihdr = struct.pack(">IIBBBBB", page.w, page.h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", comp)
        + chunk(b"IEND", b"")
    )


# ---- pictograms -----------------------------------------------------------

def draw_chip(p, x, y, s):
    """A green AI chip with gold pins, labelled NVDA."""
    p.rect(x, y, 150, 110, GREEN)
    p.rect(x + 8, y + 8, 134, 94, (38, 130, 66))
    for i in range(5):
        xx = x + 22 + i * 26
        p.rect(xx, y - 12, 10, 12, GOLD)
        p.rect(xx, y + 110, 10, 12, GOLD)
    for i in range(4):
        yy = y + 20 + i * 24
        p.rect(x - 12, yy, 12, 10, GOLD)
        p.rect(x + 150, yy, 12, 10, GOLD)
    p.text(x + 40, y + 42, 3, (255, 255, 255), "NVDA", align="left", width=150)


def draw_chart(p, x0, y0, x1, y1):
    """A steeply rising market chart with an arrowhead and a +31% badge."""
    p.line(x0, y1, x1, y1, INK, 3)
    p.line(x0, y0, x0, y1, INK, 3)
    pts = [
        (x0 + 8, y1 - 18),
        (x0 + 55, y1 - 42),
        (x0 + 100, y1 - 30),
        (x0 + 150, y1 - 78),
        (x0 + 200, y1 - 66),
        (x0 + 250, y1 - 118),
        (x0 + 300, y1 - 138),
    ]
    for a, b in zip(pts, pts[1:]):
        p.line(a[0], a[1], b[0], b[1], GREEN, 5)
    tip = pts[-1]
    p.poly(
        [(tip[0], tip[1] - 16), (tip[0] + 18, tip[1] + 2), (tip[0] - 2, tip[1] + 10)],
        GREEN,
    )
    p.text(x0 + 8, y0 + 6, 5, GREEN, "+31%")


def draw_flame(p, x, y, h):
    """A three-layer flame."""
    p.poly([(x, y + h), (x + 8, y + h // 2), (x + 22, y), (x + 36, y + h // 2),
            (x + 44, y + h)], (232, 120, 20))
    p.poly([(x + 10, y + h), (x + 16, y + h // 2 + 8), (x + 22, y + h // 3),
            (x + 28, y + h // 2 + 8), (x + 34, y + h)], (240, 200, 40))
    p.poly([(x + 17, y + h), (x + 20, y + h // 2 + 12), (x + 22, y + h // 2),
            (x + 25, y + h // 2 + 12), (x + 27, y + h)], RED)


def draw_board(p, x, y, cell=12):
    """A small 8x8 chessboard with two kings on it."""
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 == 0:
                p.rect(x + c * cell, y + r * cell, cell, cell, INK)
    p.rect(x - 3, y - 3, 8 * cell + 6, 8 * cell + 6, INK, fill=False)
    p.circle(x + 2 * cell + cell // 2, y + 6 * cell + cell // 2, 8, (255, 255, 255))
    p.rect(x + 2 * cell + cell // 2 - 1, y + 6 * cell - 4, 3, 8, (255, 255, 255))
    p.circle(x + 5 * cell + cell // 2, y + 1 * cell + cell // 2, 8, RED)
    p.rect(x + 5 * cell + cell // 2 - 1, y + 1 * cell - 4, 3, 8, RED)


# ---- page furniture -------------------------------------------------------

def panel(p, x, y, w, h):
    p.rect(x, y, w, h, INK, fill=False)
    p.rect(x, y, w, 3, INK)


def kicker(p, x, y, txt, c=RED):
    p.text(x, y, 2, c, txt)
    return y + 20


def headline(p, x, y, w, txt, s=3):
    max_chars = max(1, w // (6 * s))
    for line in wrap(txt, max_chars):
        p.text(x, y, s, INK, line)
        y += 9 * s
    return y


def deck(p, x, y, w, txt, s=2):
    return para(p, x, y, w, s, INK, txt, leading=9 * s)


def rule(p, x, y, w, t=2):
    p.hline(x, y, w, INK, t)


# ---- the front page -------------------------------------------------------

def draw_page():
    p = Page()
    p.rect(10, 10, W - 20, H - 20, INK, fill=False)
    p.rect(14, 14, W - 28, H - 28, INK, fill=False)

    # Masthead.
    p.text(28, 34, 8, INK, "THE WORLD TODAY", align="center", width=968)
    rule(p, 28, 116, 968, 3)
    p.text(28, 128, 2, INK, "TUESDAY, 24 NOVEMBER 2026")
    p.text(28, 128, 2, INK, "SOURCES: REUTERS, CNN, AP, THE TIMES, FIDE",
           align="right", width=968)
    rule(p, 28, 150, 968, 2)

    # Main story: Nvidia brings Huang back.
    y = 168
    y = kicker(p, 28, y, "TECHNOLOGY  \u2022  MARKETS")
    y += 6
    p.text(28, y, 8, INK, "HUANG IS BACK")
    y += 78
    y = para(
        p, 28, y, 656, 3, INK,
        "NVIDIA REINSTATES ITS CHIEF 11 DAYS AFTER HE QUIT. SHARES "
        "SOARED 31% AS TRUMP TOOK CREDIT.",
        leading=30,
    )
    y += 10
    draw_chip(p, 52, y + 18, 1)
    draw_chart(p, 300, y + 4, 664, y + 130)
    y += 148
    y = para(
        p, 28, y, 656, 2, GREY,
        "JENSEN HUANG, BACK AFTER 11 DAYS AWAY. THE BOARD CITED INPUT "
        "FROM SENIOR US OFFICIALS.",
        leading=18,
    )
    rule(p, 28, 560, 656, 2)

    # Right rail, top panel: COP31 aftermath.
    panel(p, 700, 168, 296, 186)
    y = kicker(p, 714, 182, "CLIMATE - ANTALYA")
    y = headline(p, 714, y, 268, "AFTER COP31: NO DEAL", s=3)
    deck(
        p, 714, y + 6, 268,
        "LONGEST CLIMATE SUMMIT EVER ENDS IN FAILURE. THE EU REJECTED A "
        "PACT WITH NO FOSSIL FUELS.",
        s=2,
    )

    # Right rail, bottom panel: war at sea.
    panel(p, 700, 370, 296, 186)
    y = kicker(p, 714, 384, "WAR AT SEA")
    y = headline(p, 714, y, 268, "KYIV CLAIMS WARSHIP SUNK OFF LIBYA", s=3)
    deck(
        p, 714, y + 6, 268,
        "UKRAINE SAYS IT SANK A RUSSIAN CORVETTE AT BENGHAZI.",
        s=2,
    )

    # Middle row, left panel: Indonesia factory fire.
    panel(p, 28, 572, 472, 214)
    y = kicker(p, 42, 586, "INDONESIA")
    y = headline(p, 42, y, 444, "24 DEAD IN CANDY FACTORY FIRE", s=3)
    draw_flame(p, 430, 660, 72)
    deck(
        p, 42, y + 4, 360,
        "BLAZE AT PT FONUSA AGUNG MULIA IN CIKANDE, BANTEN. ABOUT 30 "
        "STILL MISSING AS RESCUERS PICK THROUGH THE RUINS.",
        s=2,
    )

    # Middle row, right panel: chess championship opens.
    panel(p, 516, 572, 480, 214)
    y = kicker(p, 530, 586, "SPORT - CHESS")
    y = headline(p, 530, y, 452, "YOUNGEST TITLE MATCH BEGINS TODAY", s=3)
    draw_board(p, 884, 640, 12)
    deck(
        p, 530, y + 4, 336,
        "GUKESH, 20, DEFENDS HIS CROWN AGAINST SINDAROV, 20, IN GENEVA. "
        "GAME 1 AT 15:00 CET. 14 GAMES, $2.5M AT STAKE.",
        s=2,
    )

    # In brief.
    rule(p, 28, 802, 968, 3)
    p.text(28, 814, 3, INK, "IN BRIEF")
    rule(p, 28, 842, 968, 2)
    briefs = [
        "GAZA: OXFAM REPORT SAYS THE WAR HAS POISONED ITS AIR, SOIL AND WATER.",
        "RUSSIA HITS A HOSPITAL IN ZAPORIZHZHIA; THREE PEOPLE KILLED.",
        "TANKER INCIDENT IN THE GULF OF OMAN, UK MARITIME BODY SAYS.",
        "INDIA: MODI OPENS AN AI CENTRE AT IIT PATNA; INDIA-CHINA BORDER TALKS.",
        "WAYMO PULLS ITS DRIVERLESS TAXIS OFF ALL US FREEWAYS.",
        "SPORT: ALCARAZ WINS THE ATP FINALS; INDIA-NEW ZEALAND TEST DRAWN.",
    ]
    for i, b in enumerate(briefs):
        bx = 28 if i % 2 == 0 else 516
        by = 854 + (i // 2) * 44
        p.text(bx, by, 2, RED, "\u2022")
        para(p, bx + 16, by, 456 if i % 2 == 0 else 464, 2, INK, b, leading=18)

    # Footer.
    rule(p, 28, 984, 968, 2)
    p.text(
        28, 992, 2, GREY,
        "THE WORLD TODAY - TUESDAY 24 NOVEMBER 2026",
        align="center", width=968,
    )
    return p


def main():
    import shutil

    out = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out, exist_ok=True)
    # Clear only the CONTENTS of the output directory, never the dir itself.
    # A file we cannot remove (e.g. root-owned, in a sticky parent) is left
    # in place; the entry still lands.
    for name in os.listdir(out):
        path = os.path.join(out, name)
        try:
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)
        except OSError:
            pass
    data = png_bytes(draw_page())
    target = os.path.join(out, "entry.png")
    with open(target, "wb") as f:
        f.write(data)
    print(f"wrote {target} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
