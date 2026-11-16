import json
import pygame
import csv 
import os

try:
    from core import config
except ImportError:
    class DummyConfig:
        FPS = 60
        MAZE_TITLES = {1: "Maze Mudah", 2: "Maze Sedang", 3: "Maze Sulit"}
        MAZE_FILES = {1: "dummy.json", 2: "dummy.json", 3: "dummy.json"}
    config = DummyConfig()

# ==============================================================================
# KONFIGURASI WARNA & FONT
# ==============================================================================
FPS = getattr(config, "FPS", 60)
C_BG = (8, 8, 20) 

C_CARD_BG = (20, 20, 30)
C_CARD_BORDER = (40, 100, 150)

C_MAP_BG = (85, 60, 130)
C_MAP_BORDER = (180, 130, 220)

C_TITLE = (255, 255, 255)
C_TEXT_CYAN = (0, 220, 255)
C_TEXT_GRAY = (150, 150, 170)

C_STAT_BG = (12, 12, 20)
C_STAT_BORDER = (50, 50, 70)

C_WALL = (34, 34, 221)
C_PATH = (0, 0, 0)
C_EXIT = (0, 200, 0)
C_PACMAN = (255, 220, 0)
C_GHOST = (255, 0, 0)

C_BTN_EXPORT = (30, 120, 70)
C_BTN_EXPORT_HOVER = (40, 160, 90)
C_MSG_SUCCESS = (50, 255, 100)

# --- WARNA TOMBOL BACK BARU (Sesuai Gambar) ---
C_BACK_BG = (74, 46, 107)       # Ungu gelap
C_BACK_BG_HOVER = (94, 66, 127) # Ungu lebih terang saat di-hover
C_BACK_BORDER = (255, 255, 255) # Border putih
C_BACK_ARROW = (255, 255, 255)  # Panah putih

_fonts = {}

def _font(size, bold=False):
    key = (max(int(size), 8), bold)
    if key not in _fonts:
        _fonts[key] = pygame.font.SysFont("consolas", key[0], bold=bold)
    return _fonts[key]

def _text(screen, msg, size, color, center, bold=False):
    surf = _font(size, bold).render(str(msg), True, color)
    screen.blit(surf, surf.get_rect(center=center))

# ==============================================================================
# FUNGSI EXPORT KE EXCEL
# ==============================================================================
def export_to_csv(data, filename="Hasil_Percobaan_Pacman.csv"):
    try:
        with open(filename, mode='w', newline='', encoding='utf-8-sig') as file:
            file.write("sep=,\n")
            writer = csv.writer(file, delimiter=',')
            writer.writerow(["No", "Nama Map", "Kondisi", "Waktu Pencarian (ms)", "Jumlah Simpul", "Panjang Alur (Langkah)"])
            for i, item in enumerate(data):
                writer.writerow([
                    i + 1, 
                    item["nama_map"], 
                    item["kondisi"], 
                    item["waktu"], 
                    item["simpul"], 
                    item["panjang"]
                ])
        return True, filename
    except Exception as e:
        return False, str(e)

# ==============================================================================
# FUNGSI MENGGAMBAR PREVIEW MAP
# ==============================================================================
_preview_cache = {}

