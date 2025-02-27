import pygame
import pygame.gfxdraw
import socket
import sys
import ctypes
from ctypes import wintypes
import math
import threading
import time

# Fattore di supersampling
SUPERSAMPLE = 2

# Risoluzione finestra finale
WIDTH, HEIGHT = 400, 200
# Risoluzione di rendering (off-screen)
R_WIDTH, R_HEIGHT = WIDTH * SUPERSAMPLE, HEIGHT * SUPERSAMPLE

# -------------------------
# Impostazioni UDP
# -------------------------
UDP_IP = "127.0.0.1"
UDP_CMD_PORT = 5005       # Porta per inviare comandi (open/close)
UDP_FEEDBACK_PORT = 5006  # Porta per ricevere i dati (torque e position)

pygame.init()

# Crea la finestra finale (display)
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("SixthFingerHostWin GUI")

# Surface di rendering ad alta risoluzione
render_surface = pygame.Surface((R_WIDTH, R_HEIGHT))

# -------------------------
# Creazione della regione arrotondata per la finestra (usa le dimensioni finali)
# -------------------------
hwnd = None
if sys.platform == "win32":
    wm_info = pygame.display.get_wm_info()
    hwnd = wm_info.get("window")
    if hwnd:
        corner_radius = 30  # Raggio in pixel della finestra finale (non scalato)
        rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, WIDTH, HEIGHT, corner_radius, corner_radius)
        ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)

# -------------------------
# Definizione colori e stili (Apple-like)
# -------------------------
BACKGROUND_COLOR = (245, 245, 245)       # Grigio chiaro
# Bottoni: sfondo blu #8080FF, hover e pressed leggermente più scuri, testo bianco
BUTTON_COLOR = (128, 128, 255)           # #8080FF
BUTTON_HOVER_COLOR = (112, 112, 223)
BUTTON_PRESSED_COLOR = (96, 96, 192)
BORDER_COLOR = (160, 160, 160)
TEXT_COLOR = (255, 255, 255)             # Bianco
SHADOW_COLOR = (200, 200, 200)

# Parametri (scalati per il render_surface)
button_width = 120 * SUPERSAMPLE
button_height = 50 * SUPERSAMPLE
padding = 20 * SUPERSAMPLE

