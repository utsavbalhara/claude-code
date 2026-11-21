"""Renders 'Got a minute?' — a split-screen BUSY SON vs PRESENT SON short (720x1280, 30fps)."""
import math, os, sys
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

FPS = 30
W, H = 720, 1280
PH = 560            # panel height
TOP_Y, BOT_Y = 80, 640
SS = 2              # supersampling
GROUND = 478
DUR = 33.6
OUT = sys.argv[1] if len(sys.argv) > 1 else "frames"

F = "/usr/share/fonts/opentype/inter/"
_fc = {}
def font(size, w="Bold"):
    k = (size, w)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(F + f"Inter-{w}.otf", max(1, int(size * SS)))
    return _fc[k]

# ---------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def seg(t, a, b): return clamp((t - a) / (b - a))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def lerp(a, b, x): return a + (b - a) * x
def pop(t, t0, dur=0.22):
    """scale curve 0 -> 1.12 -> 1 for pop-in"""
    x = seg(t, t0, t0 + dur)
    if x <= 0: return 0
    if x < 0.7: return lerp(0, 1.12, ease(x / 0.7))
    return lerp(1.12, 1.0, ease((x - 0.7) / 0.3))
def window(t, a, b, fi=0.2, fo=0.25):
    return seg(t, a, a + fi) * (1 - seg(t, b - fo, b))
def mix(c1, c2, x): return tuple(int(lerp(a, b, x)) for a, b in zip(c1, c2))

# ---------------------------------------------------------------- canvas
class Cv:
    def __init__(self, img):
        self.img = img
        self.d = ImageDraw.Draw(img, "RGBA")
    def S(self, v): return v * SS
    def rect(self, x0, y0, x1, y1, fill, r=0):
        b = [x0 * SS, y0 * SS, x1 * SS, y1 * SS]
        if r: self.d.rounded_rectangle(b, r * SS, fill=fill)
        else: self.d.rectangle(b, fill=fill)
    def circ(self, x, y, r, fill, outline=None, w=0):
        self.d.ellipse([(x - r) * SS, (y - r) * SS, (x + r) * SS, (y + r) * SS], fill=fill,
                       outline=outline, width=int(w * SS))
    def line(self, pts, fill, w):
        self.d.line([(x * SS, y * SS) for x, y in pts], fill=fill, width=int(w * SS), joint="curve")
        for x, y in (pts[0], pts[-1]):
            self.circ(x, y, w / 2, fill)
    def poly(self, pts, fill):
        self.d.polygon([(x * SS, y * SS) for x, y in pts], fill=fill)
    def text(self, x, y, s, size, fill, anchor="mm", w="Bold", stroke=0, sfill=None):
        self.d.text((x * SS, y * SS), s, font=font(size, w), fill=fill, anchor=anchor,
                    stroke_width=int(stroke * SS), stroke_fill=sfill)
    def tsize(self, s, size, w="Bold"):
        b = self.d.textbbox((0, 0), s, font=font(size, w))
        return (b[2] - b[0]) / SS, (b[3] - b[1]) / SS

def vgrad(cv, x0, y0, x1, y1, c_top, c_bot, steps=40):
    for i in range(steps):
        a, b = y0 + (y1 - y0) * i / steps, y0 + (y1 - y0) * (i + 1) / steps
        cv.rect(x0, a, x1, b + 1, mix(c_top, c_bot, i / (steps - 1)))

# ---------------------------------------------------------------- characters
ARMS = {  # (upper, fore) angles from straight-down, front arm / back arm; + = toward facing
    "down":  ((0.12, 0.05), (-0.12, -0.05)),
    "phone": ((0.35, 2.1), (-0.1, -0.05)),
    "type":  ((0.55, 1.45), (0.45, 1.4)),
    "ear":   ((0.35, 2.75), (-0.1, -0.05)),
    "hold":  ((0.45, 1.55), (0.35, 1.5)),
    "hug":   ((1.25, 1.75), (1.1, 1.7)),
    "reach": ((1.0, 1.2), (-0.1, -0.05)),
}

