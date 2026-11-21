"""SOLMARA — THE ISLE THAT SAILS THE SUNSET.

A vintage travel poster for a place that isn't there, drawn entirely
with Pillow: a floating island with spired towers and waterfalls,
moored above a sunset sea. The program writes JPEG bytes to
/output/entry.png, deterministically (fixed seed), under 1,000,000
bytes.
"""

import io
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W = 1024
H = 1024
HORIZON = 748
SEED = 20261121

CREAM = (242, 232, 210)
INK = (52, 44, 40)


# ---------------------------------------------------------------- helpers

def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(lerp(c1[i], c2[i], t))) for i in range(3))


def multi_gradient(stops, t):
    """Colour at position t along a list of (pos, colour) stops."""
    t = max(0.0, min(1.0, t))
    for i in range(len(stops) - 1):
        t0, c0 = stops[i]
        t1, c1 = stops[i + 1]
        if t0 <= t <= t1:
            local = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return lerp_color(c0, c1, local)
    return stops[-1][1]


def serif(size, bold=False):
    name = "DejaVuSerif-Bold.ttf" if bold else "DejaVuSerif.ttf"
    return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/" + name, size)


def tracked_text(draw, cx, y, text, font, fill, tracking=0,
                 shadow=None, shadow_dy=3):
    """Draw text centred on cx with extra letter tracking."""
    widths = []
    for ch in text:
        box = draw.textbbox((0, 0), ch, font=font)
        widths.append(box[2] - box[0])
    total = sum(widths) + tracking * max(0, len(text) - 1)

    def render(x0, yy, col):
        x = x0
        for i, ch in enumerate(text):
            draw.text((x, yy), ch, font=font, fill=col)
            x += widths[i] + tracking

    if shadow is not None:
        render(cx - total / 2.0, y + shadow_dy, shadow)
    render(cx - total / 2.0, y, fill)


def soft_glow(base, cx, cy, radius, color, max_alpha=160, steps=28):
    """Composite a soft radial glow centred at (cx, cy) onto base."""
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i in range(steps, 0, -1):
        frac = i / steps
        r = radius * frac
        alpha = int(max_alpha * ((1.0 - frac) ** 2.2))
        if alpha > 0:
            d.ellipse((cx - r, cy - r, cx + r, cy + r),
                      fill=(color[0], color[1], color[2], alpha))
    layer = layer.filter(ImageFilter.GaussianBlur(radius * 0.10))
    return Image.alpha_composite(base, layer)


# ---------------------------------------------------------------- backdrop

SKY_STOPS = [
    (0.00, (17, 27, 52)),     # deep navy
    (0.24, (34, 52, 84)),     # slate blue
    (0.46, (78, 72, 104)),    # dusty violet
    (0.66, (156, 90, 92)),    # terracotta rose
    (0.84, (222, 130, 82)),   # burnt apricot
    (1.00, (246, 190, 114)),  # horizon gold
]

SEA_STOPS = [
    (0.00, (44, 72, 94)),
    (0.30, (29, 54, 77)),
    (0.65, (19, 39, 61)),
    (1.00, (13, 27, 45)),
]

SUN_CX, SUN_CY, SUN_R = 512, 668, 114


def paint_sky(img):
    d = ImageDraw.Draw(img)
    for y in range(HORIZON + 1):
        c = multi_gradient(SKY_STOPS, y / HORIZON)
        d.line([(0, y), (W, y)], fill=(c[0], c[1], c[2], 255))


def paint_stars(img, rng):
    d = ImageDraw.Draw(img)
    for _ in range(150):
        sx = rng.randint(46, W - 46)
        sy = rng.randint(46, 372)
        fade = 1.0 - max(0.0, (sy - 46)) / 326.0
        alpha = int(rng.randint(80, 240) * (fade ** 1.15))
        r = 1 if rng.random() < 0.82 else 2
        d.ellipse((sx - r, sy - r, sx + r, sy + r),
                  fill=(250, 242, 218, alpha))
    # a few sparkle crosses among the plain dots
    for _ in range(14):
        sx = rng.randint(60, W - 60)
        sy = rng.randint(56, 300)
        a = rng.randint(120, 210)
        col = (252, 246, 224, a)
        d.line([(sx - 4, sy), (sx + 4, sy)], fill=col, width=1)
        d.line([(sx, sy - 4), (sx, sy + 4)], fill=col, width=1)


