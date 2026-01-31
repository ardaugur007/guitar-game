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

# --- NEON RENK PALETİ ---
BG_COLOR_TOP = (5, 5, 15)      # Arka plan üst kısım
BG_COLOR_BOTTOM = (20, 10, 30) # Arka plan alt kısım
WHITE = (220, 220, 255)
NEON_RED = (255, 50, 80)       # Diyezler (Daha canlı)
NEON_BLUE = (0, 180, 255)      # Bemoller (Cyber mavi)
NEON_GREEN = (50, 255, 100)    # Skor/Vuruş
NEON_PURPLE = (180, 0, 255)    # Oyuncu Gemisi
YELLOW = (255, 230, 50)        # Duyulan nota

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
pygame.display.set_caption("Cyber Guitar Shooter")

# Fontları büyütüp güzelleştirdik
font_large = pygame.font.SysFont("Arial Black", 60) 
font_medium = pygame.font.SysFont("Arial", 28, bold=True)
font_small = pygame.font.SysFont("Consolas", 16)
clock = pygame.time.Clock()

# --- SES GİRİŞİ ---
p = pyaudio.PyAudio()
try:
    stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, input=True, input_device_index=8, frames_per_buffer=BUFFER_SIZE)
except Exception:
    try: # Yedek olarak ID 44 veya varsayılanı dener
        stream = p.open(format=pyaudio.paFloat32, channels=CHANNELS, rate=RATE, input=True, input_device_index=44, frames_per_buffer=BUFFER_SIZE)
    except: 
        print("Ses kartı başlatılamadı!")
        sys.exit()

p_detect = aubio.pitch(PITCH_METHOD, BUFFER_SIZE * 2, BUFFER_SIZE, RATE)
p_detect.set_unit("Hz")
p_detect.set_tolerance(TOLERANCE)

# --- GÖRSEL SINIFLAR VE FONKSİYONLAR ---

