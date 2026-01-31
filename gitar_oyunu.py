import pygame
import pyaudio
import numpy as np
import aubio
import random
import sys

# --- AYARLAR ---
BUFFER_SIZE = 1024
CHANNELS = 2          # Focusrite için Stereo şart
RATE = 48000          # <--- DEĞİŞİKLİK BURADA: 44100 yerine 48000 yaptık.
PITCH_METHOD = "default"
TOLERANCE = 0.8
VOLUME_THRESH = 0.0001 # Algılamayı kolaylaştırmak için eşiği iyice düşürdük

# Renkler
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
RED = (255, 60, 60)
GREEN = (50, 255, 80)
BLUE = (60, 60, 255)

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
pygame.display.set_caption("Guitar Shooter: Focusrite Edition")
font = pygame.font.SysFont("Arial", 40, bold=True)
debug_font = pygame.font.SysFont("Consolas", 18) # Hata ayıklama için küçük font
clock = pygame.time.Clock()

p = pyaudio.PyAudio()

# --- SES GİRİŞİ ---
try:
    # ID 8'i deniyoruz
    stream = p.open(format=pyaudio.paFloat32,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    input_device_index=8, 
                    frames_per_buffer=BUFFER_SIZE)
except Exception as e:
    print(f"ID 8 Hata: {e}, ID 44 deneniyor...")
    try:
        stream = p.open(format=pyaudio.paFloat32,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=44,
                        frames_per_buffer=BUFFER_SIZE)
    except Exception as e2:
        print(f"Ses kartı açılamadı: {e2}")
        sys.exit()

# Aubio Ayarı
p_detect = aubio.pitch(PITCH_METHOD, BUFFER_SIZE * 2, BUFFER_SIZE, RATE)
p_detect.set_unit("Hz")
p_detect.set_tolerance(TOLERANCE)

class Enemy:
    def __init__(self):
        self.display_note = random.choice(GAME_NOTES)
        self.real_note = ENHARMONIC_MAP.get(self.display_note, self.display_note)
        self.x = random.randint(50, WIDTH - 100)
        self.y = -60
        self.speed = 2
        self.radius = 35
        self.color = BLUE if "b" in self.display_note else RED

    def move(self): self.y += self.speed
    def draw(self):
        pygame.draw.circle(screen, self.color, (self.x, int(self.y)), self.radius)
        text = font.render(self.display_note, True, WHITE)
        text_rect = text.get_rect(center=(self.x, int(self.y)))
        screen.blit(text, text_rect)

enemies = []
spawn_timer = 0
score = 0
running = True

print("Oyun Başladı! Gitarını çal...")

while running:
    screen.fill(BLACK)
    
    current_note_detected = None
    debug_volume = 0.0
    debug_pitch = 0.0

    # --- SES İŞLEME ---
    try:
        audio_data = stream.read(BUFFER_SIZE, exception_on_overflow=False)
        samples = np.frombuffer(audio_data, dtype=np.float32)
        
        # --- KRİTİK NOKTA: STEREO'DAN MONO'YA ÇEVİRME ---
        # --- YENİ YÖNTEM: MIX (KARIŞTIRMA) ---
        if CHANNELS == 2:
            # Sol ve Sağ kanalı toplayıp ikiye bölüyoruz.
            # Böylece gitar 1'de de olsa 2'de de olsa ses gelir.
            left = samples[0::2]
            right = samples[1::2]
            # Boyut eşitlemesi (bazen 1 frame eksik gelebilir)
            min_len = min(len(left), len(right))
            samples = (left[:min_len] + right[:min_len]) / 2
        
        # Bu işlemden sonra veriyi aubio'ya veriyoruz
        pitch = p_detect(samples)[0]
        volume = np.sum(samples**2) / len(samples)
        
        debug_volume = volume
        debug_pitch = pitch
        
        if volume > VOLUME_THRESH:
            current_note_detected = hz_to_note(pitch)
            
    except Exception as e:
        pass

    # --- OYUN DÖNGÜSÜ ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT: running = False

    spawn_timer += 1
    if spawn_timer > 80:
        enemies.append(Enemy())
        spawn_timer = 0

    hit_happened = False
    if current_note_detected:
        for enemy in enemies:
            if enemy.real_note == current_note_detected:
                enemies.remove(enemy)
                score += 1
                hit_happened = True
                pygame.draw.circle(screen, GREEN, (enemy.x, int(enemy.y)), 60, 5)
                break 

    for enemy in enemies:
        enemy.move()
        enemy.draw()
        if enemy.y > HEIGHT:
            enemies.remove(enemy)
            score = max(0, score - 1)

    # --- UI & DEBUG PANELİ ---
    
    # Nota Bilgisi
    ui_color = GREEN if hit_happened else WHITE
    screen.blit(font.render(f"Nota: {current_note_detected if current_note_detected else '---'}", True, ui_color), (20, HEIGHT - 100))
    
    # Skor
    screen.blit(font.render(f"Skor: {score}", True, WHITE), (WIDTH - 200, HEIGHT - 100))

    # --- TEKNİK DETAYLAR (Sol Alt Köşe) ---
    # Burası sorunu çözmemiz için çok önemli. Ses gelip gelmediğini buradan göreceğiz.
    vol_text = f"Ses Gücü: {debug_volume:.5f}" 
    pitch_text = f"Frekans: {debug_pitch:.1f} Hz"
    
    # Eğer ses gücü çok düşükse Kırmızı, iyiyse Yeşil yazı
    vol_color = RED if debug_volume < VOLUME_THRESH else GREEN
    
    screen.blit(debug_font.render(vol_text, True, vol_color), (20, HEIGHT - 60))
    screen.blit(debug_font.render(pitch_text, True, WHITE), (20, HEIGHT - 30))

    pygame.display.flip()
    clock.tick(60)

stream.stop_stream()
stream.close()
p.terminate()
pygame.quit()