def paint_cloud_bands(img, rng):
    """Flat horizontal vintage cloud strata across the lower sky."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    bands = [
        (452, 17, (128, 84, 104, 128)),
        (508, 21, (172, 96, 94, 136)),
        (566, 23, (208, 118, 86, 140)),
        (626, 19, (232, 148, 94, 142)),
        (684, 15, (244, 178, 110, 145)),
    ]
    for by, bh, col in bands:
        for _ in range(12):
            cx = rng.randint(60, W - 60)
            cw = rng.randint(200, 460)
            ch = bh + rng.randint(-4, 10)
            cy = by + rng.randint(-4, 4)
            d.rounded_rectangle(
                (cx - cw // 2, cy - ch // 2, cx + cw // 2, cy + ch // 2),
                radius=ch // 2, fill=col)
    layer = layer.filter(ImageFilter.GaussianBlur(2.2))
    return Image.alpha_composite(img, layer)


def paint_sun(img):
    img = soft_glow(img, SUN_CX, SUN_CY, 320, (255, 196, 112), max_alpha=125)
    img = soft_glow(img, SUN_CX, SUN_CY, 175, (255, 230, 160), max_alpha=160)
    d = ImageDraw.Draw(img)
    d.ellipse((SUN_CX - SUN_R, SUN_CY - SUN_R, SUN_CX + SUN_R, SUN_CY + SUN_R),
              fill=(252, 236, 182, 255))
    # a faint warm rim on the disc
    d.ellipse((SUN_CX - SUN_R, SUN_CY - SUN_R, SUN_CX + SUN_R, SUN_CY + SUN_R),
              outline=(255, 246, 205, 255), width=2)
    return img


def paint_mountains(img):
    d = ImageDraw.Draw(img)
    layers = [
        (40, (100, 74, 94, 205), 17.0),
        (26, (59, 52, 75, 235), 29.0),
    ]
    for amp, col, seed_off in layers:
        pts = [(0, HORIZON)]
        for x in range(0, W + 16, 16):
            dip = 1.0 - 0.60 * math.exp(-((x - 512) ** 2) / 46000.0)
            h = amp * dip * (0.55 + 0.30 * math.sin(x * 0.011 + seed_off)
                             + 0.15 * math.cos(x * 0.027 - seed_off))
            pts.append((x, HORIZON - max(4.0, h)))
        pts.append((W, HORIZON))
        d.polygon(pts, fill=col)


def paint_sea(img, rng):
    d = ImageDraw.Draw(img)
    for y in range(HORIZON, H):
        c = multi_gradient(SEA_STOPS, (y - HORIZON) / (H - HORIZON))
        d.line([(0, y), (W, y)], fill=(c[0], c[1], c[2], 255))

    # wavy golden strokes: the sun's broken reflection column
    for row in range(30):
        base_y = 758 + row * 6.4
        t = row / 30.0
        half_w = 58 + 185 * (t ** 0.9)
        phase = rng.uniform(0, 6.28)
        alpha = int(lerp(95, 42, t))
        pts = []
        steps = 22
        for i in range(steps + 1):
            x = SUN_CX - half_w + (2 * half_w) * (i / steps)
            y = base_y + 3.0 * math.sin(x * 0.045 + phase)
            pts.append((x, y))
        d.line(pts, fill=(243, 196, 122, alpha), width=2)

    # short bright dashes sprinkled inside the column
    for _ in range(300):
        ry = rng.randint(HORIZON + 6, H - 30)
        t = (ry - HORIZON) / (H - HORIZON)
        spread = 55 + 175 * (t ** 0.85)
        rx = int(512 + rng.gauss(0, spread * 0.52))
        rx = max(40, min(W - 40, rx))
        rw = rng.uniform(10, 34 + 42 * t)
        d.line([(rx - rw / 2, ry), (rx + rw / 2, ry)],
               fill=(252, 214, 148, rng.randint(80, 180)), width=1)

    # pale ripples everywhere else
    for _ in range(240):
        ry = rng.randint(HORIZON + 4, H - 26)
        rx = rng.randint(36, W - 36)
        if abs(rx - 512) < 120 and rng.random() < 0.6:
            continue  # keep the shimmer column clean
        rw = rng.uniform(10, 34)
        d.line([(rx - rw / 2, ry), (rx + rw / 2, ry)],
               fill=(86, 124, 140, rng.randint(55, 130)), width=1)


# ---------------------------------------------------------------- the island

ISLE_TOP = 424
ISLE_LEFT = 300
ISLE_RIGHT = 724


def rock_depth(t):
    """How deep the island's underside hangs at profile position t."""
    return (178.0 * (math.sin(math.pi * t) ** 1.3)
            + 26.0 * math.sin(7 * math.pi * t) * math.sin(math.pi * t))