class LaserBeam:
    """Vuruş anında çıkan lazer efekti"""
    def __init__(self, start_pos, end_pos, color):
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.color = color
        self.life = 15 # Lazerin ekranda kalma süresi (frame)
        self.max_life = 15
        self.width = 10

    def draw(self):
        if self.life > 0:
            # Lazer gittikçe incelir ve saydamlaşır
            progress = self.life / self.max_life
            current_width = int(self.width * progress)
            
            # Ana ışın
            pygame.draw.line(screen, self.color, self.start_pos, self.end_pos, current_width)
            # İçindeki beyaz parlaklık (çekirdek)
            if current_width > 2:
                pygame.draw.line(screen, WHITE, self.start_pos, self.end_pos, current_width // 3)
            
            # Hedefteki patlama noktası
            pygame.draw.circle(screen, WHITE, self.end_pos, (current_width + 5))
            
            self.life -= 1

def draw_player(x, y):
    """Oyuncuyu stilize bir gitar/uzay gemisi gibi çizer"""
    # 1. Dış Hâle (Glow)
    pygame.draw.polygon(screen, (100, 0, 150), [(x, y-55), (x-35, y+35), (x+35, y+35)], 0)
    
    # 2. Ana Gövde (Mor Üçgen)
    points = [(x, y-50), (x-30, y+30), (x+30, y+30)]
    pygame.draw.polygon(screen, NEON_PURPLE, points, 0)
    
    # 3. İç Detay (Beyaz çizgi - Tel gibi)
    pygame.draw.line(screen, WHITE, (x, y-40), (x, y+25), 3)
    
    # 4. Kenar Çizgileri (Neon etkisi)
    pygame.draw.polygon(screen, (200, 100, 255), points, 3)

class Enemy:
    def __init__(self):
        self.display_note = random.choice(GAME_NOTES)
        self.real_note = ENHARMONIC_MAP.get(self.display_note, self.display_note)
        self.x = random.randint(50, WIDTH - 100)
        self.y = -60
        self.speed = 2.0 
        self.radius = 40
        self.color = NEON_BLUE if "b" in self.display_note else NEON_RED
        self.pulse = random.random() * 10 # Rastgele başlangıç fazı

    def move(self):
        self.y += self.speed
        self.pulse += 0.1 # Renk animasyonu için

    def draw(self):
        # Daire yerine "Gitar Penası" (Pick) şekli çizimi
        # Penalar yuvarlatılmış üçgene benzer.
        
        # Penanın 3 ana köşesi
        p1 = (self.x - self.radius, self.y - self.radius * 0.5) # Sol üst
        p2 = (self.x + self.radius, self.y - self.radius * 0.5) # Sağ üst
        p3 = (self.x, self.y + self.radius * 1.2)               # Alt uç
        
        # Renk animasyonu (Hafif yanıp sönme)
        pulse_val = (math.sin(self.pulse) + 1) / 2 # 0 ile 1 arası
        # Rengi biraz açıp koyulaştırıyoruz
        r = min(255, self.color[0] + pulse_val * 40)
        g = min(255, self.color[1] + pulse_val * 40)
        b = min(255, self.color[2] + pulse_val * 40)
        current_color = (r, g, b)

        # Penayı çiz
        pygame.draw.polygon(screen, current_color, [p1, p2, p3])
        # Beyaz çerçeve (Outline)
        pygame.draw.polygon(screen, WHITE, [p1, p2, p3], 3)

        # Nota Yazısı
        text_surf = font_medium.render(self.display_note, True, WHITE)
        # Yazıya hafif gölge
        shadow_surf = font_medium.render(self.display_note, True, (0,0,0))
        
        text_rect = text_surf.get_rect(center=(self.x, self.y))
        screen.blit(shadow_surf, (text_rect.x + 2, text_rect.y + 2))
        screen.blit(text_surf, text_rect)

# --- OYUN DEĞİŞKENLERİ ---
enemies = []
lasers = [] 
spawn_timer = 0
score = 0
player_pos = (WIDTH // 2, HEIGHT - 50) 
running = True

print("Cyber Guitar Shooter Başlatıldı! Rock on!")

while running:
    # --- ARKA PLAN (Gradyan) ---
    # Performans için basit bir dikdörtgen değil, dikey çizgilerle gradyan
    # (Bu işlemi her karede yapmak yorabilir, basitçe fill yapıp üzerine bir shape de atabiliriz)
    screen.fill(BG_COLOR_TOP)
    # Alt kısma hafif morluk katalım
    pygame.draw.rect(screen, BG_COLOR_BOTTOM, (0, HEIGHT//2, WIDTH, HEIGHT//2))
    
    current_note_detected = None
    debug_volume = 0.0
    debug_pitch = 0.0

    # --- SES İŞLEME ---
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
    if spawn_timer > 90: # Düşman gelme sıklığı
        enemies.append(Enemy())
        spawn_timer = 0

    hit_happened = False
    if current_note_detected:
        for enemy in enemies:
            if enemy.real_note == current_note_detected:
                # VURUŞ!
                # Lazer ekle
                lasers.append(LaserBeam(player_pos, (enemy.x, enemy.y), enemy.color))
                
                # Patlama Efekti (Basit daireler)
                pygame.draw.circle(screen, WHITE, (enemy.x, int(enemy.y)), 60)
                
                enemies.remove(enemy)
                score += 1
                hit_happened = True
                break 

    # --- ÇİZİMLER ---
    
    # 1. Oyuncu
    draw_player(player_pos[0], player_pos[1])

    # 2. Düşmanlar
    for enemy in enemies:
        enemy.move()
        enemy.draw()
        if enemy.y > HEIGHT + 50:
            enemies.remove(enemy)
            score = max(0, score - 5)

    # 3. Lazerler
    for laser in lasers:
        laser.draw()
    lasers = [l for l in lasers if l.life > 0] # Süresi bitenleri temizle

    # --- ARAYÜZ (UI) ---
    
    # Skor Paneli (Üst Orta)
    score_text = font_large.render(str(score), True, NEON_GREEN)
    screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, 10))
    screen.blit(font_small.render("SKOR", True, WHITE), (WIDTH//2 - 20, 70))

    # Duyulan Nota (Sol Alt - Büyük Gösterge)
    if hit_happened:
        indicator_color = NEON_GREEN
        pygame.draw.circle(screen, (0, 50, 0), (80, HEIGHT-80), 55) # Arka plan halkası
    else:
        indicator_color = YELLOW
    
    note_str = current_note_detected if current_note_detected else "--"
    note_surf = font_large.render(note_str, True, indicator_color)
    
    # Notayı ekrana bas
    screen.blit(note_surf, (80 - note_surf.get_width()//2, HEIGHT - 110))
    screen.blit(font_small.render("DUYULAN", True, WHITE), (50, HEIGHT - 40))

    # Debug (Sağ Alt - Çok küçük)
    vol_c = NEON_RED if debug_volume < VOLUME_THRESH else NEON_GREEN
    screen.blit(font_small.render(f"Vol: {debug_volume:.4f}", True, vol_c), (WIDTH - 150, HEIGHT - 40))
    screen.blit(font_small.render(f"Hz: {debug_pitch:.1f}", True, WHITE), (WIDTH - 150, HEIGHT - 20))

    pygame.display.flip()
    clock.tick(60)

stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()