# Posizionamento dei pulsanti (scalati)
close_button_rect = pygame.Rect(padding, (R_HEIGHT // 3) - (button_height // 2), button_width, button_height)
open_button_rect = pygame.Rect(R_WIDTH - button_width - padding, (R_HEIGHT // 3) - (button_height // 2), button_width, button_height)

# -------------------------
# Window Controls in stile macOS (solo controlli rosso e giallo)
# -------------------------
# Cerchi più piccoli e spostati più dall'angolo
CONTROL_RADIUS = 8 * SUPERSAMPLE
CONTROL_GAP = 10 * SUPERSAMPLE
control_red_center = (20 * SUPERSAMPLE, 20 * SUPERSAMPLE)
control_yellow_center = (control_red_center[0] + 2 * CONTROL_RADIUS + CONTROL_GAP, control_red_center[1])
CONTROL_RED = (255, 95, 86)
CONTROL_YELLOW = (255, 189, 46)

def is_point_in_circle(point, center, radius):
    return math.hypot(point[0] - center[0], point[1] - center[1]) <= radius

def draw_aa_circle(surface, center, radius, color):
    pygame.gfxdraw.filled_circle(surface, center[0], center[1], radius, color)
    pygame.gfxdraw.aacircle(surface, center[0], center[1], radius, color)

def draw_window_controls(surface):
    draw_aa_circle(surface, control_red_center, CONTROL_RADIUS, CONTROL_RED)
    draw_aa_circle(surface, control_yellow_center, CONTROL_RADIUS, CONTROL_YELLOW)

def handle_window_controls_event(event):
    if event.type == pygame.MOUSEBUTTONUP:
        # Per i controlli, convertiamo le coordinate dell'evento in quelle del render_surface
        pos = (event.pos[0] * SUPERSAMPLE, event.pos[1] * SUPERSAMPLE)
        if is_point_in_circle(pos, control_red_center, CONTROL_RADIUS):
            pygame.quit()
            sys.exit()
        elif is_point_in_circle(pos, control_yellow_center, CONTROL_RADIUS):
            pygame.display.iconify()
            return True
    return False

def draw_aa_rounded_rect(surface, rect, color, radius):
    rect = pygame.Rect(rect)
    temp_surface = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.gfxdraw.filled_circle(temp_surface, radius, radius, radius, color)
    pygame.gfxdraw.filled_circle(temp_surface, rect.width - radius - 1, radius, radius, color)
    pygame.gfxdraw.filled_circle(temp_surface, radius, rect.height - radius - 1, radius, color)
    pygame.gfxdraw.filled_circle(temp_surface, rect.width - radius - 1, rect.height - radius - 1, radius, color)
    pygame.draw.rect(temp_surface, color, (radius, 0, rect.width - 2 * radius, rect.height))
    pygame.draw.rect(temp_surface, color, (0, radius, rect.width, rect.height - 2 * radius))
    surface.blit(temp_surface, rect.topleft)

def draw_rounded_button(surface, rect, text, is_hovered=False, is_pressed=False):
    if is_pressed:
        color = BUTTON_PRESSED_COLOR
    elif is_hovered:
        color = BUTTON_HOVER_COLOR
    else:
        color = BUTTON_COLOR

    shadow_offset = 3 * SUPERSAMPLE
    shadow_rect = rect.copy()
    shadow_rect.x += shadow_offset
    shadow_rect.y += shadow_offset
    draw_aa_rounded_rect(surface, shadow_rect, SHADOW_COLOR, 15 * SUPERSAMPLE)
    draw_aa_rounded_rect(surface, rect, color, 15 * SUPERSAMPLE)
    pygame.draw.rect(surface, BORDER_COLOR, rect, 2, border_radius=15 * SUPERSAMPLE)
    
    text_surface = font.render(text, True, TEXT_COLOR)
    text_rect = text_surface.get_rect(center=rect.center)
    surface.blit(text_surface, text_rect)

# -------------------------
# Drag della finestra (solo su Windows)
# -------------------------
dragging = False
drag_offset = (0, 0)

def get_window_rect():
    rect = wintypes.RECT()
    ctypes.windll.user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top)

def get_cursor_pos():
    class POINT(ctypes.Structure):
        _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]
    pt = POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return (pt.x, pt.y)

def set_window_pos(x, y):
    if hwnd:
        SWP_NOSIZE = 0x0001
        SWP_NOZORDER = 0x0004
        ctypes.windll.user32.SetWindowPos(hwnd, None, x, y, 0, 0, SWP_NOSIZE | SWP_NOZORDER)

# -------------------------
# Font Apple-like (con font embeddato)
# -------------------------
import sys, os
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

try:
    font = pygame.font.Font(resource_path("SF-Pro-Display-Regular.otf"), 28 * SUPERSAMPLE)
except Exception as e:
    print("Errore nel caricamento del font:", e)
    font = pygame.font.SysFont("Arial", 28 * SUPERSAMPLE)

# -------------------------
# Socket UDP per i comandi
# -------------------------
udp_cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
def send_command(command):
    try:
        udp_cmd_sock.sendto(command.encode('utf-8'), (UDP_IP, UDP_CMD_PORT))
        print(f"Inviato comando: {command}")
    except Exception as e:
        print(f"Errore durante l'invio del comando: {e}")

# -------------------------
# Graph Data: Lista per i valori di position ricevuti via UDP
# -------------------------
position_data = []       # Lista di valori interi (position)
max_data_points = 100    # Numero massimo di punti visualizzati
data_lock = threading.Lock()

def udp_feedback_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_FEEDBACK_PORT))
    print(f"Ascolto dati UDP su {UDP_IP}:{UDP_FEEDBACK_PORT}")
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            decoded = data.decode('utf-8').strip()
            tokens = decoded.split()
            if len(tokens) >= 2:
                pos_value = int(tokens[1])
            else:
                pos_value = int(tokens[0])
            with data_lock:
                position_data.append(pos_value)
                if len(position_data) > max_data_points:
                    position_data.pop(0)
        except Exception as e:
            print("Errore nel listener UDP feedback:", e)