def top_profile(rng):
    pts = []
    steps = 60
    for i in range(steps + 1):
        t = i / steps
        x = lerp(ISLE_LEFT, ISLE_RIGHT, t)
        y = (ISLE_TOP
             - 20.0 * math.sin(math.pi * t)
             - 11.0 * math.exp(-((t - 0.5) ** 2) / 0.05)
             + rng.uniform(-2.5, 2.5))
        pts.append((x, y))
    return pts


def draw_tower(d, tx, base_y, tw, th, is_main):
    roof_h = th * 0.30
    body_top = base_y - th + roof_h
    apex_y = base_y - th
    # body: amber lit left face, indigo shadow right face
    d.polygon([(tx - tw * 0.5, base_y), (tx - tw * 0.44, body_top),
               (tx, body_top), (tx, base_y)], fill=(230, 166, 106, 255))
    d.polygon([(tx, base_y), (tx, body_top),
               (tx + tw * 0.44, body_top), (tx + tw * 0.5, base_y)],
              fill=(66, 60, 88, 255))
    # spire roof: pale lit left, dusky right
    d.polygon([(tx - tw * 0.54, body_top), (tx, apex_y), (tx, body_top)],
              fill=(250, 210, 146, 255))
    d.polygon([(tx, body_top), (tx, apex_y), (tx + tw * 0.54, body_top)],
              fill=(94, 82, 112, 255))
    # finial needle
    d.line([(tx, apex_y), (tx, apex_y - 15)], fill=(255, 238, 195, 255), width=2)
    # lit windows down the lit face
    n = 4 if is_main else 3
    for k in range(n):
        wy = body_top + 9 + k * ((base_y - body_top - 15) / max(1, n))
        ww = tw * 0.20
        wh = 9 if is_main else 7
        d.rectangle((tx - ww * 0.5 - tw * 0.10, wy,
                     tx + ww * 0.5 - tw * 0.10, wy + wh),
                    fill=(255, 244, 198, 255))


