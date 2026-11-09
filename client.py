import sys
import os
import pygame
import requests

# 保留指定的 Render 雲端網址
API_BASE_URL = "https://two0261109quiz.onrender.com"

# 顏色定義
COLOR_BG = (18, 18, 19)
COLOR_TEXT = (255, 255, 255)
COLOR_EMPTY = (58, 58, 60)
COLOR_CORRECT = (83, 141, 78)    # 綠色
COLOR_PRESENT = (181, 159, 59)  # 黃色
COLOR_ABSENT = (58, 58, 60)     # 灰色

pygame.init()
# 任務三：視窗寬度設為 700 容納側邊欄
WIDTH, HEIGHT = 700, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pygame Wordle + FastAPI Client")
font = pygame.font.SysFont("Arial", 36, bold=True)
small_font = pygame.font.SysFont("Arial", 18)

class WordleGame:
    def __init__(self):
        self.game_id = None
        self.grid = [["" for _ in range(5)] for _ in range(6)]
        self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
        self.row = 0
        self.col = 0
        self.game_over = False
        self.hard_mode = False  # 預設 Normal 模式
        self.guess_history = []  # 側邊欄歷史單字
        self.stats = {"total": 0, "wins": 0, "win_rate": 0.0}
        self.message = "Press ENTER to submit | 1: Normal | 2: Hard | 3: Restart"
        self.start_new_game()

    def start_new_game(self):
        """ 向伺服器請求建立新的一局 """
        try:
            payload = {"hard_mode": self.hard_mode}
            res = requests.post(f"{API_BASE_URL}/api/new-game", json=payload, timeout=60)
            if res.status_code == 200:
                data = res.json()
                self.game_id = data["game_id"]
                self.grid = [["" for _ in range(5)] for _ in range(6)]
                self.colors = [[COLOR_EMPTY for _ in range(5)] for _ in range(6)]
                self.row = 0
                self.col = 0
                self.game_over = False
                self.guess_history = []
                mode_str = "HARD" if self.hard_mode else "Normal"
                self.message = f"New game started! Mode: {mode_str}"
                self.fetch_stats()
            else:
                self.message = "Server error starting new game."
        except requests.exceptions.RequestException:
            self.message = "Cannot connect to FastAPI server!"

    def fetch_stats(self):
        """ 任務三：取得後端勝率統計數據 """
        try:
            res = requests.get(f"{API_BASE_URL}/api/stats", timeout=15)
            if res.status_code == 200:
                self.stats = res.json()
        except requests.exceptions.RequestException:
            pass

    def submit_guess(self):
        """ 將當前行單字發送至伺服器驗證 """
        if self.col < 5:
            self.message = "Not enough letters!"
            return

        guess_word = "".join(self.grid[self.row])
        try:
            payload = {"game_id": self.game_id, "guess": guess_word}
            res = requests.post(f"{API_BASE_URL}/api/guess", json=payload, timeout=60)
            
            if res.status_code == 200:
                data = res.json()
                feedback = data["feedback"]
                
                for i in range(5):
                    if feedback[i] == "correct":
                        self.colors[self.row][i] = COLOR_CORRECT
                    elif feedback[i] == "present":
                        self.colors[self.row][i] = COLOR_PRESENT
                    else:
                        self.colors[self.row][i] = COLOR_ABSENT

                self.guess_history.append(guess_word)
                self.fetch_stats()

                if data["is_correct"]:
                    self.message = "Congratulations! You won! Press 3 to restart."
                    self.game_over = True
                else:
                    self.row += 1
                    self.col = 0
                    attempts_left = data.get("attempts_left", 6 - self.row)
                    if self.row == 6:
                        target = data.get("target_word", "UNKNOWN")
                        # 任務一：失敗時顯示正確答案
                        self.message = f"Game Over! The word was {target}. Press 3 to restart."
                        self.game_over = True
                    else:
                        # 任務一：顯示剩餘次數
                        self.message = f"Keep guessing! ({attempts_left} tries left)"
            else:
                detail = res.json().get("detail", "Error processing guess")
                # 任務二：若不在字典內，顯示指定訊息且不增加列數（不扣次數）
                if detail == "Word not in dictionary":
                    self.message = "Not in word list!"
                else:
                    self.message = detail
        except requests.exceptions.RequestException:
            self.message = "Network error during guess!"

    def handle_keydown(self, event):
        # 任務四：按 1 切換 Normal 模式並重開新局
        if event.key in (pygame.K_1, pygame.K_KP1):
            self.hard_mode = False
            self.start_new_game()
            return

        # 任務四：按 2 切換 HARD 模式並重開新局
        if event.key in (pygame.K_2, pygame.K_KP2):
            self.hard_mode = True
            self.start_new_game()
            return

        # 按 3：維持當前模式重開新局
        if event.key in (pygame.K_3, pygame.K_KP3):
            self.start_new_game()
            return

        if self.game_over:
            return

        if event.key == pygame.K_BACKSPACE:
            if self.col > 0:
                self.col -= 1
                self.grid[self.row][self.col] = ""
        elif event.key == pygame.K_RETURN:
            self.submit_guess()
        elif event.unicode.isalpha() and len(event.unicode) == 1:
            if self.col < 5:
                self.grid[self.row][self.col] = event.unicode.upper()
                self.col += 1

    def draw(self, surface):
        surface.fill(COLOR_BG)
        
        # 1. 繪製 6x5 網格
        margin_x, margin_y = 50, 50
        box_size = 60
        gap = 10

        for r in range(6):
            for c in range(5):
                x = margin_x + c * (box_size + gap)
                y = margin_y + r * (box_size + gap)
                rect = pygame.Rect(x, y, box_size, box_size)
                
                pygame.draw.rect(surface, self.colors[r][c], rect, border_radius=4)
                if self.colors[r][c] == COLOR_EMPTY:
                    pygame.draw.rect(surface, (80, 80, 80), rect, width=2, border_radius=4)

                char = self.grid[r][c]
                if char:
                    text_surface = font.render(char, True, COLOR_TEXT)
                    text_rect = text_surface.get_rect(center=rect.center)
                    surface.blit(text_surface, text_rect)

        # 2. 任務三：繪製側邊欄分隔線與統計資訊
        pygame.draw.line(surface, (80, 80, 80), (500, 0), (500, HEIGHT), 2)

        stats_text = f"Total: {self.stats['total']} | Wins: {self.stats['wins']} | Win Rate: {self.stats['win_rate']}%"
        stats_surface = small_font.render(stats_text, True, COLOR_TEXT)
        surface.blit(stats_surface, (515, 20))

        history_title = small_font.render("Guess History:", True, (150, 150, 150))
        surface.blit(history_title, (515, 60))

        for idx, prev_word in enumerate(self.guess_history):
            w_surface = small_font.render(f"{idx + 1}. {prev_word}", True, COLOR_TEXT)
            surface.blit(w_surface, (515, 90 + idx * 30))

        # 任務四：右上角顯示目前模式
        mode_text = f"Mode: {'HARD' if self.hard_mode else 'Normal'}"
        mode_color = (255, 100, 100) if self.hard_mode else (100, 255, 100)
        mode_surface = small_font.render(mode_text, True, mode_color)
        surface.blit(mode_surface, (515, 580))

        # 3. 底部提示訊息
        msg_surface = small_font.render(self.message, True, COLOR_TEXT)
        msg_rect = msg_surface.get_rect(center=(WIDTH // 2 - 50, HEIGHT - 40))
        surface.blit(msg_surface, msg_rect)


def main():
    clock = pygame.time.Clock()
    game = WordleGame()

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event)

        game.draw(screen)
        pygame.display.flip()
        clock.tick(30)

if __name__ == "__main__":
    main()