def draw_graph(surface):
    # Area grafico: più alto e posizionato più in basso
    graph_rect = pygame.Rect(padding, R_HEIGHT - 140, R_WIDTH - 2 * padding, 120)
    draw_aa_rounded_rect(surface, graph_rect, (255, 255, 255), 10 * SUPERSAMPLE)
    pygame.draw.rect(surface, BORDER_COLOR, graph_rect, 2, border_radius=10 * SUPERSAMPLE)
    
    with data_lock:
        data = position_data.copy()
    if len(data) < 2:
        return

    min_val = 0
    max_val = 100
    points = []
    for i, value in enumerate(data):
        clamped = max(min_val, min(value, max_val))
        x = graph_rect.left + (i / (max_data_points - 1)) * graph_rect.width
        y = graph_rect.bottom - 5 * SUPERSAMPLE - ((clamped - min_val) / (max_val - min_val)) * (graph_rect.height - 10 * SUPERSAMPLE)
        points.append((int(x), int(y)))
    
    old_clip = surface.get_clip()
    surface.set_clip(graph_rect)
    if len(points) >= 2:
        pygame.draw.lines(surface, (0, 0, 0), False, points, 3)
    surface.set_clip(old_clip)

def main():
    global dragging, drag_offset
    clock = pygame.time.Clock()
    running = True

    udp_feedback_thread = threading.Thread(target=udp_feedback_listener, daemon=True)
    udp_feedback_thread.start()

    while running:
        render_surface.fill(BACKGROUND_COLOR)
        draw_window_controls(render_surface)

        mouse_pos = pygame.mouse.get_pos()  # Coordinate della finestra finale (non scalate)
        mouse_pressed = pygame.mouse.get_pressed()[0]

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if handle_window_controls_event(event):
                continue

            if event.type == pygame.MOUSEBUTTONUP:
                dragging = False
                # Per i pulsanti, convertiamo le coordinate per il render_surface
                scaled_pos = (event.pos[0] * SUPERSAMPLE, event.pos[1] * SUPERSAMPLE)
                if close_button_rect.collidepoint(scaled_pos):
                    send_command("CLOSE")
                elif open_button_rect.collidepoint(scaled_pos):
                    send_command("OPEN")

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Per collisioni, usiamo le coordinate scalate; per il drag usiamo quelle originali
                scaled_pos = (event.pos[0] * SUPERSAMPLE, event.pos[1] * SUPERSAMPLE)
                if not (close_button_rect.collidepoint(scaled_pos) or 
                        open_button_rect.collidepoint(scaled_pos) or
                        is_point_in_circle(scaled_pos, control_red_center, CONTROL_RADIUS) or
                        is_point_in_circle(scaled_pos, control_yellow_center, CONTROL_RADIUS)):
                    # Usa event.pos (non scalato) per il drag
                    drag_offset = event.pos
                    dragging = True

            if event.type == pygame.MOUSEMOTION and dragging and sys.platform == "win32":
                global_cursor = get_cursor_pos()
                new_x = global_cursor[0] - drag_offset[0]
                new_y = global_cursor[1] - drag_offset[1]
                set_window_pos(new_x, new_y)

        # Per i pulsanti, usiamo le coordinate scalate
        scaled_mouse_pos = (mouse_pos[0] * SUPERSAMPLE, mouse_pos[1] * SUPERSAMPLE)
        close_hover = close_button_rect.collidepoint(scaled_mouse_pos)
        open_hover = open_button_rect.collidepoint(scaled_mouse_pos)
        close_pressed = close_hover and mouse_pressed
        open_pressed = open_hover and mouse_pressed

        draw_rounded_button(render_surface, close_button_rect, "Close", is_hovered=close_hover, is_pressed=close_pressed)
        draw_rounded_button(render_surface, open_button_rect, "Open", is_hovered=open_hover, is_pressed=open_pressed)

        draw_graph(render_surface)

        final_surface = pygame.transform.smoothscale(render_surface, (WIDTH, HEIGHT))
        screen.blit(final_surface, (0, 0))
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