def figure(cv, x, gy, s=1.0, facing=1, col=(230, 230, 235), kind="man", walk=None, sit=0.0,
           arms="down", arm_mix=None, droop=0.0, bounce=0.0, hair=None, dress=None, prop=None):
    f = facing
    dark = mix(col, (0, 0, 0), 0.22)
    lw = 11 * s
    gy -= bounce * 8 * s
    hip_stand = (x, gy - 92 * s)
    hip_sit = (x, gy - 64 * s)
    hip = (lerp(hip_stand[0], hip_sit[0], sit), lerp(hip_stand[1], hip_sit[1], sit))
    lean = (6 * f * walk[1] if walk else 0) + droop * 10 * f + (6 * f if kind == "old" else 0)
    sh = (hip[0] + lean * s, hip[1] - 68 * s + droop * 6 * s)
    head = (sh[0] + (lean * 0.4 + droop * 10 * f) * s, sh[1] - 27 * s + droop * 8 * s)

    def limb(base, a1, a2, l1, l2):
        j = (base[0] + math.sin(a1) * l1 * f, base[1] + math.cos(a1) * l1)
        e = (j[0] + math.sin(a2) * l2 * f, j[1] + math.cos(a2) * l2)
        return [base, j, e]

    # legs
    legs = []
    for side in (1, -1):
        if walk:
            ph, amt = walk
            a = math.sin(ph + (0 if side == 1 else math.pi)) * 0.5 * amt
            st = limb(hip, a, a - max(0, -math.sin(ph + (0 if side == 1 else math.pi))) * 0.5 * amt, 47 * s, 45 * s)
        else:
            st = limb(hip, 0.07 * side, 0.03 * side, 47 * s, 45 * s)
        knee_s = (hip_sit[0] + 44 * s * f + side * 2 * s, hip[1])
        si = [hip, knee_s, (knee_s[0], gy)]
        legs.append([(lerp(p[0], q[0], sit), lerp(p[1], q[1], sit)) for p, q in zip(st, si)])
    # arms
    def arm_pts(preset, idx):
        a1, a2 = ARMS[preset][idx]
        if walk and preset == "down":
            ph, amt = walk
            sw = math.sin(ph + (math.pi if idx == 0 else 0)) * 0.45 * amt
            a1, a2 = sw, sw + 0.2
        return limb(sh, a1, a2, 36 * s, 34 * s)
    arm_list = []
    for idx in (0, 1):
        p = arm_pts(arms, idx)
        if arm_mix:
            other, m = arm_mix
            q = arm_pts(other, idx)
            p = [(lerp(a[0], b[0], m), lerp(a[1], b[1], m)) for a, b in zip(p, q)]
        arm_list.append(p)

    # back limbs
    cv.line(legs[1], dark, lw)
    cv.line(arm_list[1], dark, lw * 0.9)
    if kind in ("mom", "old"):
        dc = dress or (120, 90, 150)
        cv.poly([(sh[0] - 13 * s, sh[1]), (sh[0] + 13 * s, sh[1]),
                 (hip[0] + 26 * s + sit * 20 * s * f, hip[1] + 30 * s - sit * 20 * s),
                 (hip[0] - 26 * s + sit * 20 * s * f, hip[1] + 30 * s - sit * 20 * s)], dc)
        cv.line([sh, hip], dc, 24 * s)
    else:
        cv.line([sh, hip], col, 22 * s)
    cv.line(legs[0], col, lw)
    if kind in ("mom", "old"):
        cv.poly([(sh[0] - 13 * s, sh[1] + 4 * s), (sh[0] + 13 * s, sh[1] + 4 * s),
                 (hip[0] + 24 * s + sit * 22 * s * f, hip[1] + 28 * s - sit * 20 * s),
                 (hip[0] - 24 * s + sit * 22 * s * f, hip[1] + 28 * s - sit * 20 * s)], dress)
    # head
    hr = 19 * s
    if hair and kind in ("mom", "old"):
        cv.circ(head[0] - 15 * s * f, head[1] - 8 * s, 10 * s, hair)
    cv.circ(head[0], head[1], hr, col)
    if hair:
        cv.d.pieslice([(head[0] - hr - 1) * SS, (head[1] - hr - 1) * SS, (head[0] + hr + 1) * SS, (head[1] + hr + 1) * SS],
                      180 + (20 if f == 1 else -20), 360 + (20 if f == 1 else -20), fill=hair)
    if kind == "kid":
        cv.d.pieslice([(head[0] - hr - 1) * SS, (head[1] - hr - 2) * SS, (head[0] + hr + 1) * SS, (head[1] + hr) * SS],
                      180, 360, fill=(200, 70, 60))
        bx = head[0] if f == 1 else head[0] - 22 * s
        cv.rect(bx, head[1] - 4 * s, bx + 22 * s, head[1], (200, 70, 60))
    cv.line(arm_list[0], col, lw * 0.9)
    hand = arm_list[0][-1]
    if prop == "phone":
        cv.rect(hand[0] - 5 * s, hand[1] - 9 * s, hand[0] + 5 * s, hand[1] + 7 * s, (35, 38, 50), r=2 * s)
        cv.rect(hand[0] - 3.5 * s, hand[1] - 7.5 * s, hand[0] + 3.5 * s, hand[1] + 4 * s, (140, 190, 255), r=1 * s)
    if kind == "old":
        cv.line([(hand[0] + 4 * s * f, hand[1]), (hand[0] + 10 * s * f, gy)], (110, 80, 60), 4 * s)
    return hand, head

