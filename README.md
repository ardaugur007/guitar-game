# 🎸 Guitar Sniper: Audio-Reactive Python Game (V5)

> **A real-time reflex game controlled by an actual electric guitar, built with Python and DSP techniques.**

This project demonstrates the use of Digital Signal Processing (DSP) to create an interactive gaming experience. Instead of a keyboard or controller, the player must strum the correct notes on their guitar to destroy incoming enemies.

<img width="897" height="725" alt="image" src="https://github.com/user-attachments/assets/0e36bc24-d718-45e7-a83a-98e266dfd085" />
<img width="896" height="729" alt="image" src="https://github.com/user-attachments/assets/752ee864-b3c5-47a4-ab68-5eb1a31d9f1e" />
<img width="890" height="724" alt="image" src="https://github.com/user-attachments/assets/f4e04abb-ca9a-42e8-b0c9-b8fdc5e8c976" />


## 🌟 Key Features (V5 Update)

* **Real-Time Pitch Detection:** Uses `Aubio` and `PyAudio` for low-latency note recognition at 48kHz sample rate.
* **Bolt-Action Mechanism:** Implements a custom cooldown system to prevent "echo-triggered" false positives, simulating a bolt-action sniper rifle feel.
* **Smart Penalty System:** Features a "Penalty Bar" that tolerates accidental string noise but punishes persistent wrong notes.
* **Visual Polish:** Neon aesthetics, particle explosion effects, screen shake feedback, and dynamic target locking.
* **Safe Start Mode:** Includes a 2-second immunity shield (Grace Period) on respawn to prevent spawn-killing.
* **Adaptive Difficulty:** The spawn rate of enemies increases dynamically as the score gets higher.

## 🛠️ Tech Stack

* **Python 3.x**
* **Pygame:** Rendering engine and game loop management.
* **PyAudio:** Raw audio stream data acquisition.
* **NumPy:** Mathematical operations on audio buffers.
* **Aubio:** Real-time pitch detection algorithm.

## 🚀 Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/YOUR_USERNAME/guitar-game.git](https://github.com/YOUR_USERNAME/guitar-game.git)
    cd guitar-game
    ```

2.  **Install dependencies:**
    ```bash
    pip install pygame pyaudio numpy aubio
    ```

3.  **Hardware Setup:**
    * Connect your electric guitar to your PC via an Audio Interface (e.g., Focusrite Scarlett, Behringer).
    * Ensure the interface is set as the default recording device in Windows/Mac settings.

## ⚠️ IMPORTANT: Configuring Your Audio Interface

Since every computer assigns different IDs to sound cards, **you must update the code to match your device.**

1.  **Find your Device ID:**
    Create a new file named `check_device.py`, paste this code, and run it:
    ```python
    import pyaudio
    p = pyaudio.PyAudio()
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info['maxInputChannels'] > 0:
            print(f"ID {i}: {info['name']}")
    ```
    *Look for your Audio Interface (e.g., 'Focusrite USB Audio') and note its **ID number**.*

2.  **Update the Game Code:**
    * Open `gitar_oyunu.py`.
    * Find the line: `input_device_index=8` (around line 50).
    * Change `8` to **YOUR Device ID**.

3.  **Run the game:**
    ```bash
    python gitar_oyunu.py
    ```

## 🎮 How to Play

1.  **Start:** Strum any note loudly to begin the game from the menu.
2.  **Aim:** Enemies descend with specific notes (e.g., C, F#, A) displayed on them.
3.  **Shoot:** Play the matching note on your guitar.
    * *Tip:* The game targets the bottom-most enemy (highlighted with a yellow/grey lock).
4.  **Feedback:**
    * **Green Frame:** Perfect hit!
    * **Red Frame:** Wrong note or missed enemy.
5.  **Survive:** Don't let the "Penalty Bar" fill up or enemies pass the bottom of the screen.

---
*Developed by [Arda Ugur]*
