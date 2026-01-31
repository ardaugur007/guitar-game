import pygame
import pyaudio
import numpy as np
import aubio
import random
import sys
import math

# --- AYARLAR ---
BUFFER_SIZE = 1024
CHANNELS = 2          # Focusrite için Stereo
RATE = 48000          # Focusrite için 48k
PITCH_METHOD = "default"
TOLERANCE = 0.8
VOLUME_THRESH = 0.0001 # Hassas ayar

# --- RENK PALETİ (DEEP SPACE) ---
BG_DARK = (5, 5, 15)        # En koyu uzay
BG_NEBULA = (20, 10, 30)    # Uzak nebula renkleri
WHITE = (255, 255, 255)
NEON_RED = (255, 50, 80)    # Düşman Rengi 1
NEON_BLUE = (0, 180, 255)   # Düşman Rengi 2
NEON_GREEN = (50, 255, 100) # Skor/Vuruş
HERO_PURPLE = (150, 0, 255) # Ana Gemi Rengi
HERO_CYAN = (0, 255, 255)   # Gemi Motor/Kokpit Detayı
YELLOW = (255, 230, 50)     # Duyulan nota

# --- MÜZİK TEORİSİ ---
STANDARD_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
GAME_NOTES = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]
ENHARMONIC_MAP = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#"}

def hz_to_note(pitch):
    if pitch == 0: return None
    midi_num = 12 * (np.log2(pitch / 440.0)) + 69
    midi_num = round(midi_num)
    if midi_num < 0 or midi_num > 127: return None
    return STANDARD_NOTES[midi_num % 12]

# --- BAŞLATMA ---
pygame.init()
WIDTH, HEIGHT = 900, 700
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Guitar Space Shooter V3")

font_large = pygame.font.SysFont("Arial Black", 60) 
font_medium = pygame.font.SysFont("Arial Black", 24) 
font_small = pygame.font.SysFont("Consolas", 16)
clock = pygame.time.Clock()

# --- SES GİRİŞİ ---
p = pyaudio.PyAudio()
try:
    stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, input=True, input_device_index=8, frames_per_buffer=BUFFER_SIZE)
except Exception:
    try: 
        stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, input=True, input_device_index=44, frames_per_buffer=BUFFER_SIZE)
    except: 
        print("Ses kartı başlatılamadı!")
        sys.exit()

p_detect = aubio.pitch(PITCH_METHOD, BUFFER_SIZE * 2, BUFFER_SIZE, RATE)
p_detect.set_unit("Hz")
p_detect.set_tolerance(TOLERANCE)

# --- GELİŞMİŞ ÇİZİM FONKSİYONLARI ---

def draw_hero_ship(surface, x, y):
    """Detaylı ana oyuncu gemisi çizimi"""
    # 1. Motor Alevleri (Arkada yanıp sönen)
    thrust_len = random.randint(15, 25)
    pygame.draw.polygon(surface, HERO_CYAN, [(x-15, y+35), (x-25, y+35+thrust_len), (x-5, y+35+thrust_len)])
    pygame.draw.polygon(surface, HERO_CYAN, [(x+15, y+35), (x+25, y+35+thrust_len), (x+5, y+35+thrust_len)])
    
    # 2. Ana Gövde (Koyu Mor)
    body_points = [(x, y-50), (x-30, y+20), (x, y+35), (x+30, y+20)]
    pygame.draw.polygon(surface, (80, 0, 120), body_points) # Koyu iç renk
    pygame.draw.polygon(surface, HERO_PURPLE, body_points, 4) # Parlak dış hat

    # 3. Kanatlar
    pygame.draw.polygon(surface, HERO_PURPLE, [(x-30, y+10), (x-50, y+40), (x-30, y+35)])
    pygame.draw.polygon(surface, HERO_PURPLE, [(x+30, y+10), (x+50, y+40), (x+30, y+35)])

    # 4. Kokpit (Cam kısmı)
    pygame.draw.ellipse(surface, HERO_CYAN, (x-10, y-20, 20, 30))
    pygame.draw.ellipse(surface, WHITE, (x-5, y-15, 10, 15)) # Parlama