def glowing(panel, draw_fn, color=(255, 205, 90), radius=14, strength=1.0):
    """draw a figure on its own layer and add a soft halo behind it"""
    layer = Image.new("RGBA", panel.size, (0, 0, 0, 0))
    ret = draw_fn(Cv(layer))
    a = layer.split()[3]
    halo = Image.new("RGBA", panel.size, color + (0,))
    halo.putalpha(a.point(lambda v: int(v * 0.75 * strength)))
    halo = halo.filter(ImageFilter.GaussianBlur(radius * SS))
    panel.paste(halo, (0, 0), halo)
    edge = layer.filter(ImageFilter.MaxFilter(3))
    rim = Image.new("RGBA", panel.size, (255, 236, 170, 0))
    rim.putalpha(edge.split()[3].point(lambda v: int(v * 0.7 * strength)))
    panel.paste(rim, (0, 0), rim)
    panel.paste(layer, (0, 0), layer)
    return ret

# ---------------------------------------------------------------- UI elements
def bubble(img, x, y, text, sc, dark=True, size=17, tail=-1, italic=False):
    """speech bubble with its tail tip at (x, y)"""
    if sc <= 0.01: return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    c = Cv(lay)
    tw, th = c.tsize(text, size)
    bw, bh = tw + 30, 38
    cx, cy = x + tail * -1 * 0, y - 14 - bh / 2
    fill = (28, 30, 38, 240) if dark else (250, 248, 242, 245)
    tc = (255, 255, 255) if dark else (30, 30, 36)
    bx0 = min(max(cx - bw / 2, 10), W - 10 - bw)
    c.rect(bx0 - 2, cy - bh / 2 - 2, bx0 + bw + 2, cy + bh / 2 + 2, (255, 255, 255, 70) if dark else (0, 0, 0, 40), r=20)
    c.rect(bx0, cy - bh / 2, bx0 + bw, cy + bh / 2, fill, r=19)
    c.poly([(x - 7, cy + bh / 2 - 1), (x + 7, cy + bh / 2 - 1), (x, y)], fill)
    c.text(bx0 + bw / 2, cy + 1, text, size, tc, w="BoldItalic" if italic else "Bold")
    if sc != 1:
        lay = lay.resize((int(lay.width * sc), int(lay.height * sc)), Image.BILINEAR)
        ox, oy = int(x * SS * (1 - sc)), int(y * SS * (1 - sc))
        tmp = Image.new("RGBA", img.size, (0, 0, 0, 0))
        tmp.paste(lay, (ox, oy))
        lay = tmp
    img.paste(lay, (0, 0), lay)

def card(img, t, t0, t1, who, msg, x=None, y=60, accent=(80, 140, 255), sub=None, msg_col=(25, 25, 30),
         buttons=False, tag=None, progress=None):
    """phone-notification card that slides down in at t0 and fades at t1"""
    a = window(t, t0, t1, 0.25, 0.3)
    if a <= 0: return
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    c = Cv(lay)
    cw = 300
    ch = 92 if (buttons or progress is not None) else 74
    x = x if x is not None else W - cw - 26
    yy = y - (1 - ease(seg(t, t0, t0 + 0.3))) * 30
    c.rect(x + 3, yy + 5, x + cw + 3, yy + ch + 5, (0, 0, 0, 70), r=16)
    c.rect(x, yy, x + cw, yy + ch, (250, 250, 252), r=16)
    c.circ(x + 22, yy + 20, 9, accent)
    c.text(x + 38, yy + 20, who, 13, (110, 110, 120), anchor="lm", w="SemiBold")
    if tag:
        c.text(x + cw - 16, yy + 20, tag, 12, (150, 150, 160), anchor="rm", w="SemiBold")
    c.text(x + 18, yy + 48, msg, 17, msg_col, anchor="lm")
    if sub:
        c.text(x + cw - 16, yy + ch - 14, sub, 12, (60, 120, 230), anchor="rm", w="SemiBold")
    if buttons:
        c.circ(x + cw - 64, yy + 70, 11, (230, 70, 70))
        c.circ(x + cw - 30, yy + 70, 11, (60, 190, 100))
    if progress is not None:
        c.rect(x + 18, yy + 70, x + cw - 18, yy + 74, (220, 220, 228), r=2)
        c.rect(x + 18, yy + 70, x + 18 + (cw - 36) * progress, yy + 74, accent, r=2)
    if a < 1:
        al = lay.split()[3].point(lambda v: int(v * a))
        lay.putalpha(al)
    img.paste(lay, (0, 0), lay)

def sfx(img, x, y, text, t, t0, t1, size=20, rot=-10, shake=0.0, col=(255, 255, 255)):
    a = window(t, t0, t1, 0.08, 0.25)
    if a <= 0: return
    lay = Image.new("RGBA", (400 * SS, 120 * SS), (0, 0, 0, 0))
    c = Cv(lay)
    sc = pop(t, t0, 0.15) or 0.01
    c.text(200, 60, text, size * max(sc, 0.3), col + (int(255 * a),), stroke=2.5, sfill=(20, 20, 26, int(255 * a)), w="ExtraBold")
    lay = lay.rotate(rot, resample=Image.BICUBIC)
    dx = math.sin(t * 90) * shake
    img.paste(lay, (int((x - 200 + dx) * SS), int((y - 60) * SS)), lay)

