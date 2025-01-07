from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

active_games = {}

def create_board():
    board = [[" " for _ in range(5)] for _ in range(5)]
    # قرار دادن مهره‌های اولیه در مرکز
    board[2][2] = "⚪"
    board[2][1] = "⚫"
    board[1][2] = "⚫"
    board[1][1] = "⚪"
    return board

def create_keyboard(game_id):
    keyboard = InlineKeyboardMarkup()
    board = active_games[game_id]['board']
    
    for i in range(5):
        row = []
        for j in range(5):
            cell = board[i][j] if board[i][j] != " " else "·"
            row.append(InlineKeyboardButton(cell, callback_data=f"othello_{game_id}_{i}_{j}"))
        keyboard.row(*row)
    return keyboard

def is_valid_move(board, row, col, player):
    if board[row][col] != " ":
        return False
        
    directions = [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,-1), (1,-1), (-1,1)]
    player_piece = "⚫" if player == "B" else "⚪"
    opponent_piece = "⚪" if player == "B" else "⚫"
    
    for dx, dy in directions:
        x, y = row + dx, col + dy
        pieces_to_flip = []
        
        while 0 <= x < 5 and 0 <= y < 5 and board[x][y] == opponent_piece:
            pieces_to_flip.append((x,y))
            x, y = x + dx, y + dy
            
            if 0 <= x < 5 and 0 <= y < 5 and board[x][y] == player_piece:
                return True
                
    return False

def make_move(board, row, col, player):
    directions = [(0,1), (1,0), (0,-1), (-1,0), (1,1), (-1,-1), (1,-1), (-1,1)]
    player_piece = "⚫" if player == "B" else "⚪"
    opponent_piece = "⚪" if player == "B" else "⚫"
    pieces_flipped = []
    
    board[row][col] = player_piece
    
    for dx, dy in directions:
        x, y = row + dx, col + dy
        pieces_to_flip = []
        
        while 0 <= x < 5 and 0 <= y < 5 and board[x][y] == opponent_piece:
            pieces_to_flip.append((x,y))
            x, y = x + dx, y + dy
            
            if 0 <= x < 5 and 0 <= y < 5 and board[x][y] == player_piece:
                for flip_x, flip_y in pieces_to_flip:
                    board[flip_x][flip_y] = player_piece
                    pieces_flipped.extend(pieces_to_flip)
                break
    
    return len(pieces_flipped) > 0

def count_pieces(board):
    black = sum(row.count("⚫") for row in board)
    white = sum(row.count("⚪") for row in board)
    return black, white

def has_valid_moves(board, player):
    for i in range(5):
        for j in range(5):
            if is_valid_move(board, i, j, player):
                return True
    return False

def start_game(bot, message):
    game_id = str(time.time())
    active_games[game_id] = {
        'board': create_board(),
        'players': {'B': None, 'W': None},
        'current_player': 'B',
        'chat_id': message.chat.id
    }
    
    keyboard = InlineKeyboardMarkup()
    join_button = InlineKeyboardButton("Join Game 🎮", callback_data=f"othello_join_{game_id}")
    keyboard.add(join_button)
    
    sent = bot.send_message(
        message.chat.id,
        "🎲 بازی اوتلو 5×5 شروع شد!\nبرای پیوستن کلیک کنید:",
        reply_markup=keyboard
    )
    active_games[game_id]['message_id'] = sent.message_id

def handle_callback(bot, call):
    if call.data.startswith('othello_join_'):
        game_id = call.data.split('_')[2]
        if game_id not in active_games:
            bot.answer_callback_query(call.id, "بازی پیدا نشد!")
            return True
            
        game = active_games[game_id]
        player_name = call.from_user.first_name
        
        if game['players']['B'] is None:
            game['players']['B'] = call.from_user.id
            bot.edit_message_text(
                f"✅ {player_name} مهره سیاه را انتخاب کرد\n⏳ منتظر بازیکن دوم...",
                call.message.chat.id,
                game['message_id'],
                reply_markup=call.message.reply_markup
            )
            bot.answer_callback_query(call.id, "شما مهره سیاه هستید!")
            
        elif game['players']['W'] is None and game['players']['B'] != call.from_user.id:
            game['players']['W'] = call.from_user.id
            bot.edit_message_text(
                f"🎮 بازی شروع شد!\n⚫: {game['players']['B']}\n⚪: {player_name}\n\nنوبت: ⚫",
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
        
        if call.from_user.id != game['players'][current_player]:
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
                f"⚫: {black_count} | ⚪: {white_count}\nنوبت: {'⚫' if next_player == 'B' else '⚪'}",
                call.message.chat.id,
                game['message_id'],
                reply_markup=create_keyboard(game_id)
            )
        else:
            black_count, white_count = count_pieces(game['board'])
            winner = "⚫" if black_count > white_count else "⚪" if white_count > black_count else "مساوی"
            bot.edit_message_text(
                f"🏆 بازی تمام شد!\n⚫: {black_count} | ⚪: {white_count}\nبرنده: {winner}",
                call.message.chat.id,
                game['message_id'],
                reply_markup=create_keyboard(game_id)
            )
            del active_games[game_id]
        return True
        
    return False
