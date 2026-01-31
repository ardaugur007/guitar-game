import pygame
import pyaudio
import numpy as np
import aubio
import random
import sys
import math

# --- AYARLAR ---
BUFFER_SIZE = 1024
CHANNELS = 2          
RATE = 48000          
PITCH_METHOD = "default"
TOLERANCE = 0.8
VOLUME_THRESH = 0.0001 

# --- RENK PALETİ ---
BG_DARK = (5, 5, 15)       
BG_NEBULA = (20, 10, 30)   
WHITE = (255, 255, 255)
NEON_RED = (255, 50, 80)   
NEON_BLUE = (0, 180, 255)  
NEON_GREEN = (50, 255, 100) 
HERO_PURPLE = (150, 0, 255) 
HERO_CYAN = (0, 255, 255)   
YELLOW = (255, 230, 50)     
HEART_COLOR = (255, 0, 50)  # Can barı için kalp rengi

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
pygame.display.set_caption("Guitar Space Shooter: Full Game")

font_title = pygame.font.SysFont("Arial Black", 80)
font_large = pygame.font.SysFont("Arial Black", 50) 
font_medium = pygame.font.SysFont("Arial Black", 24) 
font_small = pygame.font.SysFont("Consolas", 18)
clock = pygame.time.Clock()

# --- SES GİRİŞİ ---
p = pyaudio.PyAudio()
try:
    stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, input=True, input_device_index=8, frames_per_buffer=BUFFER_SIZE)
except Exception:
    try: 
        stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, input=True, input_device_index=44, frames_per_buffer=BUFFER_SIZE)
    except: sys.exit()

p_detect = aubio.pitch(PITCH_METHOD, BUFFER_SIZE * 2, BUFFER_SIZE, RATE)
p_detect.set_unit("Hz")
p_detect.set_tolerance(TOLERANCE)

# --- ÇİZİM FONKSİYONLARI ---