def float_ha(img, x, y, t, t0, n=3, txt="ha"):
    for i in range(n):
        s = t0 + i * 0.35
        u = seg(t, s, s + 1.1)
        if 0 < u < 1:
            sfx(img, x + (i % 2) * 22 - 8, y - u * 40, txt, t, s, s + 1.1, size=15, rot=8 if i % 2 else -8)

def heart(c, x, y, r, col):
    c.circ(x - r * 0.5, y, r * 0.55, col)
    c.circ(x + r * 0.5, y, r * 0.55, col)
    c.poly([(x - r * 1.02, y + r * 0.15), (x + r * 1.02, y + r * 0.15), (x, y + r * 1.25)], col)

def hearts(img, x, y, t, t0, n=3):
    lay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    c = Cv(lay)
    for i in range(n):
        s = t0 + i * 0.4
        u = seg(t, s, s + 1.5)
        if 0 < u < 1:
            a = int(255 * min(1, (1 - u) * 2))
            heart(c, x + math.sin(u * 6 + i) * 10 + (i - 1) * 18, y - u * 60, 7 + 2 * pop(t, s, 0.2), (240, 90, 110, a))
    img.paste(lay, (0, 0), lay)

# ---------------------------------------------------------------- backgrounds
def bg_kitchen(c, warm=True, empty=False, dim=0.0):
    if warm:
        wall_t, wall_b, floor = (92, 64, 70), (150, 100, 84), (88, 58, 46)
        sky_t, sky_b = (60, 50, 110), (236, 140, 90)
    else:
        wall_t, wall_b, floor = (40, 46, 60), (56, 62, 78), (34, 36, 44)
        sky_t, sky_b = (14, 18, 34), (40, 46, 74)
    vgrad(c, 0, 0, W, GROUND, wall_t, wall_b)
    c.rect(0, GROUND, W, PH, floor)
    c.rect(0, GROUND, W, GROUND + 4, mix(floor, (0, 0, 0), 0.3))
    # window
    vgrad(c, 470, 110, 640, 290, sky_t, sky_b, 20)
    c.rect(470, 110, 640, 116, (60, 40, 40) if warm else (28, 30, 40))
    c.rect(552, 110, 558, 290, (60, 40, 40) if warm else (28, 30, 40))
    c.rect(462, 286, 648, 296, (70, 48, 44) if warm else (30, 32, 42))
    # framed photo on wall
    c.rect(330, 150, 400, 220, (60, 44, 40) if warm else (36, 38, 48))
    c.rect(336, 156, 394, 214, (220, 190, 150) if warm else (80, 84, 96))
    c.circ(355, 182, 8, (120, 90, 80) if warm else (60, 62, 72))
    c.circ(375, 186, 6, (120, 90, 80) if warm else (60, 62, 72))
    # lamp
    c.line([(270, 0), (270, 120)], (30, 30, 34), 2)
    c.d.pieslice([238 * SS, 105 * SS, 302 * SS, 160 * SS], 180, 360, fill=(230, 180, 90) if warm else (70, 74, 86))
    if warm or not empty:
        al = int((70 if warm else 22) * (1 - dim))
        c.poly([(245, 132), (295, 132), (420, GROUND), (120, GROUND)], (255, 210, 140, al))
    # table + chairs
    tc = (110, 70, 50) if warm else (54, 56, 66)
    c.rect(170, 372, 400, 384, tc, r=3)
    c.rect(185, 384, 195, GROUND, mix(tc, (0, 0, 0), 0.25))
    c.rect(375, 384, 385, GROUND, mix(tc, (0, 0, 0), 0.25))
    if warm:
        c.circ(250, 365, 12, (240, 240, 235)); c.circ(325, 365, 12, (240, 240, 235))
        c.rect(282, 346, 292, 372, (200, 80, 70), r=3)
    else:
        c.rect(300, 360, 318, 372, (70, 72, 84), r=2)  # a single cup
    for cx_, flip in ((130, 1), (440, -1)):
        cc = mix(tc, (0, 0, 0), 0.1)
        c.rect(cx_ - 22, 412, cx_ + 22, 420, cc, r=2)
        c.rect(cx_ - 20, 420, cx_ - 14, GROUND, cc)
        c.rect(cx_ + 14, 420, cx_ + 20, GROUND, cc)
        bx = cx_ - 22 if flip == 1 else cx_ + 16
        c.rect(bx, 330, bx + 6, 420, cc)