def draw_island(img, rng):
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    top = top_profile(rng)

    # underside profile, tip at centre
    bottom = []
    b_steps = 56
    for i in range(b_steps, -1, -1):
        t = i / b_steps
        x = lerp(ISLE_LEFT + 12, ISLE_RIGHT - 12, t)
        y = ISLE_TOP + 16 + rock_depth(t) + rng.uniform(-4.0, 5.0)
        bottom.append((x, y))
    d.polygon(top + bottom, fill=(30, 32, 46, 255))

    # faceted rock planes: warm near the rim, slate/indigo deeper
    for _ in range(120):
        t = rng.uniform(0.05, 0.95)
        px = lerp(ISLE_LEFT + 16, ISLE_RIGHT - 16, t)
        max_d = rock_depth(t)
        py = ISLE_TOP + 8 + rng.uniform(0, max(10.0, max_d * 0.88))
        w = rng.uniform(13, 40)
        h = rng.uniform(16, 50)
        pts = [(px, py - h * 0.5), (px + w * 0.55, py - h * 0.1),
               (px + w * 0.25, py + h * 0.55), (px - w * 0.45, py + h * 0.35),
               (px - w * 0.55, py - h * 0.15)]
        warmth = max(0.0, 1.0 - (py - (ISLE_TOP - 20)) / 120.0)
        roll = rng.random()
        if roll < 0.42 * warmth:
            col = lerp_color((70, 60, 78), (172, 110, 84), rng.uniform(0.3, 0.9))
            col = (col[0], col[1], col[2], 225)
        elif roll < 0.55:
            col = (21, 23, 35, 225)
        else:
            col = (rng.choice([(40, 42, 60), (48, 50, 70), (58, 56, 80)]))
            col = (col[0], col[1], col[2], 225)
        d.polygon(pts, fill=col)

    # meadow: a flatter green band following the top edge
    band_front = [(x, y + 24) for (x, y) in reversed(top)]
    d.polygon(top + band_front, fill=(25, 64, 54, 255))
    strip_front = [(x, y + 10) for (x, y) in reversed(top)]
    d.polygon(top + strip_front, fill=(38, 90, 72, 255))

    # scalloped foliage blobs sitting on the meadow
    greens = [(22, 56, 56), (31, 76, 70), (44, 96, 82), (70, 122, 96)]
    for i in range(len(top) - 1):
        x1, y1 = top[i]
        x2, y2 = top[i + 1]
        for _ in range(2):
            bx = lerp(x1, x2, rng.random())
            by = lerp(y1, y2, rng.random()) + rng.uniform(-3, 6)
            rx = rng.uniform(9, 21)
            ry = rng.uniform(5, 11)
            c = greens[rng.randint(0, len(greens) - 1)]
            d.ellipse((bx - rx, by - ry, bx + rx, by + ry),
                      fill=(c[0], c[1], c[2], 255))

    # warm rim light along the top edge
    d.line(top, fill=(240, 188, 118, 110), width=2)

    # dotted golden lantern path along the meadow front
    path = [(368, 442), (424, 430), (474, 421), (512, 417),
            (556, 423), (604, 433), (642, 444)]
    d.line(path, fill=(236, 176, 100, 175), width=2)
    for px_, py_ in path:
        d.ellipse((px_ - 2.5, py_ - 2.5, px_ + 2.5, py_ + 2.5),
                  fill=(255, 230, 172, 255))

    img = Image.alpha_composite(img, layer)

    # warm glow pooled at the towers, then the towers themselves
    img = soft_glow(img, 512, 316, 96, (255, 216, 135), max_alpha=118)
    img = soft_glow(img, 445, 360, 46, (255, 196, 110), max_alpha=88)
    img = soft_glow(img, 582, 364, 46, (255, 196, 110), max_alpha=88)
    d = ImageDraw.Draw(img)
    towers = [
        (445, 414, 22, 96, False),
        (480, 411, 20, 122, False),
        (512, 409, 32, 166, True),
        (548, 411, 20, 116, False),
        (582, 414, 22, 88, False),
    ]
    for tx, by, tw, th, main in towers:
        draw_tower(d, tx, by, tw, th, main)
    return img


def draw_satellites(img, rng):
    d = ImageDraw.Draw(img)
    rocks = [
        (232, 380, 58, 68, True),
        (795, 366, 64, 76, True),
        (270, 546, 26, 34, False),
        (756, 554, 30, 38, False),
    ]
    for sx, sy, sw, sh, capped in rocks:
        pts = [(sx - sw * 0.5, sy), (sx - sw * 0.2, sy - sh * 0.22),
               (sx + sw * 0.25, sy - sh * 0.18), (sx + sw * 0.5, sy + sh * 0.04),
               (sx + sw * 0.2, sy + sh * 0.62), (sx, sy + sh * 0.85),
               (sx - sw * 0.28, sy + sh * 0.52)]
        d.polygon(pts, fill=(29, 31, 45, 255))
        if capped:
            d.polygon([(sx - sw * 0.46, sy), (sx, sy - sh * 0.21),
                       (sx + sw * 0.44, sy + sh * 0.02), (sx, sy + sh * 0.14)],
                      fill=(40, 84, 74, 255))
    return img


def draw_waterfalls(img, rng):
    """Layered translucent falls with bright cores, foam and mist."""
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    falls = [
        (362, 452, 42, 770),   # island falls: broad
        (432, 470, 22, 760),
        (598, 468, 24, 760),
        (662, 450, 38, 770),
        (232, 424, 17, 756),   # satellite falls: thin
        (795, 410, 18, 756),
    ]
    for wx, y0, ww, y1 in falls:
        for frac, alpha, col in [
            (1.00, 62, (148, 212, 210)),
            (0.68, 125, (204, 242, 234)),
            (0.36, 205, (248, 252, 244)),
        ]:
            half = ww * frac / 2.0
            d.rectangle((wx - half, y0, wx + half, y1),
                        fill=(col[0], col[1], col[2], alpha))
        # broken foam streaks
        for _ in range(9):
            sx = wx + rng.uniform(-ww * 0.38, ww * 0.38)
            sy = y0 + rng.uniform(0, 36)
            while sy < y1 - 14:
                seg = rng.uniform(16, 50)
                d.line([(sx, sy), (sx, min(y1, sy + seg))],
                       fill=(255, 253, 245, rng.randint(120, 230)), width=1)
                sy += seg + rng.uniform(8, 22)
        # mist puffs where the fall lands
        for _ in range(18):
            mx = wx + rng.gauss(0, ww * 0.8)
            my = y1 + rng.gauss(0, 6)
            mr = rng.uniform(6, 17)
            d.ellipse((mx - mr, my - mr * 0.55, mx + mr, my + mr * 0.55),
                      fill=(240, 247, 240, rng.randint(55, 135)))
    layer = layer.filter(ImageFilter.GaussianBlur(1.3))
    return Image.alpha_composite(img, layer)


