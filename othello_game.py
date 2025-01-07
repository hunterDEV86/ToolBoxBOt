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

def get_ai_move(board, difficulty, player):
    valid_moves = []
    for i in range(8):
        for j in range(8):
            if is_valid_move(board, i, j, player):
                score = evaluate_move(board, i, j, player, difficulty)
                valid_moves.append((score, i, j))
    
    if not valid_moves:
        return None
        
    if difficulty == 'easy':
        _, row, col = random.choice(valid_moves)
    else:
        _, row, col = max(valid_moves)
    return (row, col)

def evaluate_move(board, row, col, player, difficulty):
    temp_board = [row[:] for row in board]
    make_move(temp_board, row, col, player)
    
    weights = [
        [120, -20, 20, 5, 5, 20, -20, 120],
        [-20, -40, -5, -5, -5, -5, -40, -20],
        [20, -5, 15, 3, 3, 15, -5, 20],
        [5, -5, 3, 3, 3, 3, -5, 5],
        [5, -5, 3, 3, 3, 3, -5, 5],
        [20, -5, 15, 3, 3, 15, -5, 20],
        [-20, -40, -5, -5, -5, -5, -40, -20],
        [120, -20, 20, 5, 5, 20, -20, 120]
    ]
    
    score = weights[row][col]
    
    if difficulty in ['medium', 'hard']:
        black, white = count_pieces(temp_board)
        piece_diff = black - white if player == 'B' else white - black
        score += piece_diff * (10 if difficulty == 'hard' else 5)
        
    return score

def start_game(bot, message, vs_ai=False, difficulty=None):
    game_id = str(time.time())
    active_games[game_id] = {
        'board': create_board(),
        'players': {'B': None, 'W': None},
        'current_player': 'B',
        'chat_id': message.chat.id,
        'vs_ai': vs_ai,
        'difficulty': difficulty,
        'message_id': None
    }
    
    if vs_ai:
        active_games[game_id]['players']['B'] = {
            'id': message.from_user.id,
            'name': message.from_user.first_name
        }
        active_games[game_id]['players']['W'] = {
            'id': 'AI',
            'name': 'Bot'
        }
        sent = bot.send_message(
            message.chat.id,
            f"🎮 بازی با هوش مصنوعی (سطح {difficulty}) شروع شد!\n🔴 {message.from_user.first_name} vs ⚪ Bot\n\nنوبت: 🔴",
            reply_markup=create_keyboard(game_id)
        )
        active_games[game_id]['message_id'] = sent.message_id

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

def handle_ai_turn(game, bot, chat_id, message_id):
    ai_move = get_ai_move(game['board'], game['difficulty'], 'W')
    
    if ai_move:
        row, col = ai_move
        make_move(game['board'], row, col, 'W')
        game['current_player'] = 'B'
        
        black_count, white_count = count_pieces(game['board'])
        
        bot.edit_message_text(
            f"🔴: {black_count} | ⚪: {white_count}\nنوبت: 🔴",
            chat_id,
            message_id,
            reply_markup=create_keyboard(game['game_id'])
        )
        
        return True
    return False

def show_game_menu(bot, message):
    keyboard = InlineKeyboardMarkup(row_width=2)
    
    vs_friend = InlineKeyboardButton("بازی با دوست 👥", callback_data="othello_mode_friend")
    
    vs_ai_easy = InlineKeyboardButton("بات - آسان 🤖", callback_data="othello_mode_ai_easy")
    vs_ai_medium = InlineKeyboardButton("بات - متوسط 🤖", callback_data="othello_mode_ai_medium")
    vs_ai_hard = InlineKeyboardButton("بات - سخت 🤖", callback_data="othello_mode_ai_hard")
    
    keyboard.add(vs_friend)
    keyboard.add(vs_ai_easy, vs_ai_medium, vs_ai_hard)
    
    bot.send_message(
        message.chat.id,
        "🎮 لطفا حالت بازی را انتخاب کنید:",
        reply_markup=keyboard
    )