def bg_apartment(c):
    vgrad(c, 0, 0, W, GROUND, (24, 30, 58), (40, 48, 84))
    c.rect(0, GROUND, W, PH, (26, 28, 44))
    vgrad(c, 60, 90, 300, 280, (8, 10, 24), (24, 30, 60), 16)
    for i in range(26):
        bx = 70 + (i * 37) % 220; by = 180 + (i * 53) % 90
        c.rect(bx, by, bx + 16, 280, (16, 20, 40))
        if i % 3 == 0: c.rect(bx + 4, by + 8, bx + 8, by + 12, (250, 210, 120))
    c.circ(250, 125, 14, (235, 235, 210))
    c.circ(256, 120, 13, (12, 14, 30))
    c.rect(56, 86, 304, 92, (14, 16, 30)); c.rect(56, 280, 304, 288, (14, 16, 30))
    c.circ(640, 240, 22, (200, 200, 210)); c.circ(640, 240, 18, (40, 44, 70))
    c.line([(640, 240), (640, 228)], (200, 200, 210), 2); c.line([(640, 240), (649, 240)], (200, 200, 210), 2)
    # desk
    c.rect(400, 380, 620, 390, (60, 54, 70))
    c.rect(410, 390, 418, GROUND, (44, 40, 54)); c.rect(602, 390, 610, GROUND, (44, 40, 54))
    c.poly([(440, 378), (520, 378), (510, 334), (450, 334)], (180, 184, 196))
    c.poly([(446, 376), (514, 376), (506, 338), (454, 338)], (130, 180, 255))
    c.poly([(450, 380), (380, GROUND + 60), (650, GROUND + 60), (530, 380)], (140, 190, 255, 28))
    # chair
    c.rect(338, 412, 384, 420, (30, 32, 46)); c.rect(356, 420, 364, GROUND, (30, 32, 46))
    c.rect(332, 340, 340, 420, (30, 32, 46))

def bg_balcony(c, t):
    vgrad(c, 0, 0, W, 300, (90, 80, 150), (250, 160, 100), 50)
    c.circ(470, 300, 60, (255, 220, 150, 120)); c.circ(470, 300, 42, (255, 230, 170))
    vgrad(c, 0, 300, W, GROUND, (210, 130, 110), (120, 80, 110), 30)
    for i in range(7):
        yy = 320 + i * 22
        xo = (t * 12 + i * 70) % 200
        c.rect(380 + xo - 100, yy, 470 + xo - 90, yy + 3, (255, 220, 170, 110))
    for hx, hr in ((60, 30), (110, 22), (640, 34), (690, 24)):
        c.circ(hx, 300, hr, (110, 80, 120))
    c.rect(0, GROUND, W, PH, (90, 120, 80))
    c.rect(0, 420, W, 426, (60, 50, 60))
    for i in range(0, W, 26):
        c.rect(i, 426, i + 4, GROUND, (60, 50, 60))
    c.rect(150, 210, 156, GROUND, (40, 36, 46))
    c.circ(153, 205, 12, (255, 230, 170)); c.circ(153, 205, 28, (255, 230, 170, 60))

def bg_office(c, t):
    vgrad(c, 0, 0, W, GROUND, (30, 34, 44), (46, 52, 64))
    c.rect(0, GROUND, W, PH, (28, 30, 36))
    vgrad(c, 380, 70, 680, 300, (10, 12, 26), (20, 26, 48), 16)
    for i in range(18):
        bx = 390 + (i * 41) % 280; by = 170 + (i * 29) % 100
        c.rect(bx, by, bx + 22, 300, (18, 22, 38))
        for k in range(3):
            if (i + k) % 2: c.rect(bx + 4, by + 10 + k * 18, bx + 9, by + 14 + k * 18, (230, 200, 120))
    for xx in (378, 528, 678):
        c.rect(xx, 70, xx + 4, 300, (16, 18, 26))
    # desk + monitor + papers
    c.rect(150, 380, 420, 390, (70, 74, 86))
    c.rect(160, 390, 168, GROUND, (50, 52, 62)); c.rect(402, 390, 410, GROUND, (50, 52, 62))
    c.rect(300, 290, 400, 360, (40, 42, 52), r=4); c.rect(305, 295, 395, 355, (120, 160, 230))
    for k in range(4):
        c.rect(312, 304 + k * 12, 312 + 60 + (k * 13) % 20, 308 + k * 12, (210, 225, 255))
    c.rect(345, 360, 355, 380, (40, 42, 52))
    for k in range(4):
        c.rect(200 + k * 3, 368 - k * 4, 250 + k * 3, 372 - k * 4, (220, 220, 210))
    c.circ(270, 368, 8, (180, 120, 80))
    c.poly([(305, 330), (200, GROUND + 60), (480, GROUND + 60), (395, 330)], (140, 180, 255, 20))
    c.rect(198, 412, 244, 420, (30, 32, 40)); c.rect(218, 420, 226, GROUND, (30, 32, 40))
    c.rect(192, 340, 200, 420, (30, 32, 40))

