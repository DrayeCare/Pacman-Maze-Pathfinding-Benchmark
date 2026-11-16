import pygame
from core import config
from tampilan.ui_mulai import show_mulai
from tampilan.ui_setting import show_setting, _font
from tampilan.ui_info import show_hasil

MENU_SIZE = (680, 560)
FPS = getattr(config, "FPS", 60)

COLOR_BG = getattr(config, "COLOR_BG", (0, 0, 0))
COLOR_PACMAN = getattr(config, "COLOR_PACMAN", (255, 220, 0))
C_MENU_BG = (8, 8, 20)
C_TITLE = (110, 220, 255)
C_SUBTITLE = (190, 190, 190)
C_TEXT = (235, 235, 245)
C_MUTED = (140, 140, 170)
C_LINE = (60, 60, 100)
C_BTN = (40, 40, 70)
C_BTN_HOVER = (62, 62, 110)

MENU_ITEMS = [
    ("mulai", "MULAI"),
    ("setting", "SETTING"),
    ("info", "INFO"),
    ("quit", "QUIT"),
]

def _text(screen, msg, size, color, center, bold=False):
    surf = _font(size, bold).render(str(msg), True, color)
    screen.blit(surf, surf.get_rect(center=center))

class Button:
    def __init__(self, rect, label, value, font_size=22):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.value = value
        self.font_size = font_size

    def draw(self, screen):
        hover = self.rect.collidepoint(pygame.mouse.get_pos())
        pygame.draw.rect(screen, C_BTN_HOVER if hover else C_BTN, self.rect, border_radius=10)
        pygame.draw.rect(screen, C_LINE, self.rect, 2, border_radius=10)
        _text(screen, self.label, self.font_size, C_TEXT, self.rect.center, bold=True)

    def clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and event.button == 1
                and self.rect.collidepoint(event.pos))

def show_main_menu(screen=None):
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
    pygame.display.set_caption("Pac-Man AI: BFS vs A*")
    w, h = screen.get_size()
    clock = pygame.time.Clock()

    s = h / MENU_SIZE[1]
    btn_w, btn_h, gap = int(320 * s), int(60 * s), int(20 * s)
    total_h = 4 * btn_h + 3 * gap
    top = int(h * 0.36)
    top = min(top, h - total_h - int(30 * s))  # jaga agar tombol tidak keluar layar
    buttons = [
        Button((w // 2 - btn_w // 2, top + i * (btn_h + gap), btn_w, btn_h),
               label, value, font_size=int(24 * s))
        for i, (value, label) in enumerate(MENU_ITEMS)
    ]
    keymap = {pygame.K_1: "mulai", pygame.K_2: "setting",
              pygame.K_3: "info", pygame.K_4: "quit"}

    title_size, sub_size = int(64 * s), int(20 * s)
    title_y, sub_y = int(h * 0.14), int(h * 0.14) + int(58 * s)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return "quit"
                if event.key in keymap:
                    return keymap[event.key]
            for b in buttons:
                if b.clicked(event):
                    return b.value

        screen.fill(C_MENU_BG)
        _text(screen, "GHOST vs PAC-MAN", title_size, C_TITLE, (w // 2, title_y), bold=True)
        _text(screen, "BFS  |  A*  -  AI Search Comparison", sub_size, C_SUBTITLE,
              (w // 2, sub_y), bold=True)
        for b in buttons:
            b.draw(screen)
        pygame.display.flip()
        clock.tick(FPS)

def run():
    pygame.init()
    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    data_hasil_percobaan = []

    while True:
        pilihan = show_main_menu(screen)

        if pilihan == "quit":
            break

        if pilihan == "mulai":
            hasil = show_mulai(screen)
            if hasil == "quit":
                break
            if hasil == "back":
                continue
            print("Pengaturan game:", hasil)
            continue

        if pilihan == "setting":
            hasil = show_setting(screen)
            if hasil == "quit":
                break
            continue

        if pilihan == "info":
            if not data_hasil_percobaan:
                data_dummy = [
                    {"maze_id": 1, "nama_map": "Maze Mudah - Banyak Jalur", "kondisi": "Pac-Man Diam", "waktu": 0.342, "simpul": 87, "panjang": 15},
                    {"maze_id": 2, "nama_map": "Maze Sedang - Loop", "kondisi": "Pac-Man Diam", "waktu": 0.512, "simpul": 120, "panjang": 22},
                    {"maze_id": 3, "nama_map": "Maze Sulit - Belokan", "kondisi": "Pac-Man Bergerak", "waktu": 1.234, "simpul": 340, "panjang": 45},
                ]
                show_hasil(screen, data_dummy)
            else:
                show_hasil(screen, data_hasil_percobaan)
                
            continue

    pygame.quit()

if __name__ == "__main__":
    run()