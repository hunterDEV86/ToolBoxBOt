from telebot import types
import random
import math
from copy import deepcopy

BOARD_SIZE = 9
games = {}

class GoGame:
    def __init__(self, player1_id):
        self.board = [[" " for _ in range(BOARD_SIZE)] for _ in range(BOARD_SIZE)]
        self.current_player = "⚫"
        self.player1 = player1_id
        self.player2 = None
        self.mode = None
        self.difficulty = None
        self.last_move = None
        self.previous_board = None
        self.captured_stones = {"⚫": 0, "⚪": 0}
        self.pass_count = 0

    def make_move(self, row, col):
        if self.board[row][col] != " ":
            return False
            
        # ذخیره وضعیت قبلی برای قانون Ko
        self.previous_board = deepcopy(self.board)
        
        self.board[row][col] = self.current_player
        captured = self.check_captures(row, col)
        
        # بررسی خودکشی
        if not captured and not self.has_liberties(row, col):
            self.board[row][col] = " "
            return False
            
        # بررسی قانون Ko
        if self.previous_board and self.is_ko():
            self.board[row][col] = " "
            return False
            
        self.last_move = (row, col)
        self.current_player = "⚪" if self.current_player == "⚫" else "⚫"
        self.pass_count = 0
        return True

    def check_captures(self, row, col):
        opponent = "⚪" if self.current_player == "⚫" else "⚫"
        captured = False
        directions = [(0,1), (1,0), (0,-1), (-1,0)]
        
        for dx, dy in directions:
            x, y = row + dx, col + dy
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                if self.board[x][y] == opponent:
                    group = self.get_group(x, y)
                    if not self.has_liberties_group(group):
                        captured = True
                        for gx, gy in group:
                            self.board[gx][gy] = " "
                            self.captured_stones[self.current_player] += 1
        
        return captured

    def get_group(self, row, col):
        color = self.board[row][col]
        group = set()
        stack = [(row, col)]
        
        while stack:
            r, c = stack.pop()
            if (r, c) not in group:
                group.add((r, c))
                for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
                    x, y = r + dx, c + dy
                    if (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE and 
                        self.board[x][y] == color):
                        stack.append((x, y))
        return group

    def has_liberties(self, row, col):
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            x, y = row + dx, col + dy
            if (0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE and 
                self.board[x][y] == " "):
                return True
        return False

    def has_liberties_group(self, group):
        for row, col in group:
            if self.has_liberties(row, col):
                return True
        return False

    def is_ko(self):
        return self.board == self.previous_board

    def get_valid_moves(self):
        valid_moves = []
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.board[i][j] == " ":
                    test_board = deepcopy(self)
                    if test_board.make_move(i, j):
                        valid_moves.append((i, j))
        return valid_moves

    def ai_move(self):
        if self.difficulty == "easy":
            return self.ai_easy_move()
        elif self.difficulty == "medium":
            return self.ai_medium_move()
        else:
            return self.ai_hard_move()

    def ai_easy_move(self):
        valid_moves = self.get_valid_moves()
        if valid_moves:
            return random.choice(valid_moves)
        return None

    def ai_medium_move(self):
        valid_moves = self.get_valid_moves()
        best_move = None
        best_score = float('-inf')
        
        for move in valid_moves:
            score = self.evaluate_move(move[0], move[1])
            if score > best_score:
                best_score = score
                best_move = move
                
        return best_move

    def ai_hard_move(self):
        return self.monte_carlo_tree_search()

    def evaluate_move(self, row, col):
        score = 0
        # Capture potential
        test_board = deepcopy(self)
        if test_board.make_move(row, col):
            score += test_board.captured_stones[self.current_player] * 10
            
        # Center control
        center_dist = abs(row - BOARD_SIZE//2) + abs(col - BOARD_SIZE//2)
        score -= center_dist
        
        # Territory potential
        for dx, dy in [(0,1), (1,0), (0,-1), (-1,0)]:
            x, y = row + dx, col + dy
            if 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE:
                if self.board[x][y] == self.current_player:
                    score += 2
                    
        return score

    def monte_carlo_tree_search(self, iterations=1000):
        valid_moves = self.get_valid_moves()
        if not valid_moves:
            return None
            
        scores = {move: 0 for move in valid_moves}
        
        for move in valid_moves:
            for _ in range(iterations // len(valid_moves)):
                test_board = deepcopy(self)
                if test_board.make_move(move[0], move[1]):
                    result = test_board.simulate_random_game()
                    scores[move] += result
                    
        return max(scores.items(), key=lambda x: x[1])[0]

    def simulate_random_game(self, max_moves=50):
        test_board = deepcopy(self)
        moves = 0
        
        while moves < max_moves:
            valid_moves = test_board.get_valid_moves()
            if not valid_moves:
                break
                
            row, col = random.choice(valid_moves)
            test_board.make_move(row, col)
            moves += 1
            
        return test_board.evaluate_position()

    def evaluate_position(self):
        black_score = self.captured_stones["⚫"]
        white_score = self.captured_stones["⚪"]
        
        for i in range(BOARD_SIZE):
            for j in range(BOARD_SIZE):
                if self.board[i][j] == "⚫":
                    black_score += 1
                elif self.board[i][j] == "⚪":
                    white_score += 1
                    
        return black_score - white_score if self.current_player == "⚫" else white_score - black_score

def create_board_markup(game):
    markup = types.InlineKeyboardMarkup(row_width=BOARD_SIZE)
    for i in range(BOARD_SIZE):
        row = []
        for j in range(BOARD_SIZE):
            cell = game.board[i][j] if game.board[i][j] != " " else "·"
            callback_data = f"go_move_{i}_{j}"
            row.append(types.InlineKeyboardButton(cell, callback_data=callback_data))
        markup.row(*row)
    
    pass_btn = types.InlineKeyboardButton("Pass", callback_data="go_pass")
    resign_btn = types.InlineKeyboardButton("Resign", callback_data="go_resign")
    markup.row(pass_btn, resign_btn)
    
    return markup

def start_game(bot, message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    vs_bot = types.InlineKeyboardButton("🤖 بازی با ربات", callback_data="go_bot")
    vs_friend = types.InlineKeyboardButton("👥 بازی با دوست", callback_data="go_friend")
    tutorial = types.InlineKeyboardButton("📖 آموزش بازی", callback_data="go_tutorial")
    markup.add(vs_bot, vs_friend)
    markup.add(tutorial)
    
    bot.send_message(
        message.chat.id,
        "🎮 به بازی گو خوش آمدید!\n"
        "لطفا یک گزینه را انتخاب کنید:",
        reply_markup=markup
    )

def handle_callback(bot, call):
    if not call.data.startswith("go_"):
        return False

    chat_id = call.message.chat.id
    action = call.data[3:]

    if action == "tutorial":
        show_tutorial(bot, chat_id)
        return True
        
    if action == "start":
        start_game(bot, call.message)
        return True

    if action == "bot":
        markup = types.InlineKeyboardMarkup(row_width=3)
        easy = types.InlineKeyboardButton("آسان", callback_data="go_diff_easy")
        medium = types.InlineKeyboardButton("متوسط", callback_data="go_diff_medium")
        hard = types.InlineKeyboardButton("سخت", callback_data="go_diff_hard")
        markup.add(easy, medium, hard)
        
        bot.edit_message_text(
            "سطح دشواری را انتخاب کنید:",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )
        return True

    if action == "friend":
        game = GoGame(call.from_user.id)
        game.mode = "friend"
        games[chat_id] = game
        
        markup = types.InlineKeyboardMarkup()
        join_btn = types.InlineKeyboardButton("پیوستن به بازی", callback_data="go_join")
        markup.add(join_btn)
        
        bot.edit_message_text(
            "منتظر پیوستن بازیکن دوم...",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )
        return True

    if action.startswith("diff_"):
        difficulty = action[5:]
        game = GoGame(call.from_user.id)
        game.mode = "bot"
        game.difficulty = difficulty
        game.player2 = "bot"
        games[chat_id] = game
        
        bot.edit_message_text(
            f"بازی شروع شد! شما مهره سیاه هستید.",
            chat_id,
            call.message.message_id,
            reply_markup=create_board_markup(game)
        )
        return True

    if action == "join":
        game = games.get(chat_id)
        if game and game.mode == "friend" and game.player2 is None:
            if call.from_user.id != game.player1:
                game.player2 = call.from_user.id
                bot.edit_message_text(
                    "بازی شروع شد!\n⚫: بازیکن اول\n⚪: بازیکن دوم",
                    chat_id,
                    call.message.message_id,
                    reply_markup=create_board_markup(game)
                )
        return True

    if action.startswith("move_"):
        game = games.get(chat_id)
        if not game:
            return True
            
        row, col = map(int, action[5:].split("_"))
        
        # Check if it's player's turn
        if game.mode == "friend":
            current_player_id = game.player1 if game.current_player == "⚫" else game.player2
            if call.from_user.id != current_player_id:
                bot.answer_callback_query(call.id, "نوبت شما نیست!")
                return True
        elif game.mode == "bot" and game.current_player == "⚪":
            bot.answer_callback_query(call.id, "نوبت ربات است!")
            return True

        if game.make_move(row, col):
            bot.edit_message_reply_markup(
                chat_id,
                call.message.message_id,
                reply_markup=create_board_markup(game)
            )
            
            # Bot's turn
            if game.mode == "bot" and game.current_player == "⚪":
                bot_move = game.ai_move()
                if bot_move:
                    game.make_move(bot_move[0], bot_move[1])
                    bot.edit_message_reply_markup(
                        chat_id,
                        call.message.message_id,
                        reply_markup=create_board_markup(game)
                    )
        else:
            bot.answer_callback_query(call.id, "حرکت غیرمجاز!")
        return True

    if action == "pass":
        game = games.get(chat_id)
        if game:
            game.pass_count += 1
            game.current_player = "⚪" if game.current_player == "⚫" else "⚫"
            
            if game.pass_count >= 2:
                # End game and calculate score
                score_black = game.captured_stones["⚫"]
                score_white = game.captured_stones["⚪"]
                winner = "⚫" if score_black > score_white else "⚪"
                
                bot.edit_message_text(
                    f"بازی تمام شد!\nامتیاز سیاه: {score_black}\nامتیاز سفید: {score_white}\nبرنده: {winner}",
                    chat_id,
                    call.message.message_id
                )
                del games[chat_id]
            else:
                bot.edit_message_reply_markup(
                    chat_id,
                    call.message.message_id,
                    reply_markup=create_board_markup(game)
                )
        return True

    if action == "resign":
        game = games.get(chat_id)
        if game:
            winner = "⚪" if game.current_player == "⚫" else "⚫"
            bot.edit_message_text(
                f"بازیکن {game.current_player} تسلیم شد!\nبرنده: {winner}",
                chat_id,
                call.message.message_id
            )
            del games[chat_id]
        return True

    return False
def show_tutorial(bot, chat_id):
    tutorial_text = """
🎮 آموزش بازی گو:

1️⃣ هدف بازی:
- محاصره کردن مهره‌های حریف
- کنترل بیشترین فضای ممکن در صفحه

2️⃣ قوانین اصلی:
• نوبتی مهره می‌گذارید (سیاه شروع می‌کند)
• مهره‌ها روی تقاطع خطوط قرار می‌گیرند
• مهره‌های محاصره شده حذف می‌شوند
• نمی‌توانید حرکتی انجام دهید که باعث خودکشی شود

3️⃣ نکات مهم:
• قانون Ko: نمی‌توانید وضعیت قبلی صفحه را تکرار کنید
• می‌توانید "Pass" کنید اگر حرکت مناسبی ندارید
• دو Pass متوالی = پایان بازی

4️⃣ امتیازدهی:
• هر مهره‌ای که حذف کردید: 1 امتیاز
• هر فضایی که محاصره کردید: 1 امتیاز

5️⃣ دکمه‌های بازی:
🔘 نقطه‌ها: محل‌های مجاز برای قرار دادن مهره
⚫ مهره سیاه
⚪ مهره سفید
▶️ Pass: رد کردن نوبت
🏳️ Resign: تسلیم شدن
"""
    markup = types.InlineKeyboardMarkup()
    start_game = types.InlineKeyboardButton("🎮 شروع بازی", callback_data="go_start")
    markup.add(start_game)
    
    bot.send_message(chat_id, tutorial_text, reply_markup=markup)