def bg_porch(c, t):
    vgrad(c, 0, 0, W, GROUND, (150, 96, 70), (214, 150, 100))
    c.rect(0, GROUND, W, PH, (110, 70, 52))
    c.rect(80, 150, 200, GROUND, (90, 50, 40), r=4)
    c.rect(90, 160, 190, GROUND, (120, 70, 50), r=2)
    c.circ(178, 330, 5, (240, 200, 120))
    c.circ(240, 200, 10, (255, 230, 160)); c.circ(240, 200, 40, (255, 220, 150, 50))
    for k, col in enumerate([(230, 90, 90), (240, 200, 90), (120, 170, 220)]):
        x0 = 520 + k * 40
        c.line([(x0, 0), (x0 + 20, 60)], (80, 50, 40), 2)
        c.poly([(x0 + 10, 60), (x0 + 30, 60), (x0 + 20, 82)], col)
    c.rect(560, 380, 600, GROUND, (90, 60, 48), r=6)
    c.circ(580, 362, 26, (90, 150, 80)); c.circ(566, 350, 18, (110, 170, 90))

def cake(c, x, y, t):
    c.rect(x - 26, y - 4, x + 26, y + 18, (250, 230, 230), r=4)
    c.rect(x - 26, y - 4, x + 26, y + 3, (230, 120, 140), r=3)
    for k in (-12, 0, 12):
        c.rect(x + k - 1.5, y - 16, x + k + 1.5, y - 4, (120, 180, 240))
        fl = 4 + math.sin(t * 25 + k) * 1.2
        c.circ(x + k, y - 20, fl, (255, 200, 80))
        c.circ(x + k, y - 20, fl * 3, (255, 200, 80, 40))

# ---------------------------------------------------------------- panel post FX
def finish(panel_rgba, cold, scene_t, scene_len, zoom=0.035):
    img = panel_rgba.convert("RGB")
    if cold:
        g = ImageEnhance.Color(img).enhance(0.55)
        img = Image.blend(g, Image.new("RGB", img.size, (30, 40, 70)), 0.12)
        img = ImageEnhance.Brightness(img).enhance(0.86)
    else:
        img = Image.blend(img, Image.new("RGB", img.size, (255, 190, 110)), 0.05)
    z = 1 + zoom * ease(scene_t / scene_len)
    if z > 1.001:
        w, h = img.size
        cw, ch = w / z, h / z
        img = img.resize((w, h), Image.BICUBIC, box=((w - cw) / 2, (h - ch) * 0.6, (w + cw) / 2, (h - ch) * 0.6 + ch))
    # vignette
    v = Image.new("L", img.size, 0)
    dv = ImageDraw.Draw(v)
    dv.ellipse([-img.width * 0.15, -img.height * 0.25, img.width * 1.15, img.height * 1.25], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(60 * SS))
    img = Image.composite(img, ImageEnhance.Brightness(img).enhance(0.6), v)
    fade = seg(scene_t, 0, 0.3) * (1 - seg(scene_t, scene_len - 0.3, scene_len))
    if fade < 1:
        img = ImageEnhance.Brightness(img).enhance(fade)
    return img

# ---------------------------------------------------------------- scenes
GOLD = (236, 196, 96)
GREY = (196, 200, 210)
CREAM = (246, 238, 226)
MOM_DRESS = (150, 100, 160)
MOM_HAIR = (90, 60, 50)
OLD_HAIR = (205, 205, 210)
SCENES = [  # (start, end, age)
    (0.0, 8.6, 16),
    (8.6, 15.2, 24),
    (15.2, 21.8, 33),
    (21.8, 28.8, 45),
]

def walk_state(t, t0, t1, x0, x1, speed=9.0):
    u = ease(seg(t, t0, t1))
    moving = t0 < t < t1
    return lerp(x0, x1, u), ((t * speed, 1.0) if moving else None)

def scene1(p, t, top):
    c = Cv(p)
    bg_kitchen(c, warm=True, dim=seg(t, 4.5, 7) * 0.6 if top else 0)
    momdroop = ease(seg(t, 4.6, 6.4)) if top else 0
    figure(c, 130, GROUND, 1, 1, CREAM, "mom", sit=1, arms="down", droop=momdroop,
           hair=MOM_HAIR, dress=MOM_DRESS, bounce=abs(math.sin(t * 14)) * window(t, 5.4, 7.6) if not top else 0)
    if top:
        x, wk = walk_state(t, 3.7, 6.3, 520, 800)
        face = -1 if t < 3.6 else 1
        figure(c, x, GROUND, 1, face, GREY, walk=wk, arms="phone", prop="phone")
        bubble(p, 152, 300, "Got a minute?", pop(t, 0.35))  if t < 2.4 else None
        bubble(p, 500, 290, "Not now, Mom.", pop(t, 2.3)) if 2.3 < t < 4.2 else None
        bubble(p, 152, 310, "...", pop(t, 6.4), size=17) if 6.4 < t < 8.4 else None
    else:
        x, wk = walk_state(t, 3.0, 4.5, 520, 440)
        sit = ease(seg(t, 4.5, 5.0))
        arm = "phone" if t < 2.9 else "down"
        b = abs(math.sin(t * 14 + 1)) * window(t, 5.4, 7.6)
        def hero(cc):
            return figure(cc, x, GROUND, 1, -1, GOLD, walk=wk, sit=sit, arms=arm,
                          prop="phone" if t < 2.9 else None, bounce=b)
        glowing(p, hero, strength=0.6 + 0.4 * seg(t, 2.3, 3.0))
        bubble(p, 152, 300, "Got a minute?", pop(t, 0.35)) if t < 2.4 else None
        bubble(p, 500, 290, "Always.", pop(t, 2.3)) if 2.3 < t < 4.0 else None
        float_ha(p, 300, 280, t, 5.4, 4)
        hearts(p, 290, 300, t, 6.6, 3)

