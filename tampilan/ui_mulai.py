import json
import math
import pygame
from core import config
from tampilan import theme

FPS = getattr(config, "FPS", 60)

# Warna dari design tokens (tampilan/theme.py)
C_BG = theme.BG_DEEP
C_TITLE = theme.TEXT
C_LABEL = theme.TEXT_MUTED
C_ENEMY_LABEL = theme.ASTAR
C_COND_LABEL = theme.BFS
C_TEXT = theme.TEXT
C_SUBTEXT = theme.TEXT_MUTED

C_CARD = theme.SURFACE
C_BTN = theme.SURFACE_2
C_BORDER = theme.BORDER

# Satu aksen "terpilih" untuk map & kondisi
C_MAZE_ACTIVE_FILL = theme.BFS
C_MAZE_ACTIVE_BORDER = theme.lighten(theme.BFS, 45)
C_ENEMY_ACTIVE_FILL = theme.SURFACE_2
C_ENEMY_ACTIVE_BORDER = theme.BORDER
C_COND_ACTIVE_FILL = theme.BFS
C_COND_ACTIVE_BORDER = theme.lighten(theme.BFS, 45)

C_BACK_FILL = theme.SURFACE_2
C_START_FILL = theme.SUCCESS

C_WALL = theme.WALL
C_PATH = theme.PATH
C_EXIT = theme.EXIT
C_PACMAN = theme.PACMAN
C_GHOST = theme.GHOST_RED

# Teks 2 baris untuk masing-masing Map sesuai rancangan PDF
MAP_CAPTIONS = {
    1: ("Maze Mudah", "Banyak Jalur Alternatif"),
    2: ("Maze Sedang", "Loop dan Percabangan"),
    3: ("Maze Sulit", "Loop Bersarang dan Belokan"),
}

MAP_OPTIONS = [(mid, MAP_CAPTIONS[mid]) for mid in (1, 2, 3)]
ALGO_OPTIONS = [("bfs", "BFS"), ("astar", "A*")]
COND_OPTIONS = [("diam", "Pac-Man Diam"), ("bergerak", "Pac-Man Bergerak")]

def _font(size, bold=False):
    return theme.font(size, bold)


def _text(screen, msg, size, color, center, bold=False):
    surf = _font(size, bold).render(str(msg), True, color)
    screen.blit(surf, surf.get_rect(center=center))


def _fit_size(msg, max_w, start, bold=False):
    """Ukuran font terbesar (<= start) agar teks muat dalam max_w."""
    size = int(start)
    while size > 8 and _font(size, bold).size(msg)[0] > max_w:
        size -= 1
    return size


def _lighten(color, amount=16):
    return tuple(min(255, v + amount) for v in color)


def _draw_pacman(surface, center, radius, mouth_bg_color, mouth_angle_deg=35, with_eye=True):
    """Menggambar Pac-Man kuning lengkap dengan mulut terbuka ke kanan."""
    cx, cy = int(center[0]), int(center[1])
    r = max(int(radius), 2)

    # 1. Gambar tubuh lingkaran kuning
    pygame.draw.circle(surface, C_PACMAN, (cx, cy), r)

    # 2. Gambar mulut (segitiga berwarna latar di sisi kanan)
    rad = math.radians(mouth_angle_deg)
    # Dilebihkan sedikit (r + 2) agar tepi lingkaran terpotong rapi
    p1 = (cx, cy)
    p2 = (cx + int((r + 2) * math.cos(rad)), cy - int((r + 2) * math.sin(rad)))
    p3 = (cx + int((r + 2) * math.cos(rad)), cy + int((r + 2) * math.sin(rad)))
    pygame.draw.polygon(surface, mouth_bg_color, [p1, p2, p3])

    # 3. Gambar mata kecil hitam di bagian atas kepala (jika radius cukup besar)
    if with_eye and r >= 6:
        eye_x = cx - int(r * 0.08)
        eye_y = cy - int(r * 0.48)
        eye_r = max(int(r * 0.16), 1)
        pygame.draw.circle(surface, (15, 15, 25), (eye_x, eye_y), eye_r)


_preview_cache = {}


def _load_maze_data(maze_id):
    if maze_id not in _preview_cache:
        with open(config.MAZE_FILES[maze_id], "r") as f:
            _preview_cache[maze_id] = json.load(f)
    return _preview_cache[maze_id]


