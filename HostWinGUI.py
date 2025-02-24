import pygame
import socket
import sys
import ctypes
import math

# -------------------------
# Impostazioni UDP
# -------------------------
UDP_IP = "127.0.0.1"
UDP_CMD_PORT = 5005

# -------------------------
# Inizializzazione Pygame e finestra borderless
# -------------------------
pygame.init()

WIDTH, HEIGHT = 400, 300
# Crea una finestra senza cornice (NOFRAME)
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("SixthFingerHostWin GUI")

# Applica una regione arrotondata alla finestra (solo su Windows)
if sys.platform == "win32":
    wm_info = pygame.display.get_wm_info()
    hwnd = wm_info.get("window")
    if hwnd:
        corner_radius = 30
        rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, WIDTH, HEIGHT, corner_radius, corner_radius)
        ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)

# -------------------------
# Definizione colori e stili (Apple-like)
# -------------------------
BACKGROUND_COLOR = (245, 245, 245)       # Grigio chiaro
BUTTON_COLOR = (230, 230, 230)           # Grigio morbido
BUTTON_HOVER_COLOR = (210, 210, 210)
BUTTON_PRESSED_COLOR = (190, 190, 190)
BORDER_COLOR = (160, 160, 160)
TEXT_COLOR = (50, 50, 50)
SHADOW_COLOR = (200, 200, 200)

# Parametri dei pulsanti principali
button_width = 120
button_height = 50
padding = 20

close_button_rect = pygame.Rect(padding, HEIGHT // 2 - button_height // 2, button_width, button_height)
open_button_rect = pygame.Rect(WIDTH - button_width - padding, HEIGHT // 2 - button_height // 2, button_width, button_height)

# -------------------------
# Window Controls in stile macOS
# -------------------------
# Dimensioni e posizioni dei cerchietti in alto a sinistra
CONTROL_RADIUS = 10
CONTROL_GAP = 5
# Posizione del primo cerchio (rosso) - in alto a sinistra, con margine
control_red_center = (15, 15)
control_yellow_center = (control_red_center[0] + 2*CONTROL_RADIUS + CONTROL_GAP, control_red_center[1])
control_green_center = (control_yellow_center[0] + 2*CONTROL_RADIUS + CONTROL_GAP, control_red_center[1])
# Colori tipici macOS
CONTROL_RED = (255, 95, 86)
CONTROL_YELLOW = (255, 189, 46)
CONTROL_GREEN = (39, 201, 63)

def is_point_in_circle(point, center, radius):
    return math.hypot(point[0]-center[0], point[1]-center[1]) <= radius

def draw_window_controls():
    """Disegna i tre cerchietti di controllo in alto a sinistra."""
    pygame.draw.circle(screen, CONTROL_RED, control_red_center, CONTROL_RADIUS)
    pygame.draw.circle(screen, CONTROL_YELLOW, control_yellow_center, CONTROL_RADIUS)
    pygame.draw.circle(screen, CONTROL_GREEN, control_green_center, CONTROL_RADIUS)

def handle_window_controls_event(event):
    """Controlla se il click riguarda i controlli della finestra e ne gestisce l'azione.
       Ritorna True se l'evento è stato consumato.
    """
    if event.type == pygame.MOUSEBUTTONUP:
        pos = event.pos
        if is_point_in_circle(pos, control_red_center, CONTROL_RADIUS):
            pygame.quit()
            sys.exit()
        elif is_point_in_circle(pos, control_yellow_center, CONTROL_RADIUS):
            pygame.display.iconify()  # minimizza la finestra
            return True
        elif is_point_in_circle(pos, control_green_center, CONTROL_RADIUS):
            # Tenta di passare al fullscreen (toggle)
            pygame.display.toggle_fullscreen()
            return True
    return False

# -------------------------
# Font Apple-like
# -------------------------
# Invece di usare pygame.font.match_font, carica direttamente il file .otf:
try:
    font = pygame.font.Font("SF-Pro-Display-Regular.otf", 28)
except Exception as e:
    print("Errore nel caricamento del font:", e)
    font = pygame.font.SysFont("Arial", 28)

# -------------------------
# Socket UDP per l'invio dei comandi
# -------------------------
udp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_command(command):
    """Invia il comando specificato tramite UDP."""
    try:
        udp_sock.sendto(command.encode('utf-8'), (UDP_IP, UDP_CMD_PORT))
        print(f"Inviato comando: {command}")
    except Exception as e:
        print(f"Errore durante l'invio del comando: {e}")

def draw_rounded_button(rect, text, is_hovered=False, is_pressed=False):
    """
    Disegna un pulsante arrotondato con ombra, bordo e testo centrato.
    """
    if is_pressed:
        color = BUTTON_PRESSED_COLOR
    elif is_hovered:
        color = BUTTON_HOVER_COLOR
    else:
        color = BUTTON_COLOR

    shadow_offset = 3
    shadow_rect = rect.copy()
    shadow_rect.x += shadow_offset
    shadow_rect.y += shadow_offset
    pygame.draw.rect(screen, SHADOW_COLOR, shadow_rect, border_radius=15)

    pygame.draw.rect(screen, color, rect, border_radius=15)
    pygame.draw.rect(screen, BORDER_COLOR, rect, 2, border_radius=15)

    text_surface = font.render(text, True, TEXT_COLOR)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)

def main():
    clock = pygame.time.Clock()
    running = True

    while running:
        screen.fill(BACKGROUND_COLOR)
        # Disegna i controlli della finestra
        draw_window_controls()
        
        mouse_pos = pygame.mouse.get_pos()
        mouse_pressed = pygame.mouse.get_pressed()[0]

        # Controlla se il click riguarda i window controls
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Gestisci prima gli eventi dei controlli finestra
            if handle_window_controls_event(event):
                continue
            # Altri eventi
            if event.type == pygame.MOUSEBUTTONUP:
                if close_button_rect.collidepoint(event.pos):
                    send_command("CLOSE")
                elif open_button_rect.collidepoint(event.pos):
                    send_command("OPEN")
        
        # Determina hover e pressed per i pulsanti "CLOSE" e "OPEN"
        close_hover = close_button_rect.collidepoint(mouse_pos)
        open_hover = open_button_rect.collidepoint(mouse_pos)
        close_pressed = close_hover and mouse_pressed
        open_pressed = open_hover and mouse_pressed

        draw_rounded_button(close_button_rect, "Close", is_hovered=close_hover, is_pressed=close_pressed)
        draw_rounded_button(open_button_rect, "Open", is_hovered=open_hover, is_pressed=open_pressed)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