def handle_callback(bot, call):
    if call.data.startswith('othello_mode_'):
        mode = call.data.split('_')[2]
        if mode == 'friend':
            start_game(bot, call.message)
        elif mode.startswith('ai'):
            difficulty = mode.replace('ai_', '')
            start_game(bot, call.message, vs_ai=True, difficulty=difficulty)
        return True
    if call.data.startswith('othello_join_'):
        game_id = call.data.split('_')[2]
        if game_id not in active_games:
            bot.answer_callback_query(call.id, "بازی پیدا نشد!")
            return True
            
        game = active_games[game_id]
        player_name = call.from_user.first_name
        
        if game['players']['B'] is None:
            game['players']['B'] = {'id': call.from_user.id, 'name': player_name}
            bot.edit_message_text(
                f"✅ {player_name} مهره قرمز را انتخاب کرد\n⏳ منتظر بازیکن دوم...",
                call.message.chat.id,
                game['message_id'],
                reply_markup=call.message.reply_markup
            )
            bot.answer_callback_query(call.id, "شما مهره سیاه هستید!")
            
        elif game['players']['W'] is None and game['players']['B']['id'] != call.from_user.id:
            game['players']['W'] = {'id': call.from_user.id, 'name': player_name}
            bot.edit_message_text(
                f"🎮 بازی شروع شد!\n🔴 {game['players']['B']['name']}\n⚪ {game['players']['W']['name']}\n\nنوبت: 🔴",
                call.message.chat.id,
                game['message_id'],
                reply_markup=create_keyboard(game_id)
            )
            bot.answer_callback_query(call.id, "شما مهره سفید هستید!")
            
        else:
            bot.answer_callback_query(call.id, "بازی پر است!")
        return True
        
    elif call.data.startswith('othello_'):
        _, game_id, row, col = call.data.split('_')
        row, col = int(row), int(col)
        
        if game_id not in active_games:
            bot.answer_callback_query(call.id, "بازی پیدا نشد!")
            return True
            
        game = active_games[game_id]
        current_player = 'B' if game['current_player'] == 'B' else 'W'
        
        if call.from_user.id != game['players'][current_player]['id']:
            bot.answer_callback_query(call.id, "نوبت شما نیست!")
            return True
            
        if not is_valid_move(game['board'], row, col, current_player):
            bot.answer_callback_query(call.id, "حرکت نامعتبر!")
            return True
            
        make_move(game['board'], row, col, current_player)
        next_player = 'W' if current_player == 'B' else 'B'
        
        if has_valid_moves(game['board'], next_player):
            game['current_player'] = next_player
            black_count, white_count = count_pieces(game['board'])
            bot.edit_message_text(
                f"🔴: {black_count} | ⚪: {white_count}\nنوبت: {'🔴' if next_player == 'B' else '⚪'}",
                call.message.chat.id,
                game['message_id'],
                reply_markup=create_keyboard(game_id)
            )
        else:
            black_count, white_count = count_pieces(game['board'])
            if black_count > white_count:
                winner_name = game['players']['B']['name']
                winner_piece = "🔴"
            elif white_count > black_count:
                winner_name = game['players']['W']['name']
                winner_piece = "⚪"
            else:
                winner_name = "مساوی"
                winner_piece = "🤝"
            
            bot.edit_message_text(
                f"🏆 بازی تمام شد!\n🔴 {game['players']['B']['name']}: {black_count}\n⚪ {game['players']['W']['name']}: {white_count}\nبرنده: {winner_name} {winner_piece}",
                call.message.chat.id,
                game['message_id'],
                reply_markup=create_keyboard(game_id)
            )
            del active_games[game_id]
        
        if game['vs_ai'] and next_player == 'W':
            ai_move = get_ai_move(game['board'], game['difficulty'], 'W')
            
            if ai_move:
                ai_row, ai_col = ai_move
                make_move(game['board'], ai_row, ai_col, 'W')
                next_player = 'B'
                
                black_count, white_count = count_pieces(game['board'])
                
                bot.edit_message_text(
                    f"🔴: {black_count} | ⚪: {white_count}\nنوبت: 🔴",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=create_keyboard(game_id)
                )
        
        return True
    
    return False