def scene2(p, t, top):
    c = Cv(p)
    if top:
        bg_apartment(c)
        figure(c, 360, GROUND, 1, 1, GREY, sit=1, arms="type", bounce=0)
        sfx(p, 400, 300, "BZZT", t, 0.6, 2.2, size=22, shake=3)
        card(p, t, 0.6, 2.6, "Mom  ·  incoming call", "Mom is calling...", buttons=True, accent=(90, 200, 120))
        sfx(p, 440, 330, "tap", t, 2.1, 2.9, size=16, rot=8)
        card(p, t, 2.6, 3.3, "Mom  ·  call", "Call declined", msg_col=(220, 60, 60), accent=(220, 60, 60))
        card(p, t, 3.6, 6.4, "Mom  ·  now", "ok. call when you're free", sub="Seen" if t > 4.8 else None)
        sfx(p, 460, 340, "click  click", t, 1.0, 6.2, size=13, rot=0) if t > 3.0 else None
    else:
        bg_balcony(c, t)
        ear = ease(seg(t, 1.8, 2.3))
        b = abs(math.sin(t * 13)) * window(t, 3.4, 5.4)
        def hero(cc):
            return figure(cc, 330, GROUND, 1, 1, GOLD, arms="phone", arm_mix=("ear", ear), prop="phone", bounce=b)
        glowing(p, hero)
        sfx(p, 270, 330, "BZZT", t, 0.6, 1.8, size=22, shake=3)
        card(p, t, 0.6, 2.0, "Mom  ·  incoming call", "Mom is calling...", buttons=True, accent=(90, 200, 120))
        bubble(p, 345, 260, "Hey Mom! How are you?", pop(t, 2.3)) if 2.3 < t < 3.7 else None
        float_ha(p, 360, 250, t, 3.6, 4)
        card(p, t, 5.0, 6.5, "Phone", "Mom  ·  1 h 12 min", accent=(90, 200, 120))

def scene3(p, t, top):
    c = Cv(p)
    if top:
        bg_office(c, t)
        figure(c, 240, GROUND, 1, 1, GREY, sit=1, arms="type", droop=0.15)
        card(p, t, 0.6, 2.6, "Calendar  ·  today", "Mom's birthday", accent=(230, 80, 80), tag="ALL DAY")
        sfx(p, 560, 150, "swipe", t, 2.1, 2.8, size=16, rot=-4)
        card(p, t, 3.0, 6.3, "Mom  ·  9:47 PM", "it's okay. i know you're busy", sub="Seen" if t > 4.2 else None)
    else:
        bg_porch(c, t)
        x, wk = walk_state(t, 0.3, 2.4, 790, 380)
        hug = ease(seg(t, 4.6, 5.1))
        xs = lerp(x, 292, ease(seg(t, 4.4, 5.0)))
        figure(c, 220, GROUND, 1, 1, CREAM, "mom", arms="down", arm_mix=("hug", hug), hair=MOM_HAIR, dress=MOM_DRESS)
        def hero(cc):
            h, _ = figure(cc, xs, GROUND, 1, -1, GOLD, walk=wk if t < 2.4 else None,
                          arms="hold", arm_mix=("hug", hug))
            return h
        hand = glowing(p, hero)
        if hug < 0.5:
            cake(Cv(p), hand[0] - 4, hand[1] - 6, t)
        bubble(p, 380, 280, "Happy birthday, Mom!", pop(t, 2.6)) if 2.6 < t < 4.4 else None
        hearts(p, 255, 290, t, 5.0, 4)

