from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time
import random

AI_DIFFICULTIES = {
    'easy': 1,
    'medium': 3, 
    'hard': 5
}

active_games = {}

def create_board():
    board = [[" " for _ in range(8)] for _ in range(8)]
    board[3][3] = "⚪"
    board[3][4] = "🔴"
    board[4][3] = "🔴" 
    board[4][4] = "⚪"
    return board

def create_keyboard(game_id):
    keyboard = InlineKeyboardMarkup()
    board = active_games[game_id]['board']
    
    for i in range(8):
        row = []
        for j in range(8):
            cell = board[i][j] if board[i][j] != " " else "·"
            row.append(InlineKeyboardButton(cell, callback_data=f"othello_{game_id}_{i}_{j}"))
        keyboard.row(*row)
    return keyboard

def is_valid_move(board, row, col, player):
    if board[row][col] != " ":
        return False
        
    directions = [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,-1), (1,-1), (-1,1)]
    player_piece = "🔴" if player == "B" else "⚪"
    opponent_piece = "⚪" if player == "B" else "🔴"
    
    for dx, dy in directions:
        x, y = row + dx, col + dy
        pieces_to_flip = []
        
        while 0 <= x < 8 and 0 <= y < 8 and board[x][y] == opponent_piece:
            pieces_to_flip.append((x,y))
            x, y = x + dx, y + dy
            
            if 0 <= x < 8 and 0 <= y < 8 and board[x][y] == player_piece:
                return True
                
    return False

def make_move(board, row, col, player):
    directions = [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,-1), (1,-1), (-1,1)]
    player_piece = "🔴" if player == "B" else "⚪"
    opponent_piece = "⚪" if player == "B" else "🔴"
    pieces_flipped = []
    
    board[row][col] = player_piece
    
    for dx, dy in directions:
        x, y = row + dx, col + dy
        pieces_to_flip = []
        
        while 0 <= x < 8 and 0 <= y < 8 and board[x][y] == opponent_piece:
            pieces_to_flip.append((x,y))
            x, y = x + dx, y + dy
            
            if 0 <= x < 8 and 0 <= y < 8 and board[x][y] == player_piece:
                for flip_x, flip_y in pieces_to_flip:
                    board[flip_x][flip_y] = player_piece
                    pieces_flipped.extend(pieces_to_flip)
                break
    
    return len(pieces_flipped) > 0

def count_pieces(board):
    red = sum(row.count("🔴") for row in board)
    white = sum(row.count("⚪") for row in board)
    return red, white

def has_valid_moves(board, player):
    for i in range(8):
        for j in range(8):
            if is_valid_move(board, i, j, player):
                return True
    return False

def get_ai_move(board, difficulty, player):
    valid_moves = []
    for i in range(8):
        for j in range(8):
            if is_valid_move(board, i, j, player):
                score = evaluate_move(board, i, j, player, difficulty)
                valid_moves.append((score, i, j))
    
    if not valid_moves:
        print("AI has no valid moves")  # Debug
        return None
        
    if difficulty == 'easy':
        move = random.choice(valid_moves)[1:]
    else:
        valid_moves.sort(reverse=True)
        move = valid_moves[0][1:]

    print(f"AI selected move: {move}")  # Debug
    return move

def evaluate_move(board, row, col, player, difficulty):
    temp_board = [r[:] for r in board]
    make_move(temp_board, row, col, player)
    
    weights = [
        [100, -20, 10, 5, 5, 10, -20, 100],
        [-20, -50, -2, -2, -2, -2, -50, -20],
        [10, -2, -1, -1, -1, -1, -2, 10],
        [5, -2, -1, -1, -1, -1, -2, 5],
        [5, -2, -1, -1, -1, -1, -2, 5],
        [10, -2, -1, -1, -1, -1, -2, 10],
        [-20, -50, -2, -2, -2, -2, -50, -20],
        [100, -20, 10, 5, 5, 10, -20, 100]
    ]
    
    score = weights[row][col]
    if difficulty == 'hard':
        black, white = count_pieces(temp_board)
        score += (black - white) * 10
        
    return score

def handle_ai_turn(bot, game_id):
    game = active_games[game_id]
    difficulty = game['difficulty']
    player = 'W'

    ai_move = get_ai_move(game['board'], difficulty, player)
    if ai_move is None:
        bot.send_message(game['chat_id'], "هوش مصنوعی حرکتی ندارد!")
        return

    row, col = ai_move
    make_move(game['board'], row, col, player)

    next_player = 'B'
    if has_valid_moves(game['board'], next_player):
        game['current_player'] = next_player
        black_count, white_count = count_pieces(game['board'])
        bot.send_message(
            game['chat_id'],
            f"🔴: {black_count} | ⚪: {white_count}\nنوبت: {'🔴' if next_player == 'B' else '⚪'}",
            reply_markup=create_keyboard(game_id)
        )
    else:
        black_count, white_count = count_pieces(game['board'])
        if black_count > white_count:
            winner_name = game['players']['B']['name']
            winner_piece = "🔴"
        elif white_count > black_count:
            winner_name = "Bot"
            winner_piece = "⚪"
        else:
            winner_name = "مساوی"
            winner_piece = "🤝"
        
        bot.send_message(
            game['chat_id'],
            f"🏆 بازی تمام شد!\n🔴 {game['players']['B']['name']}: {black_count}\n⚪ Bot: {white_count}\nبرنده: {winner_name} {winner_piece}"
        )
        del active_games[game_id]