def draw_enemy_ship(surface, x, y, color, note_text):
    """Notayı taşıyan uzaylı gemisi çizimi"""
    points = [(x, y+40), (x-35, y-20), (x-15, y-30), (x+15, y-30), (x+35, y-20)]
    
    dark_color = (color[0]//2, color[1]//2, color[2]//2)
    pygame.draw.polygon(surface, dark_color, points)
    pygame.draw.polygon(surface, color, points, 4)
    
    pygame.draw.circle(surface, color, (x-25, y-25), 8)
    pygame.draw.circle(surface, color, (x+25, y-25), 8)

    text_surf = font_medium.render(note_text, True, WHITE)
    s = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 6))
    s.set_alpha(150)
    s.fill((0,0,0))
    surface.blit(s, (x - s.get_width()//2, y - 15))
    text_rect = text_surf.get_rect(center=(x, y))
    surface.blit(text_surf, text_rect)

class LaserBeam:
    def __init__(self, start_pos, end_pos, color):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.color = color
        self.life = 12
        self.max_life = 12
        self.width = 12

    def draw(self):
        if self.life > 0:
            progress = self.life / self.max_life
            current_width = int(self.width * progress)
            pygame.draw.line(screen, self.color, self.start_pos, self.end_pos, current_width)
            if current_width > 4:
                 pygame.draw.line(screen, WHITE, self.start_pos, self.end_pos, current_width // 2)
            radius = (self.max_life - self.life) * 3
            pygame.draw.circle(screen, self.color, self.end_pos, radius, 4)
            self.life -= 1

class Enemy:
    def __init__(self):
        self.display_note = random.choice(GAME_NOTES)
        self.real_note = ENHARMONIC_MAP.get(self.display_note, self.display_note)
        self.x = random.randint(50, WIDTH - 100)
        self.y = -60
        self.speed = 2.0 
        self.color = NEON_BLUE if "b" in self.display_note else NEON_RED

    def move(self): self.y += self.speed
    def draw(self): draw_enemy_ship(screen, self.x, int(self.y), self.color, self.display_note)

# --- YILDIZ SİSTEMİ ---
stars = []
for _ in range(100): 
    stars.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3)])

# --- OYUN DEĞİŞKENLERİ ---
enemies = []
lasers = [] 
spawn_timer = 0
score = 0
player_pos = (WIDTH // 2, HEIGHT - 60) 
running = True

print("Guitar Space Shooter V3.1 (Fixed) Başlatıldı!")

while running:
    # --- ARKA PLAN ve YILDIZLAR ---
    screen.fill(BG_DARK)
    pygame.draw.rect(screen, BG_NEBULA, (0, HEIGHT//2, WIDTH, HEIGHT//2))

    for star in stars:
        star[1] += star[2]
        if star[1] > HEIGHT:
            star[1] = -5
            star[0] = random.randint(0, WIDTH)
        
        # DÜZELTME BURADA: Renk hesaplarken 255 sınırını kontrol ediyoruz
        size = star[2]
        brightness = int(min(255, star[2] * 80))
        # Blue bileşeni 255'i geçmesin diye min() kullandık
        b_val = min(255, brightness + 50)
        
        pygame.draw.circle(screen, (brightness, brightness, b_val), (star[0], star[1]), size)

    # --- SES İŞLEME ---
    current_note_detected = None
    debug_volume = 0.0
    debug_pitch = 0.0
    try:
        audio_data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
        samples = np.frombuffer(audio_data, dtype=np.float32)
        if CHANNELS == 2:
            left = samples[0::2]; right = samples[1::2]
            min_len = min(len(left), len(right))
            samples = (left[:min_len] + right[:min_len]) / 2
        
        pitch = p_detect(samples)[0]
        volume = np.sum(samples**2) / len(samples)
        debug_volume = volume; debug_pitch = pitch
        
        if volume > VOLUME_THRESH:
            current_note_detected = hz_to_note(pitch)    
    except: pass

    # --- OYUN MANTIĞI ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    spawn_timer += 1
    if spawn_timer > 90:
        enemies.append(Enemy())
        spawn_timer = 0

    hit_happened = False
    if current_note_detected:
        for enemy in enemies:
            if enemy.real_note == current_note_detected:
                nose_pos = (player_pos[0], player_pos[1] - 50)
                lasers.append(LaserBeam(nose_pos, (enemy.x, enemy.y), enemy.color))
                
                pygame.draw.circle(screen, WHITE, (enemy.x, int(enemy.y)), 80)
                pygame.draw.circle(screen, enemy.color, (enemy.x, int(enemy.y)), 70, 10)
                
                enemies.remove(enemy)
                score += 1
                hit_happened = True
                break 

    # --- ÇİZİMLER ---
    
    for laser in lasers: laser.draw()
    lasers = [l for l in lasers if l.life > 0]

    # DÜZELTME BURADA: draw_hero_ship fonksiyonunu doğru isimle çağırdık
    draw_hero_ship(screen, player_pos[0], player_pos[1])

    for enemy in enemies:
        enemy.move()
        enemy.draw()
        if enemy.y > HEIGHT + 50:
            enemies.remove(enemy)
            score = max(0, score - 5)

    # --- ARAYÜZ (UI) ---
    score_text = font_large.render(str(score), True, NEON_GREEN)
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 10))
    screen.blit(font_small.render("SKOR", True, WHITE), (WIDTH//2 - 20, 70))

    if hit_happened:
        pygame.draw.circle(screen, NEON_GREEN, (80, HEIGHT-80), 65, 4)
        indicator_color = NEON_GREEN
    else:
        indicator_color = YELLOW
    
    note_str = current_note_detected if current_note_detected else "--"
    note_surf = font_large.render(note_str, True, indicator_color)
    screen.blit(note_surf, (80 - note_surf.get_width()//2, HEIGHT - 110))
    screen.blit(font_small.render("DUYULAN", True, WHITE), (50, HEIGHT - 40))

    vol_c = NEON_RED if debug_volume < VOLUME_THRESH else NEON_GREEN
    screen.blit(font_small.render(f"Vol: {debug_volume:.5f}", True, vol_c), (WIDTH - 160, HEIGHT - 40))

    pygame.display.flip()
    clock.tick(60)

stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()