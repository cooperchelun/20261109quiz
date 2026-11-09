import os
import random
import uuid
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD", "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT",
    "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE", "ALLOW", "ALONE",
    "ALONG", "ALTER", "AMONG", "ANGER", "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT", "AVOID", "AWAKE", "AWARE", "BADGE",
    "BAKER", "BASIC", "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH", "BLACK", "BLAME",
    "BLANK", "BLAST", "BLEED", "BLEND", "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING", "BROAD", "BROWN", "BRUSH", "BUILD",
    "BUNCH", "BUYER", "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE", "CHAIN", "CHAIR",
    "CHALK", "CHARM", "CHART", "CHASE", "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB", "CLOCK", "CLOSE", "COACH", "COAST",
    "COUNT", "COURT", "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD", "CROWN", "CURVE",
    "CYCLE", "DAILY", "DANCE", "DEATH", "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "EQUAL", "ERROR",
    "EVENT", "EVERY", "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD", "FIGHT", "FINAL",
    "FIRST", "FLAME", "FLASH", "FLOAT", "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT", "GIANT", "GLASS", "GLOBE", "GRACE",
    "GRADE", "GRAND", "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD", "GUESS", "GUIDE",
    "HAPPY", "HEART", "HEAVY", "HOTEL", "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH", "MAGIC", "MAJOR", "MARCH", "MATCH",
    "MEDAL", "MONEY", "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN", "OFFER", "ORDER"
]

# 任務三：全域勝率統計變數
total_games = 0
wins = 0

# 記憶體儲存遊戲狀態
games_db: Dict[str, dict] = {}


class NewGameRequest(BaseModel):
    hard_mode: bool = False


class GuessRequest(BaseModel):
    game_id: str
    guess: str


@app.post("/api/new-game")
def start_new_game(req: NewGameRequest = None):
    """ 建立新一局遊戲，支援 hard_mode 參數並計算總遊戲數 """
    global total_games
    total_games += 1

    hard_mode = req.hard_mode if req else False
    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)
    
    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": hard_mode,
        "history": []  # 記錄歷史猜測與結果（供硬核模式驗證）
    }
    return {"game_id": game_id, "message": "New game started!", "hard_mode": hard_mode}


@app.get("/api/stats")
def get_stats():
    """ 任務三：回傳勝率統計數據供前端顯示 """
    win_rate = (wins / total_games * 100) if total_games > 0 else 0
    return {
        "total": total_games,
        "wins": wins,
        "win_rate": round(win_rate, 1)
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):
    """ 接收玩家猜測，包含單字合法性檢查、硬核模式驗證與勝率累計 """
    global wins
    game_id = req.game_id
    guess = req.guess.upper()

    if game_id not in games_db:
        raise HTTPException(status_code=404, detail="Game session not found.")
    
    if len(guess) != 5:
        raise HTTPException(status_code=400, detail="Word must be 5 letters.")

    # 任務二：檢查單字是否在字典內
    if guess not in WORD_BANK:
        raise HTTPException(status_code=400, detail="Word not in dictionary")

    game = games_db[game_id]
    target = game["target"]

    # 任務四：硬核模式（Hard Mode）驗證
    if game["hard_mode"] and game["history"]:
        for prev_guess, prev_feedback in game["history"]:
            for i in range(5):
                if prev_feedback[i] == "correct":
                    if guess[i] != prev_guess[i]:
                        raise HTTPException(
                            status_code=400,
                            detail="Hard Mode: Must use revealed hint at green position"
                        )

    game["attempts"] += 1
    attempts = game["attempts"]

    feedback = ["absent"] * 5
    target_letter_counts = {}

    for char in target:
        target_letter_counts[char] = target_letter_counts.get(char, 0) + 1

    # 標記綠色 correct
    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            target_letter_counts[guess[i]] -= 1

    # 標記黃色 present
    for i in range(5):
        if feedback[i] != "correct" and guess[i] in target:
            if target_letter_counts[guess[i]] > 0:
                feedback[i] = "present"
                target_letter_counts[guess[i]] -= 1

    # 記錄歷史
    game["history"].append((guess, feedback))

    is_correct = (guess == target)
    is_game_over = is_correct or (attempts >= 6)

    if is_correct:
        game["status"] = "WON"
        wins += 1  # 累計勝場
    elif attempts >= 6:
        game["status"] = "LOST"

    # 任務一：失敗或成功時回傳 target_word
    response_target = target if is_game_over else None

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "target_word": response_target,
        "attempts_left": 6 - attempts
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
