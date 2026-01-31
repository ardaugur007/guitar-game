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
HEART_COLOR = (255, 0, 50)
TARGET_COLOR = (255, 200, 0) 
RELOAD_COLOR = (100, 100, 100) 
SAFE_COLOR = (100, 200, 255) 

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
pygame.display.set_caption("Guitar Sniper V11: Sweet Spot")

font_title = pygame.font.SysFont("Arial Black", 80)
font_large = pygame.font.SysFont("Arial Black", 50) 
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
    except: sys.exit()

p_detect = aubio.pitch(PITCH_METHOD, BUFFER_SIZE * 2, BUFFER_SIZE, RATE)
p_detect.set_unit("Hz")
p_detect.set_tolerance(TOLERANCE)

# --- ÇİZİM SINIFLARI ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x; self.y = y; self.color = color
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(2, 8)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed
        self.life = random.randint(20, 40)
        self.size = random.randint(3, 6)
    def update(self):
        self.x += self.vx; self.y += self.vy
        self.life -= 1; self.size = max(0, self.size - 0.1)
    def draw(self, surface):
        if self.life > 0: pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.size))

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
    def draw(self): 
        points = [(self.x, self.y+40), (self.x-35, self.y-20), (self.x-15, self.y-30), (self.x+15, self.y-30), (self.x+35, self.y-20)]
        dark_color = (self.color[0]//2, self.color[1]//2, self.color[2]//2)
        pygame.draw.polygon(screen, dark_color, points)
        pygame.draw.polygon(screen, self.color, points, 4)
        pygame.draw.circle(screen, self.color, (self.x-25, self.y-25), 8)
        pygame.draw.circle(screen, self.color, (self.x+25, self.y-25), 8)
        text_surf = font_medium.render(self.display_note, True, WHITE)
        s = pygame.Surface((text_surf.get_width() + 10, text_surf.get_height() + 6))
        s.set_alpha(150); s.fill((0,0,0))
        screen.blit(s, (self.x - s.get_width()//2, self.y - 15))
        text_rect = text_surf.get_rect(center=(self.x, self.y))
        screen.blit(text_surf, text_rect)

# --- YARDIMCI FONKSİYONLAR ---
def draw_heart(surface, x, y, size):
    points = [(x, y + size//4), (x - size//2, y - size//4), (x - size//4, y - size//2), (x, y - size//4), (x + size//4, y - size//2), (x + size//2, y - size//4)]
    pygame.draw.polygon(surface, HEART_COLOR, points)

def draw_target_lock(surface, x, y, radius, is_reloading):
    color = RELOAD_COLOR if is_reloading else TARGET_COLOR
    time = pygame.time.get_ticks() * 0.005
    for i in range(4):
        start_angle = time + (i * (math.pi / 2))
        end_angle = start_angle + (math.pi / 4)
        pygame.draw.arc(surface, color, (x-radius, y-radius, radius*2, radius*2), start_angle, end_angle, 3)

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

# --- OYUN DURUMLARI ---
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2
game_state = STATE_MENU

enemies = []
lasers = []
particles = [] 
stars = []
for _ in range(100): stars.append([random.randint(0, WIDTH), random.randint(0, HEIGHT), random.randint(1, 3)])

spawn_timer = 0
score = 0
lives = 3
combo = 0
player_pos = (WIDTH // 2, HEIGHT - 60)
running = True

# --- DENGELENMİŞ AYARLAR (V11) ---
last_penalty_time = 0 
screen_flash_timer = 0  
screen_flash_color = NEON_RED 
game_over_timer = 0

wrong_note_buildup = 0 
WRONG_NOTE_LIMIT = 30  # AYAR 1: Limit 30'a çekildi (Daha dengeli)
DECAY_RATE = 3         # AYAR 2: Soğuma hızı 3 yapıldı (Çok hızlı sönmez, gerilim kalır)

last_shot_time = 0
SHOT_COOLDOWN = 600    
game_start_time = 0
GRACE_PERIOD_MS = 2000 

def reset_game():
    global score, lives, combo, enemies, lasers, particles, spawn_timer, last_penalty_time, last_shot_time, game_start_time, wrong_note_buildup, screen_flash_timer
    score = 0
    lives = 3
    combo = 0
    enemies = []
    lasers = []
    particles = []
    spawn_timer = 0
    
    last_penalty_time = 0
    wrong_note_buildup = 0
    screen_flash_timer = 0
    
    last_shot_time = pygame.time.get_ticks()
    game_start_time = pygame.time.get_ticks()

print("Guitar Sniper V11: Sweet Spot Başlatıldı!")

while running:
    current_time = pygame.time.get_ticks()
    
    # Arka Plan
    screen.fill(BG_DARK)
    pygame.draw.rect(screen, BG_NEBULA, (0, HEIGHT//2, WIDTH, HEIGHT//2))
    for star in stars:
        star[1] += star[2]
        if star[1] > HEIGHT: star[1] = -5; star[0] = random.randint(0, WIDTH)
        size = star[2]
        brightness = int(min(255, star[2] * 80))
        b_val = min(255, brightness + 50)
        pygame.draw.circle(screen, (brightness, brightness, b_val), (star[0], star[1]), size)

    # Ses Analizi
    current_note_detected = None
    volume = 0
    
    # RELOAD KONTROLÜ
    is_reloading = (current_time - last_shot_time < SHOT_COOLDOWN)
    is_grace_period = (current_time - game_start_time < GRACE_PERIOD_MS)

    if not is_reloading:
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
    else:
        # Buffer şişmesin diye boş okuma yap
        try: stream.read(BUFFER_SIZE, exception_on_overflow=False)
        except: pass

    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    # --- OYUN MANTIĞI ---

    if game_state == STATE_MENU:
        title_surf = font_title.render("GUITAR SNIPER", True, TARGET_COLOR)
        sub_surf = font_medium.render("Başlamak için notaya vur!", True, WHITE)
        alpha = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 255
        sub_surf.set_alpha(int(alpha))
        screen.blit(title_surf, (WIDTH//2 - title_surf.get_width()//2, HEIGHT//3))
        screen.blit(sub_surf, (WIDTH//2 - sub_surf.get_width()//2, HEIGHT//2))
        draw_hero_ship(screen, WIDTH//2, HEIGHT - 100)
        
        if volume > VOLUME_THRESH * 5 and not is_reloading:
            reset_game()
            game_state = STATE_PLAYING

    elif game_state == STATE_PLAYING:
        spawn_timer += 1
        spawn_rate = max(40, 90 - (score // 10))
        if spawn_timer > spawn_rate:
            enemies.append(Enemy())
            spawn_timer = 0

        target_enemy = None
        if len(enemies) > 0: target_enemy = enemies[0] 

        hit_happened = False
        
        # Hata Barı Soğutma
        wrong_note_buildup = max(0, wrong_note_buildup - DECAY_RATE)

        if current_note_detected and target_enemy and not is_reloading:
            if current_note_detected == target_enemy.real_note:
                # --- DOĞRU VURUŞ ---
                nose_pos = (player_pos[0], player_pos[1] - 50)
                lasers.append(LaserBeam(nose_pos, (target_enemy.x, target_enemy.y), target_enemy.color))
                for _ in range(25): particles.append(Particle(target_enemy.x, target_enemy.y, target_enemy.color))
                enemies.pop(0) 
                
                combo += 1
                multiplier = 1 + (combo // 5)
                score += 10 * multiplier
                hit_happened = True
                
                wrong_note_buildup = 0 
                last_shot_time = current_time 
                screen_flash_timer = 10 
                screen_flash_color = NEON_GREEN
                
            else:
                # --- YANLIŞ NOTA ---
                if not is_grace_period:
                    if volume > VOLUME_THRESH * 1.5:
                        wrong_note_buildup += 5 
                    
                    if wrong_note_buildup >= WRONG_NOTE_LIMIT:
                        if current_time - last_penalty_time > 500:
                            lives -= 1
                            combo = 0
                            last_penalty_time = current_time
                            wrong_note_buildup = 0 
                            
                            screen_flash_timer = 10
                            screen_flash_color = NEON_RED
                            
                            if lives <= 0:
                                game_state = STATE_GAMEOVER
                                game_over_timer = current_time

        # Çizimler
        for laser in lasers: laser.draw()
        lasers = [l for l in lasers if l.life > 0]
        for p in particles: p.update(); p.draw(screen)
        particles = [p for p in particles if p.life > 0]
        draw_hero_ship(screen, player_pos[0], player_pos[1])

        for i, enemy in enumerate(enemies):
            enemy.move()
            enemy.draw()
            if i == 0: draw_target_lock(screen, enemy.x, int(enemy.y), 50, is_reloading)
            if enemy.y > HEIGHT + 50:
                enemies.remove(enemy)
                lives -= 1
                combo = 0
                screen_flash_timer = 10; screen_flash_color = NEON_RED 
                if lives <= 0: 
                    game_state = STATE_GAMEOVER
                    game_over_timer = current_time

        # Çerçeve Efekti
        if screen_flash_timer > 0:
            flash_c = SAFE_COLOR if (is_grace_period and screen_flash_color != NEON_RED) else screen_flash_color
            if is_grace_period: flash_c = SAFE_COLOR 
            pygame.draw.rect(screen, flash_c, (0, 0, WIDTH, HEIGHT), 15) 
            screen_flash_timer -= 1
        
        if is_grace_period:
             pygame.draw.rect(screen, SAFE_COLOR, (0, 0, WIDTH, HEIGHT), 5)

        # --- HUD ---
        score_surf = font_large.render(f"{score}", True, NEON_GREEN)
        screen.blit(score_surf, (20, 10))
        if combo > 1:
            multiplier = 1 + (combo // 5)
            combo_surf = font_medium.render(f"{combo} COMBO! (x{multiplier})", True, YELLOW)
            screen.blit(combo_surf, (20, 70))
        for i in range(lives):
            draw_heart(screen, WIDTH - 40 - (i * 40), 40, 30)

        # HATA BARI
        if wrong_note_buildup > 0:
            bar_width = 200
            bar_height = 10
            fill_amount = (wrong_note_buildup / WRONG_NOTE_LIMIT) * bar_width
            pygame.draw.rect(screen, (50, 0, 0), (WIDTH//2 - bar_width//2, HEIGHT - 150, bar_width, bar_height))
            pygame.draw.rect(screen, NEON_RED, (WIDTH//2 - bar_width//2, HEIGHT - 150, fill_amount, bar_height))
            screen.blit(font_small.render("HATA SINIRI", True, NEON_RED), (WIDTH//2 - 40, HEIGHT - 170))

        # DUYULAN NOTA
        if is_grace_period:
            indicator_color = SAFE_COLOR
            note_str = "KORUMA"
        elif is_reloading:
            indicator_color = RELOAD_COLOR
            note_str = "..." 
        elif screen_flash_timer > 0 and screen_flash_color == NEON_RED:
            indicator_color = NEON_RED
            note_str = "HATA"
        elif hit_happened:
            indicator_color = NEON_GREEN
            note_str = current_note_detected
        else:
            indicator_color = YELLOW
            note_str = current_note_detected if current_note_detected else "--"
        
        note_surf = font_large.render(note_str, True, indicator_color)
        screen.blit(note_surf, (80 - note_surf.get_width()//2, HEIGHT - 110))
        
        # DEBUG
        debug_info = f"Vol: {volume:.5f} | Bar: {wrong_note_buildup:.1f}"
        screen.blit(font_small.render(debug_info, True, (100, 100, 100)), (20, HEIGHT - 25))

    elif game_state == STATE_GAMEOVER:
        go_surf = font_title.render("GAME OVER", True, NEON_RED)
        final_score_surf = font_large.render(f"Skor: {score}", True, WHITE)
        time_passed = current_time - game_over_timer
        if time_passed < 2000: 
            retry_text = f"Sistem Soğuyor... {2 - int(time_passed/1000)}"
            retry_color = (100, 100, 100)
            can_restart = False
        else:
            retry_text = "Tekrar başlamak için VUR!"
            retry_color = HERO_CYAN
            can_restart = True
        retry_surf = font_medium.render(retry_text, True, retry_color)
        screen.blit(go_surf, (WIDTH//2 - go_surf.get_width()//2, HEIGHT//3))
        screen.blit(final_score_surf, (WIDTH//2 - final_score_surf.get_width()//2, HEIGHT//2))
        screen.blit(retry_surf, (WIDTH//2 - retry_surf.get_width()//2, HEIGHT//2 + 80))
        
        if can_restart and volume > VOLUME_THRESH * 10 and not is_reloading:
             reset_game()
             game_state = STATE_PLAYING

    pygame.display.flip()
    clock.tick(60)

stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()