# ---------------------------------------------------------------- traffic & foreground

def draw_airship(d, cx, cy, scale=1.0, flip=False):
    sgn = -1 if flip else 1
    rx, ry = 35 * scale, 11.5 * scale
    # hull
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=(40, 36, 54, 242))
    # sunlit crown of the envelope
    d.pieslice((cx - rx, cy - ry, cx + rx, cy + ry), start=185, end=355,
               fill=(226, 148, 96, 225))
    # tail fins
    tx = cx - sgn * rx * 0.85
    d.polygon([(tx, cy), (tx - sgn * 11 * scale, cy - 11 * scale),
               (tx + sgn * 4 * scale, cy - 3 * scale)], fill=(32, 30, 46, 242))
    d.polygon([(tx, cy), (tx - sgn * 11 * scale, cy + 10 * scale),
               (tx + sgn * 4 * scale, cy + 3 * scale)], fill=(32, 30, 46, 242))
    # rigging + gondola with one lit porthole
    gx1, gx2 = cx - 10 * scale, cx + 10 * scale
    gy1, gy2 = cy + ry + 3 * scale, cy + ry + 7.5 * scale
    d.line([(cx - 8 * scale, cy + ry * 0.8), (gx1, gy1)],
           fill=(32, 30, 46, 200), width=1)
    d.line([(cx + 8 * scale, cy + ry * 0.8), (gx2, gy1)],
           fill=(32, 30, 46, 200), width=1)
    d.rectangle((gx1, gy1, gx2, gy2), fill=(32, 30, 46, 245))
    d.ellipse((cx - 2 * scale, gy1 + 1 * scale, cx + 2 * scale, gy2 - 1 * scale),
              fill=(255, 224, 150, 255))


def draw_boats(d):
    boats = [(306, 800, 0.8), (698, 786, 0.65), (750, 828, 1.0)]
    for bx, by, bs in boats:
        d.polygon([(bx - 10 * bs, by), (bx + 10 * bs, by),
                   (bx + 6 * bs, by + 4 * bs), (bx - 6 * bs, by + 4 * bs)],
                  fill=(19, 25, 39, 235))
        d.polygon([(bx, by - 1 * bs), (bx, by - 18 * bs), (bx + 9 * bs, by - 2 * bs)],
                  fill=(240, 222, 190, 220))
        d.polygon([(bx - 1 * bs, by - 1 * bs), (bx - 1 * bs, by - 14 * bs),
                   (bx - 8 * bs, by - 2 * bs)], fill=(202, 172, 144, 200))


def draw_pine(d, px, py, th):
    d.rectangle((px - 3, py - th * 0.22, px + 3, py + 4), fill=(15, 19, 30, 255))
    for tier in range(4):
        ty = py - th * (0.20 + tier * 0.20)
        tw = (4 - tier) * 11 + 8
        d.polygon([(px - tw, ty), (px + tw, ty), (px, ty - th * 0.27)],
                  fill=(19, 40, 44, 255))