def _build_preview(data, side):
    rows = data["grid"]
    n, m = len(rows), len(rows[0])
    cell = max(side // max(n, m), 2)
    surf = pygame.Surface((cell * m, cell * n))
    surf.fill(C_PATH)
    for r, row in enumerate(rows):
        for c, v in enumerate(row):
            if v == 1:
                pygame.draw.rect(surf, C_WALL, (c * cell, r * cell, cell, cell))
    pad = max(cell // 5, 1)
    er, ec = data["exit"]
    pygame.draw.rect(
        surf, C_EXIT, (ec * cell + pad, er * cell + pad, cell - 2 * pad, cell - 2 * pad)
    )

    # Gambar Pac-Man dengan mulut di dalam preview map
    pr, pc = data["pacman_start"]
    pac_center = (pc * cell + cell // 2, pr * cell + cell // 2)
    _draw_pacman(surf, pac_center, max(cell // 2 - 1, 2), C_PATH, mouth_angle_deg=35, with_eye=False)

    # Gambar Ghost merah di dalam preview map
    gr, gc = data["ghost_start"]
    pygame.draw.circle(
        surf, C_GHOST, (gc * cell + cell // 2, gr * cell + cell // 2), max(cell // 2 - 1, 2)
    )
    return surf


class Button:
    def __init__(self, rect, label, value=None, font_size=20, bold=False, radius=10):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.font_size = font_size
        self.bold = bold
        self.radius = radius

    def hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, screen, fill=C_BTN, border=C_BORDER, border_w=2, text_color=C_TEXT):
        color = _lighten(fill) if self.hovered() else fill
        pygame.draw.rect(screen, color, self.rect, border_radius=self.radius)
        pygame.draw.rect(screen, border, self.rect, border_w, border_radius=self.radius)
        _text(
            screen, self.label, self.font_size, text_color, self.rect.center, self.bold
        )

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class MapCard:
    def __init__(self, rect, maze_id, title_line, sub_line, preview, title_size, sub_size, pad):
        self.rect = pygame.Rect(rect)
        self.maze_id = maze_id
        self.title_line = title_line
        self.sub_line = sub_line
        self.preview = preview
        self.title_size = title_size
        self.sub_size = sub_size
        self.pad = pad

    def hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, screen, active):
        if active:
            fill, border, bw = C_MAZE_ACTIVE_FILL, C_MAZE_ACTIVE_BORDER, 3
        else:
            fill, border, bw = C_CARD, C_BORDER, 2
        if self.hovered():
            fill = _lighten(fill)

        pygame.draw.rect(screen, fill, self.rect, border_radius=12)
        pygame.draw.rect(screen, border, self.rect, bw, border_radius=12)

        pr = self.preview.get_rect(midtop=(self.rect.centerx, self.rect.top + self.pad))
        screen.blit(self.preview, pr)

        # Area teks 2 baris di bawah preview maze
        text_area_top = pr.bottom
        text_area_h = self.rect.bottom - text_area_top
        y_title = text_area_top + int(text_area_h * 0.34)
        y_sub = text_area_top + int(text_area_h * 0.70)

        _text(screen, self.title_line, self.title_size, C_TEXT, (self.rect.centerx, y_title), bold=True)
        _text(screen, self.sub_line, self.sub_size, C_SUBTEXT, (self.rect.centerx, y_sub), bold=False)

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


class ConditionCard:
    def __init__(self, rect, value, caption, icon_type, font_size, scale):
        self.rect = pygame.Rect(rect)
        self.value = value
        self.caption = caption
        self.icon_type = icon_type
        self.font_size = font_size
        self.s = scale

    def hovered(self):
        return self.rect.collidepoint(pygame.mouse.get_pos())

    def draw(self, screen, active):
        if active:
            fill, border, bw = C_COND_ACTIVE_FILL, C_COND_ACTIVE_BORDER, 3
        else:
            fill, border, bw = C_CARD, C_BORDER, 2
        if self.hovered():
            fill = _lighten(fill)

        pygame.draw.rect(screen, fill, self.rect, border_radius=12)
        pygame.draw.rect(screen, border, self.rect, bw, border_radius=12)

        s = self.s
        cx = self.rect.centerx
        cy = self.rect.top + int(self.rect.height * 0.36)
        r = max(int(10 * s), 6)
        arrow_w = max(int(2.5 * s), 2)

        if self.icon_type == "diam":
            # Ghost Merah -> Panah Putih -> Pac-Man Kuning (mulut sedikit terbuka)
            ghost_x = cx - int(44 * s)
            pac_x = cx + int(44 * s)
            line_x1 = cx - int(22 * s)
            line_x2 = cx + int(16 * s)
            tip_x = cx + int(27 * s)
            head_h = int(6 * s)

            pygame.draw.circle(screen, (255, 35, 35), (ghost_x, cy), r)
            pygame.draw.line(screen, C_TITLE, (line_x1, cy), (line_x2, cy), arrow_w)
            pygame.draw.polygon(
                screen,
                C_TITLE,
                [(line_x2, cy - head_h), (line_x2, cy + head_h), (tip_x, cy)],
            )
            # Gambar Pac-Man dengan mulut & mata (warna mulut menyatu dengan warna fill kartu)
            _draw_pacman(screen, (pac_x, cy), r, fill, mouth_angle_deg=25, with_eye=True)

        elif self.icon_type == "bergerak":
            # 3 Garis Kecepatan -> Pac-Man Kuning (mulut terbuka lebar) -> Panah Putih -> Ghost Merah
            speed_x1 = cx - int(68 * s)
            speed_x2 = cx - int(50 * s)
            pac_x = cx - int(32 * s)
            line_x1 = cx - int(12 * s)
            line_x2 = cx + int(24 * s)
            tip_x = cx + int(35 * s)
            ghost_x = cx + int(52 * s)
            head_h = int(6 * s)

            for offset in (-int(7 * s), 0, int(7 * s)):
                pygame.draw.line(
                    screen, C_TEXT, (speed_x1, cy + offset), (speed_x2, cy + offset), max(int(2 * s), 1)
                )
            # Gambar Pac-Man bergerak dengan mulut terbuka lebih lebar
            _draw_pacman(screen, (pac_x, cy), r, fill, mouth_angle_deg=38, with_eye=True)

            pygame.draw.line(screen, C_TITLE, (line_x1, cy), (line_x2, cy), arrow_w)
            pygame.draw.polygon(
                screen,
                C_TITLE,
                [(line_x2, cy - head_h), (line_x2, cy + head_h), (tip_x, cy)],
            )
            pygame.draw.circle(screen, (255, 35, 35), (ghost_x, cy), r)

        # Label teks di bagian bawah kartu
        text_y = self.rect.top + int(self.rect.height * 0.74)
        _text(screen, self.caption, self.font_size, C_TEXT, (cx, text_y), bold=True)

    def clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


def show_mulai(screen=None):
    if screen is None:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Pac-Man AI: BFS vs A*")
    w, h = screen.get_size()
    clock = pygame.time.Clock()
    s = min(h / 850.0, w / 1400.0)  # Skala dibatasi viewport agar layout tetap muat

    sel = {"maze": 1, "algorithm": "bfs", "condition": "diam"}

    # --- TOMBOL BACK (Pojok Kiri Atas) ---
    back_btn = Button(
        (int(18 * s), int(18 * s), int(112 * s), int(40 * s)),
        "BACK",
        "back",
        int(18 * s),
        bold=True,
        radius=8,
    )

    # --- 1. LAYOUT PILIH MAP ---
    pad = int(14 * s)
    gap = int(26 * s)
    card_w = min(int(w * 0.24), int(275 * s))
    side = min(card_w - 2 * pad, int(205 * s))
    caption_h = int(56 * s)
    card_h = pad + side + caption_h
    total_w = 3 * card_w + 2 * gap
    x0 = (w - total_w) // 2
    card_top = int(h * 0.145)

    title_size = min(
        _fit_size(t_line, card_w - 2 * pad, int(17 * s), bold=True)
        for _, (t_line, _) in MAP_OPTIONS
    )
    sub_size = min(
        _fit_size(s_line, card_w - 2 * pad, int(13 * s), bold=False)
        for _, (_, s_line) in MAP_OPTIONS
    )

    cards = []
    for i, (maze_id, (t_line, s_line)) in enumerate(MAP_OPTIONS):
        rect = (x0 + i * (card_w + gap), card_top, card_w, card_h)
        preview = _build_preview(_load_maze_data(maze_id), side)
        cards.append(MapCard(rect, maze_id, t_line, s_line, preview, title_size, sub_size, pad))

    # --- 2. LAYOUT ALGORITMA MUSUH ---
    algo_w, algo_h, algo_gap = int(205 * s), int(48 * s), int(22 * s)
    algo_total = 2 * algo_w + algo_gap
    algo_top = int(h * 0.555)
    algo_btns = [
        Button(
            (w // 2 - algo_total // 2 + i * (algo_w + algo_gap), algo_top, algo_w, algo_h),
            label,
            value,
            int(20 * s),
            bold=True,
            radius=10,
        )
        for i, (value, label) in enumerate(ALGO_OPTIONS)
    ]

    # --- 3. LAYOUT GAME CONDITION ---
    cond_w, cond_h, cond_gap = int(255 * s), int(92 * s), int(22 * s)
    cond_total = 2 * cond_w + cond_gap
    cond_top = int(h * 0.70)
    cond_cards = [
        ConditionCard(
            (w // 2 - cond_total // 2 + i * (cond_w + cond_gap), cond_top, cond_w, cond_h),
            value,
            caption,
            value,
            int(16 * s),
            s,
        )
        for i, (value, caption) in enumerate(COND_OPTIONS)
    ]

    # --- 4. LAYOUT TOMBOL MULAI GAME ---
    start_w, start_h = int(310 * s), int(58 * s)
    start_btn = Button(
        (w // 2 - start_w // 2, int(h * 0.855), start_w, start_h),
        "MULAI GAME",
        "start",
        int(24 * s),
        bold=True,
        radius=12,
    )

    def result():
        return {
            "maze": sel["maze"],
            "algorithm": sel["algorithm"],
            "condition": sel["condition"],
        }

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back"
                if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    return result()
                if event.key in (pygame.K_1, pygame.K_2, pygame.K_3):
                    sel["maze"] = event.key - pygame.K_0
                if event.key in (pygame.K_b, pygame.K_TAB):
                    sel["algorithm"] = "astar" if sel["algorithm"] == "bfs" else "bfs"
                if event.key == pygame.K_c:
                    sel["condition"] = "bergerak" if sel["condition"] == "diam" else "diam"

            if back_btn.clicked(event):
                return "back"
            for card in cards:
                if card.clicked(event):
                    sel["maze"] = card.maze_id
            for b in algo_btns:
                if b.clicked(event):
                    sel["algorithm"] = b.value
            for c in cond_cards:
                if c.clicked(event):
                    sel["condition"] = c.value
            if start_btn.clicked(event):
                return result()

        # --- RENDER TAMPILAN ---
        screen.fill(C_BG)

        # Tombol Back
        back_btn.draw(screen, fill=C_BACK_FILL, border=(190, 175, 220), border_w=2)

        # Judul Utama
        _text(screen, "PENGATURAN GAME", int(34 * s), C_TITLE, (w // 2, int(h * 0.058)), bold=True)

        # Section 1: Pilih Map
        _text(screen, "PILIH MAP", int(18 * s), C_LABEL, (w // 2, int(h * 0.115)), bold=True)
        for card in cards:
            card.draw(screen, active=(sel["maze"] == card.maze_id))

        # Section 2: Algoritma Musuh
        _text(screen, "ALGORITMA MUSUH", int(18 * s), C_ENEMY_LABEL, (w // 2, int(h * 0.52)), bold=True)
        for b in algo_btns:
            if sel["algorithm"] == b.value:
                identitas = theme.warna_algoritma(b.value)
                b.draw(screen, fill=identitas,
                       border=theme.lighten(identitas, 50), border_w=3,
                       text_color=theme.BG_DEEP)
            else:
                b.draw(screen, fill=C_BTN, border=C_BORDER, border_w=2)

        # Section 3: Game Condition
        _text(screen, "GAME CONDITION", int(18 * s), C_COND_LABEL, (w // 2, int(h * 0.665)), bold=True)
        for c in cond_cards:
            c.draw(screen, active=(sel["condition"] == c.value))

        # Tombol Mulai Game
        start_btn.draw(screen, fill=C_START_FILL, border=(160, 235, 175), border_w=2)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    pygame.init()
    scr = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    print("Hasil:", show_mulai(scr))
    pygame.quit()