def scene4(p, t, top):
    c = Cv(p)
    if top:
        bg_kitchen(c, warm=False, empty=True)
        x, wk = walk_state(t, 3.4, 5.0, 520, 440)
        sit = ease(seg(t, 5.0, 5.5))
        figure(c, x, GROUND, 1, -1, GREY, walk=wk, sit=sit, arms="phone", prop="phone",
               droop=0.6 * ease(seg(t, 4.8, 6.0)))
        card(p, t, 0.5, 6.6, "Voicemail  ·  saved 3 yrs ago", "Mom", accent=(160, 160, 175),
             progress=clamp(seg(t, 1.2, 4.6)))
        bubble(p, 470, 300, "Got a minute?", pop(t, 1.5), dark=False, italic=True) if 1.5 < t < 3.6 else None
        sfx(p, 440, 340, "thud", t, 5.4, 6.4, size=14, rot=6, col=(200, 200, 210))
    else:
        bg_kitchen(c, warm=True)
        b = abs(math.sin(t * 14)) * window(t, 5.2, 6.8)
        figure(c, 130, GROUND, 1, 1, CREAM, "old", sit=1, arms="down", hair=OLD_HAIR, dress=(120, 110, 160), bounce=b)
        kx, kwk = walk_state(t, 0.3, 1.8, 780, 560, speed=12)
        figure(c, kx, GROUND, 0.62, -1, (250, 236, 220), "kid", walk=kwk)
        face = -1 if t < 2.6 else 1
        def hero(cc):
            return figure(cc, 440, GROUND, 1, face, GOLD, sit=1, arms="down", bounce=b)
        glowing(p, hero)
        bubble(p, 560, 340, "Got a minute, Dad?", pop(t, 2.0)) if 2.0 < t < 3.8 else None
        bubble(p, 450, 300, "Always.", pop(t, 3.9)) if 3.9 < t < 5.4 else None
        float_ha(p, 260, 280, t, 5.2, 4)
        hearts(p, 150, 300, t, 5.6, 3)

SCENE_FN = [scene1, scene2, scene3, scene4]

def label(c, x, y, txt, col):
    tw, _ = c.tsize(txt, 18, "ExtraBold")
    c.rect(x, y, x + tw + 24, y + 32, (22, 23, 28, 235), r=7)
    c.d.rounded_rectangle([x * SS, y * SS, (x + tw + 24) * SS, (y + 32) * SS], 7 * SS,
                          outline=(255, 255, 255, 60), width=SS)
    c.text(x + 12 + tw / 2, y + 16, txt, 18, col, w="ExtraBold")

def render(i):
    t = i / FPS
    frame = Image.new("RGB", (W * SS, H * SS), (8, 9, 12))
    si = 3
    for k, (a, b, _) in enumerate(SCENES):
        if t < b: si = k; break
    final = t >= SCENES[-1][1] - 0.0
    if final:
        si, lt = 3, SCENES[3][1] - SCENES[3][0] - 0.31  # hold last frame (before fade)
    else:
        lt = t - SCENES[si][0]
    slen = SCENES[si][1] - SCENES[si][0]
    for top, py in ((True, TOP_Y), (False, BOT_Y)):
        p = Image.new("RGB", (W * SS, PH * SS), (0, 0, 0))
        SCENE_FN[si](p, lt, top)
        img = finish(p, top, lt, slen if not final else 1e9)
        frame.paste(img, (0, py * SS))
    c = Cv(frame)
    label(c, 14, TOP_Y + 14, "BUSY SON", (240, 240, 245))
    label(c, 14, BOT_Y + 14, "PRESENT SON", GOLD)
    c.rect(0, BOT_Y - 2, W, BOT_Y + 2, (14, 14, 18))
    age = SCENES[si][2]
    asz = pop(t, SCENES[si][0] + 0.05, 0.25) if not final else 1
    if asz > 0.1:
        tw = 96 * asz
        c.rect(W / 2 - tw / 2, BOT_Y - 17 * asz, W / 2 + tw / 2, BOT_Y + 17 * asz, (20, 21, 26), r=10 * asz)
        c.d.rounded_rectangle([(W / 2 - tw / 2) * SS, (BOT_Y - 17 * asz) * SS, (W / 2 + tw / 2) * SS,
                               (BOT_Y + 17 * asz) * SS], 10 * asz * SS, outline=(255, 255, 255, 120), width=SS)
        c.text(W / 2, BOT_Y + 1, f"AGE {age}", 17 * asz, (255, 255, 255), w="ExtraBold")
    if final:
        ft = t - SCENES[-1][1]
        ov = Image.new("RGBA", frame.size, (6, 7, 10, int(200 * ease(seg(ft, 0, 0.6)))))
        frame = frame.convert("RGBA"); frame.alpha_composite(ov)
        frame = frame.convert("RGB")
        c = Cv(frame)
        a1 = int(255 * ease(seg(ft, 0.4, 0.9)))
        a2 = int(255 * ease(seg(ft, 1.5, 2.0)))
        c.text(W / 2, 545, "One son never had a minute.", 31, (255, 255, 255, a1), w="ExtraBold")
        c.text(W / 2, 620, "One son gave her", 31, GOLD + (a2,), w="ExtraBold")
        c.text(W / 2, 662, "every one of his.", 31, GOLD + (a2,), w="ExtraBold")
        frame = frame.convert("RGB")
        fo = seg(t, DUR - 0.5, DUR)
        if fo > 0:
            frame = ImageEnhance.Brightness(frame).enhance(1 - fo)
    frame = frame.resize((W, H), Image.LANCZOS)
    frame.save(f"{OUT}/{i:04d}.png")

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    n = int(DUR * FPS)
    only = os.environ.get("ONLY")
    idx = [int(x) for x in only.split(",")] if only else range(n)
    with Pool(4) as pool:
        pool.map(render, idx, chunksize=4)