def draw_heart(surface, x, y, size):
    """Can barı için kalp çizer"""
    points = [
        (x, y + size // 4),
        (x - size // 2, y - size // 4),
        (x - size // 4, y - size // 2),
        (x, y - size // 4),
        (x + size // 4, y - size // 2),
        (x + size // 2, y - size // 4),
    ]
    pygame.draw.polygon(surface, HEART_COLOR, points)

def draw_hero_ship(surface, x, y):
    thrust_len = random.randint(15, 25)
    pygame.draw.polygon(surface, HERO_CYAN, [(x-15, y+35), (x-25, y+35+thrust_len), (x-5, y+35+thrust_len)])
    pygame.draw.polygon(surface, HERO_CYAN, [(x+15, y+35), (x+25, y+35+thrust_len), (x+5, y+35+thrust_len)])
    
    body_points = [(x, y-50), (x-30, y+20), (x, y+35), (x+30, y+20)]
    pygame.draw.polygon(surface, (80, 0, 120), body_points) 
    pygame.draw.polygon(surface, HERO_PURPLE, body_points, 4) 

    pygame.draw.polygon(surface, HERO_PURPLE, [(x-30, y+10), (x-50, y+40), (x-30, y+35)])
    pygame.draw.polygon(surface, HERO_PURPLE, [(x+30, y+10), (x+50, y+40), (x+30, y+35)])

    pygame.draw.ellipse(surface, HERO_CYAN, (x-10, y-20, 20, 30))
    pygame.draw.ellipse(surface, WHITE, (x-5, y-15, 10, 15))

def draw_enemy_ship(surface, x, y, color, note_text):
    points = [(x, y+40), (x-35, y-20), (x-15, y-30), (x+15, y-30), (x+35, y-20)]
    dark_color = (color[0]//2, color[1]//2, color[2]//2)
    pygame.draw.polygon(surface, dark_color, points)
    pygame.draw.polygon(surface, color, points, 4)
    pygame.draw.circle(surface, color, (x-25, y-25), 8)
    pygame.draw.circle(surface, color, (x+25, y-25), 8)

    text_surf = font_medium.render(note_text, True, WHITE)
    s = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 6))
    s.set_alpha(150); s.fill((0,0,0))
    surface.blit(s, (x - s.get_width()//2, y - 15))
    text_rect = text_surf.get_rect(center=(x, y))
    surface.blit(text_surf, text_rect)

class LaserBeam:
    def __init__(self, start_pos, end_pos, color):
        self.start_pos = start_pos; self.end_pos = end_pos; self.color = color
        self.life = 12; self.max_life = 12; self.width = 12
    def draw(self):
        if self.life > 0:
            progress = self.life / self.max_life
            current_width = int(self.width * progress)
            pygame.draw.line(screen, self.color, self.start_pos, self.end_pos, current_width)
            if current_width > 4: pygame.draw.line(screen, WHITE, self.start_pos, self.end_pos, current_width // 2)
            pygame.draw.circle(screen, self.color, self.end_pos, (self.max_life - self.life) * 3, 4)
            self.life -= 1

class Enemy:
    def __init__(self):
        self.display_note = random.choice(GAME_NOTES)
        self.real_note = ENHARMONIC_MAP.get(self.display_note, self.display_note)
        self.x = random.randint(50, WIDTH - 100); self.y = -60
        self.speed = 2.0; self.color = NEON_BLUE if "b" in self.display_note else NEON_RED
    def move(self): self.y += self.speed
    def draw(self): draw_enemy_ship(screen, self.x, int(self.y), self.color, self.display_note)

# --- OYUN DURUMLARI (STATE MACHINE) ---
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2
game_state = STATE_MENU

# Değişkenler
enemies = []
lasers = []
stars = []
for _ in range(100): stars.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3)])

spawn_timer = 0
score = 0
lives = 3
combo = 0
player_pos = (WIDTH // 2, HEIGHT - 60)
running = True

def reset_game():
    global score, lives, combo, enemies, lasers, spawn_timer
    score = 0
    lives = 3
    combo = 0
    enemies = []
    lasers = []
    spawn_timer = 0

print("Guitar Space Shooter V4 - Full Game Başlatıldı!")

while running:
    # 1. Ortak Arka Plan Çizimi
    screen.fill(BG_DARK)
    pygame.draw.rect(screen, BG_NEBULA, (0, HEIGHT//2, WIDTH, HEIGHT//2))
    for star in stars:
        star[1] += star[2]
        if star[1] > HEIGHT: star[1] = -5; star[0] = random.randint(0, WIDTH)
        size = star[2]
        brightness = int(min(255, star[2] * 80))
        b_val = min(255, brightness + 50)
        pygame.draw.circle(screen, (brightness, brightness, b_val), (star[0], star[1]), size)

    # 2. Ses Analizi (Her durumda çalışmalı ki menüde de algılasın)
    current_note_detected = None
    volume = 0
    try:
        audio_data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
        samples = np.frombuffer(audio_data, dtype=np.float32)
        if CHANNELS == 2:
            left = samples[0::2]; right = samples[1::2]
            min_len = min(len(left), len(right))
            samples = (left[:min_len] + right[:min_len]) / 2
        
        pitch = p_detect(samples)[0]
        volume = np.sum(samples**2) / len(samples)
        
        if volume > VOLUME_THRESH:
            current_note_detected = hz_to_note(pitch)    
    except: pass

    # 3. Olay Döngüsü
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    # --- DURUM MAKİNESİ (STATE MACHINE) ---

    if game_state == STATE_MENU:
        # Menü Ekranı
        title_surf = font_title.render("GUITAR SHOOTER", True, HERO_CYAN)
        sub_surf = font_medium.render("Başlamak için herhangi bir notaya vur!", True, WHITE)
        
        # Yanıp sönen efekt
        alpha = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 255
        sub_surf.set_alpha(int(alpha))

        screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, HEIGHT//3))
        screen.blit(sub_surf, (WIDTH//2 - sub_surf.get_width()//2, HEIGHT//2))
        
        draw_hero_ship(screen, WIDTH//2, HEIGHT - 100)

        # Başlama Kontrolü (Gitar sesi gelirse)
        if volume > VOLUME_THRESH * 5: # Biraz daha sert vuruş istesin yanlışlıkla açılmasın
            reset_game()
            game_state = STATE_PLAYING

    elif game_state == STATE_PLAYING:
        # Oyun Mantığı
        spawn_timer += 1
        # Skor arttıkça zorluk artsın
        spawn_rate = max(40, 90 - (score // 10)) 
        
        if spawn_timer > spawn_rate:
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
                    
                    # Combo Sistemi
                    combo += 1
                    multiplier = 1 + (combo // 5) # Her 5 comboda çarpan artar
                    points = 10 * multiplier
                    score += points
                    
                    hit_happened = True
                    break 
            
            # Eğer nota çaldı ama kimseyi vuramadıysa combo sıfırlanır (Opsiyonel, şimdilik kapalı kalsın, çok zor olmasın)
            # if not hit_happened: combo = 0

        # Çizimler ve Hareket
        for laser in lasers: laser.draw()
        lasers = [l for l in lasers if l.life > 0]

        draw_hero_ship(screen, player_pos[0], player_pos[1])

        for enemy in enemies:
            enemy.move()
            enemy.draw()
            
            # Düşman kaçarsa
            if enemy.y > HEIGHT + 50:
                enemies.remove(enemy)
                lives -= 1
                combo = 0 # Can kaybedince combo gider
                # Kırmızı ekran flaşı efekti yapılabilir buraya
                
                if lives <= 0:
                    game_state = STATE_GAMEOVER

        # --- ARAYÜZ (HUD) ---
        # Sol Üst: Skor ve Combo
        score_surf = font_large.render(f"{score}", True, NEON_GREEN)
        screen.blit(score_surf, (20, 10))
        
        if combo > 1:
            multiplier = 1 + (combo // 5)
            combo_surf = font_medium.render(f"{combo} COMBO! (x{multiplier})", True, YELLOW)
            screen.blit(combo_surf, (20, 70))

        # Sağ Üst: Canlar
        for i in range(lives):
            draw_heart(screen, WIDTH - 40 - (i * 40), 40, 30)

        # Alt: Duyulan Nota
        if hit_happened:
            indicator_color = NEON_GREEN
        else:
            indicator_color = YELLOW
        
        note_str = current_note_detected if current_note_detected else "--"
        note_surf = font_large.render(note_str, True, indicator_color)
        screen.blit(note_surf, (80 - note_surf.get_width()//2, HEIGHT - 110))
        screen.blit(font_small.render("DUYULAN", True, WHITE), (50, HEIGHT - 40))

    elif game_state == STATE_GAMEOVER:
        # Game Over Ekranı
        go_surf = font_title.render("GAME OVER", True, NEON_RED)
        final_score_surf = font_large.render(f"Skorun: {score}", True, WHITE)
        retry_surf = font_medium.render("Tekrar oynamak için gitarına vur!", True, HERO_CYAN)

        screen.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, HEIGHT//3))
        screen.blit(final_score_surf, (WIDTH//2 - final_score_surf.get_width()//2, HEIGHT//2))
        screen.blit(retry_surf, (WIDTH//2 - retry_surf.get_width()//2, HEIGHT//2 + 80))

        # Yeniden Başlatma Kontrolü (Hemen tetiklenmesin diye ufak bir bekleme süresi eklenebilir ama şimdilik direkt ses kontrolü)
        if volume > VOLUME_THRESH * 5:
             reset_game()
             game_state = STATE_PLAYING

    pygame.display.flip()
    clock.tick(60)

stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()