def _load_maze_data(maze_id):
    if maze_id not in _preview_cache:
        try:
            with open(config.MAZE_FILES[maze_id], "r") as f:
                _preview_cache[maze_id] = json.load(f)
        except Exception:
            _preview_cache[maze_id] = {
                "grid": [[1]*15 if i%2==0 else [1]+[0]*13+[1] for i in range(15)],
                "exit": (13, 13), "pacman_start": (1, 1), "ghost_start": (1, 13)
            }
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
    pygame.draw.rect(surf, C_EXIT, (ec * cell + pad, er * cell + pad, cell - 2 * pad, cell - 2 * pad))
    for key, color in (("pacman_start", C_PACMAN), ("ghost_start", C_GHOST)):
        r, c = data[key]
        pygame.draw.circle(surf, color, (c * cell + cell // 2, r * cell + cell // 2), max(cell // 2 - 1, 2))
    return surf

# ==============================================================================
# FUNGSI MENGGAMBAR IKON STATISTIK
# ==============================================================================
def _draw_icon_clock(screen, cx, cy, r):
    pygame.draw.circle(screen, (40, 80, 100), (cx, cy), r)
    pygame.draw.circle(screen, C_TEXT_CYAN, (cx, cy), r, 2)
    pygame.draw.line(screen, C_TEXT_CYAN, (cx, cy), (cx, cy - r//2), 2)
    pygame.draw.line(screen, C_TEXT_CYAN, (cx, cy), (cx + r//3, cy), 2)

def _draw_icon_nodes(screen, cx, cy, r):
    pygame.draw.circle(screen, (40, 80, 100), (cx, cy), r)
    pygame.draw.circle(screen, C_TEXT_CYAN, (cx, cy), r, 2)
    pygame.draw.circle(screen, C_TEXT_CYAN, (cx, cy - r//2), 3)
    pygame.draw.circle(screen, C_TEXT_CYAN, (cx - r//2, cy + r//2), 3)
    pygame.draw.circle(screen, C_TEXT_CYAN, (cx + r//2, cy + r//2), 3)
    pygame.draw.line(screen, C_TEXT_CYAN, (cx, cy - r//2), (cx - r//2, cy + r//2), 2)
    pygame.draw.line(screen, C_TEXT_CYAN, (cx, cy - r//2), (cx + r//2, cy + r//2), 2)

def _draw_icon_path(screen, cx, cy, r):
    pygame.draw.circle(screen, (40, 80, 100), (cx, cy), r)
    pygame.draw.circle(screen, C_TEXT_CYAN, (cx, cy), r, 2)
    pts = [(cx - r//2, cy + r//3), (cx, cy), (cx + r//3, cy + r//3), (cx + r//2, cy - r//3)]
    pygame.draw.lines(screen, C_TEXT_CYAN, False, pts, 2)

# ==============================================================================
# CLASS KARTU PERCOBAAN
# ==============================================================================
class ExperimentCard:
    def __init__(self, x, y, w, h, index, data):
        self.rect = pygame.Rect(x, y, w, h)
        self.index = index
        self.data = data
        
    def draw(self, screen, screen_offset_y):
        draw_rect = self.rect.copy()
        draw_rect.y += screen_offset_y
        
        if draw_rect.bottom < 0 or draw_rect.top > screen.get_height():
            return

        pygame.draw.rect(screen, C_CARD_BG, draw_rect, border_radius=12)
        pygame.draw.rect(screen, C_CARD_BORDER, draw_rect, 2, border_radius=12)

        _text(screen, f"PERCOBAAN {self.index}", int(16), C_TITLE, (draw_rect.centerx, draw_rect.y + 25), bold=True)

        map_w = draw_rect.width - 40
        map_h = int(map_w * 0.65)
        map_rect = pygame.Rect(draw_rect.x + 20, draw_rect.y + 50, map_w, map_h)
        
        pygame.draw.rect(screen, C_MAP_BG, map_rect, border_radius=10)
        pygame.draw.rect(screen, C_MAP_BORDER, map_rect, 2, border_radius=10)
        
        maze_data = _load_maze_data(self.data["maze_id"])
        preview_surf = _build_preview(maze_data, map_h - 60)
        pr = preview_surf.get_rect(center=(map_rect.centerx, map_rect.y + (map_h - 30)//2))
        screen.blit(preview_surf, pr)

        _text(screen, self.data["nama_map"], int(12), C_TITLE, (map_rect.centerx, map_rect.bottom - 25), bold=True)
        _text(screen, f"KONDISI: {self.data['kondisi']}", int(14), C_TEXT_CYAN, (draw_rect.centerx, map_rect.bottom + 25), bold=True)

        stat_y = map_rect.bottom + 45
        stat_w = (draw_rect.width - 50) // 3
        stat_h = draw_rect.bottom - stat_y - 20
        gap = 5
        
        stats = [
            ("WAKTU\nPENCARIAN", str(self.data["waktu"]), "ms", "clock"),
            ("JUMLAH\nSIMPUL", str(self.data["simpul"]), "simpul", "nodes"),
            ("PANJANG\nALUR", str(self.data["panjang"]), "langkah", "path")
        ]

        for i, (label, val, unit, icon_type) in enumerate(stats):
            sx = draw_rect.x + 20 + i * (stat_w + gap)
            sub_rect = pygame.Rect(sx, stat_y, stat_w, stat_h)
            
            pygame.draw.rect(screen, C_STAT_BG, sub_rect, border_radius=8)
            pygame.draw.rect(screen, C_STAT_BORDER, sub_rect, 1, border_radius=8)
            
            icon_cy = sub_rect.y + 30
            if icon_type == "clock": _draw_icon_clock(screen, sub_rect.centerx, icon_cy, 12)
            elif icon_type == "nodes": _draw_icon_nodes(screen, sub_rect.centerx, icon_cy, 12)
            elif icon_type == "path": _draw_icon_path(screen, sub_rect.centerx, icon_cy, 12)
            
            label_lines = label.split('\n')
            for j, line in enumerate(label_lines):
                _text(screen, line, int(9), C_TEXT_GRAY, (sub_rect.centerx, icon_cy + 22 + j*12), bold=True)
            
            _text(screen, val, int(22), C_TEXT_CYAN, (sub_rect.centerx, sub_rect.bottom - 35), bold=True)
            _text(screen, unit, int(10), C_TEXT_GRAY, (sub_rect.centerx, sub_rect.bottom - 15))

# ==============================================================================
# FUNGSI UTAMA MENAMPILKAN UI
# ==============================================================================
def show_hasil(screen, data_percobaan):
    if screen is None:
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Pac-Man AI: Hasil Pengujian")
    w, h = screen.get_size()
    clock = pygame.time.Clock()

    scroll_y = 0
    scroll_speed = 40
    
    # Tombol Back dan Export
    # Ukuran disesuaikan agar terlihat seperti kotak persegi panjang
    btn_back_rect = pygame.Rect(30, 25, 80, 50)
    btn_export_rect = pygame.Rect(w - 250, 25, 220, 40)
    
    msg_simpan = ""
    msg_timer = 0

    card_w, card_h = 380, 500
    gap_x, gap_y = 30, 30
    top_margin = 100
    
    cols = max(1, (w - gap_x) // (card_w + gap_x))
    
    cards = []
    for i, data in enumerate(data_percobaan):
        row = i // cols
        col = i % cols
        total_w = (cols * card_w) + ((cols - 1) * gap_x)
        start_x = (w - total_w) // 2
        x = start_x + col * (card_w + gap_x)
        y = top_margin + row * (card_h + gap_y)
        cards.append(ExperimentCard(x, y, card_w, card_h, i+1, data))
        
    total_rows = (len(cards) + cols - 1) // cols
    content_height = top_margin + total_rows * (card_h + gap_y)
    max_scroll = max(0, content_height - h + 50)

    running = True
    while running:
        mouse_pos = pygame.mouse.get_pos()
        is_hover_export = btn_export_rect.collidepoint(mouse_pos)
        is_hover_back = btn_back_rect.collidepoint(mouse_pos)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "back" # Kembali ke menu utama
                elif event.key == pygame.K_DOWN:
                    scroll_y -= scroll_speed
                elif event.key == pygame.K_UP:
                    scroll_y += scroll_speed
            elif event.type == pygame.MOUSEWHEEL:
                scroll_y += event.y * scroll_speed
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Klik Tombol Back
                if btn_back_rect.collidepoint(event.pos):
                    return "back"
                
                # Klik Tombol Export
                if btn_export_rect.collidepoint(event.pos):
                    if not data_percobaan:
                        msg_simpan = "Gagal: Tidak ada data untuk disimpan."
                        msg_timer = 180
                    else:
                        sukses, pesan = export_to_csv(data_percobaan)
                        if sukses:
                            msg_simpan = f"Berhasil disimpan ke: {pesan}"
                            msg_timer = 180 
                        else:
                            msg_simpan = f"Gagal: {pesan}"
                            msg_timer = 180

        scroll_y = max(-max_scroll, min(0, scroll_y))

        screen.fill(C_BG)
        _text(screen, "HASIL PENGUJIAN PAC-MAN", int(28), C_TITLE, (w // 2, 45), bold=True)
        
        # =====================================================================
        # GAMBAR TOMBOL BACK (Desain Baru Sesuai Gambar)
        # =====================================================================
        back_bg_color = C_BACK_BG_HOVER if is_hover_back else C_BACK_BG
        
        # 1. Background Kotak Ungu
        pygame.draw.rect(screen, back_bg_color, btn_back_rect, border_radius=12)
        # 2. Border Putih
        pygame.draw.rect(screen, C_BACK_BORDER, btn_back_rect, 3, border_radius=12)
        
        # 3. Gambar Ikon Panah
        cx, cy = btn_back_rect.center
        # Garis horizontal (badan panah)
        pygame.draw.line(screen, C_BACK_ARROW, (cx - 12, cy), (cx + 12, cy), 4)
        # Garis diagonal atas (kepala panah)
        pygame.draw.line(screen, C_BACK_ARROW, (cx - 12, cy), (cx - 2, cy - 10), 4)
        # Garis diagonal bawah (kepala panah)
        pygame.draw.line(screen, C_BACK_ARROW, (cx - 12, cy), (cx - 2, cy + 10), 4)

        # =====================================================================
        # GAMBAR TOMBOL EXPORT
        # =====================================================================
        btn_color = C_BTN_EXPORT_HOVER if is_hover_export else C_BTN_EXPORT
        pygame.draw.rect(screen, btn_color, btn_export_rect, border_radius=8)
        pygame.draw.rect(screen, C_TEXT_CYAN, btn_export_rect, 2, border_radius=8)
        _text(screen, "SIMPAN KE EXCEL", int(14), C_TITLE, btn_export_rect.center, bold=True)

        if msg_timer > 0:
            msg_timer -= 1
            _text(screen, msg_simpan, int(16), C_MSG_SUCCESS, (w // 2, 90), bold=True)

        for card in cards:
            card.draw(screen, scroll_y)

        if max_scroll > 0:
            bar_h = max(50, int(h * (h / content_height)))
            bar_y = int((scroll_y / -max_scroll) * (h - bar_h)) if max_scroll > 0 else 0
            pygame.draw.rect(screen, (50, 50, 70), (w - 15, 10, 10, h - 20), border_radius=5)
            pygame.draw.rect(screen, C_TEXT_CYAN, (w - 15, bar_y + 10, 10, bar_h), border_radius=5)

        pygame.display.flip()
        clock.tick(FPS)
        
if __name__ == "__main__":
    pygame.init()
    scr = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    show_hasil(scr, [])
    pygame.quit()