def draw_foreground(img, rng):
    d = ImageDraw.Draw(img)
    left = [(0, 786), (86, 799), (166, 827), (236, 864),
            (316, 914), (398, 990), (398, 1024), (0, 1024)]
    right = [(1024, 778), (932, 791), (846, 823), (768, 866),
             (686, 920), (616, 990), (616, 1024), (1024, 1024)]
    d.polygon(left, fill=(21, 25, 39, 255))
    d.polygon(right, fill=(19, 23, 37, 255))
    # warm rim light along each crest
    d.line(left[:6], fill=(168, 108, 84, 175), width=3)
    d.line(right[:6], fill=(168, 108, 84, 175), width=3)

    for px, py, th in [(92, 802, 78), (136, 818, 56),
                       (930, 794, 84), (884, 812, 60)]:
        draw_pine(d, px, py, th)

    # scattered leaves and small blossoms along the bottom edges
    palette = [(214, 102, 84), (236, 156, 106), (244, 216, 172)]
    for side in (-1, 1):
        for _ in range(26):
            if side == -1:
                bx = rng.randint(36, 292)
            else:
                bx = rng.randint(W - 292, W - 36)
            by = rng.randint(866, 946)
            ang = rng.uniform(-1.1, 1.1)
            llen = rng.uniform(16, 32)
            lx = bx + math.sin(ang) * llen
            ly = by - math.cos(ang) * llen
            d.line([(bx, by), (lx, ly)], fill=(30, 66, 62, 255), width=4)
            if rng.random() < 0.45:
                fc = palette[rng.randint(0, len(palette) - 1)]
                for p in range(5):
                    pa = 2 * math.pi * p / 5.0
                    ex = bx + math.cos(pa) * 5
                    ey = by + math.sin(pa) * 5
                    d.ellipse((ex - 4, ey - 4, ex + 4, ey + 4),
                              fill=(fc[0], fc[1], fc[2], 255))
                d.ellipse((bx - 2, by - 2, bx + 2, by + 2),
                          fill=(255, 240, 200, 255))
    return img


# ---------------------------------------------------------------- assembly

def add_grain(img, rng):
    """Subtle film grain from the seeded RNG (byte-identical runs)."""
    noise = Image.frombytes("L", (W, H), rng.randbytes(W * H))
    lut = [max(0, min(255, 128 + (v - 128) // 5)) for v in range(256)]
    noise = noise.point(lut).convert("RGB")
    return Image.blend(img.convert("RGB"), noise, 0.055).convert("RGBA")


def paint_frame_and_text(img):
    d = ImageDraw.Draw(img)
    # poster text, inside the art
    tracked_text(d, 512, 52, "SOLMARA", serif(152, bold=True),
                 (250, 240, 214, 255), tracking=13,
                 shadow=(22, 19, 36, 150), shadow_dy=4)
    tracked_text(d, 512, 224, "THE ISLE THAT SAILS THE SUNSET",
                 serif(37), (246, 226, 190, 255), tracking=6,
                 shadow=(22, 19, 36, 140), shadow_dy=3)

    # cream paper border + footer band
    d.rectangle((0, 0, W, 36), fill=CREAM + (255,))
    d.rectangle((0, 950, W, H), fill=CREAM + (255,))
    d.rectangle((0, 0, 36, H), fill=CREAM + (255,))
    d.rectangle((W - 36, 0, W, H), fill=CREAM + (255,))
    # thin dark keylines: outer edge and around the art
    d.rectangle((7, 7, W - 8, H - 8), outline=INK + (255,), width=2)
    d.rectangle((36, 36, W - 37, 949), outline=INK + (255,), width=2)

    tracked_text(d, 512, 957, "VISIT SOLMARA · AIRSHIP DAILY FROM PORT AURELE",
                 serif(27), INK + (255,), tracking=3)
    return img


def build_poster():
    rng = random.Random(SEED)
    img = Image.new("RGBA", (W, H), CREAM + (255,))
    paint_sky(img)
    paint_stars(img, rng)
    img = paint_cloud_bands(img, rng)
    img = paint_sun(img)
    paint_mountains(img)
    paint_sea(img, rng)
    img = draw_satellites(img, rng)
    img = draw_island(img, rng)
    img = draw_waterfalls(img, rng)
    d = ImageDraw.Draw(img)
    draw_airship(d, 216, 312, scale=1.05, flip=False)
    draw_airship(d, 806, 330, scale=0.68, flip=True)
    draw_boats(d)
    img = draw_foreground(img, rng)
    img = add_grain(img, rng)
    img = paint_frame_and_text(img)
    return img


def save_poster(img, path="/output/entry.png"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rgb = img.convert("RGB")
    quality = 92
    while True:
        buf = io.BytesIO()
        rgb.save(buf, "JPEG", quality=quality)
        data = buf.getvalue()
        if len(data) <= 1_000_000 or quality <= 40:
            break
        quality -= 4
    with open(path, "wb") as fh:
        fh.write(data)
    return len(data), quality


def main():
    img = build_poster()
    size, quality = save_poster(img)
    print(f"wrote /output/entry.png: {size} bytes at JPEG quality {quality}")


if __name__ == "__main__":
    main()
