from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

active_games = {}
def create_board(size=3):
    return [[" " for _ in range(size)] for _ in range(size)]

def create_keyboard(game_id):
    keyboard = InlineKeyboardMarkup()
    game = active_games[game_id]
    board = game['board']
    size = len(board)
    
    for i in range(size):
        row = []
        for j in range(size):
            cell = board[i][j] if board[i][j] != " " else "·"
            row.append(InlineKeyboardButton(cell, callback_data=f"move_{game_id}_{i}_{j}"))
        keyboard.row(*row)
    return keyboard

def check_winner(board):
    size = len(board)
    
    # Check rows
    for row in board:
        if row.count(row[0]) == size and row[0] != " ":
            return row[0]
    
    # Check columns
    for col in range(size):
        if all(board[row][col] == board[0][col] != " " for row in range(size)):
            return board[0][col]
    
    # Check diagonals
    if all(board[i][i] == board[0][0] != " " for i in range(size)):
        return board[0][0]
    if all(board[i][size-1-i] == board[0][size-1] != " " for i in range(size)):
        return board[0][size-1]
    
    if all(cell != " " for row in board for cell in row):
        return "Draw"
    
    return None

def start_game(bot, message):
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("3×3", callback_data="size_3"),
        InlineKeyboardButton("4×4", callback_data="size_4"),
        InlineKeyboardButton("5×5", callback_data="size_5")
    )
    
    bot.send_message(
        message.chat.id,
        "🎲 انتخاب سایز بازی:",
        reply_markup=keyboard
    )

def handle_callback(bot, call):
    if call.data.startswith('size_'):
        size = int(call.data.split('_')[1])
        game_id = str(time.time())
        active_games[game_id] = {
            'board': create_board(size),
            'players': {'X': None, 'O': None},
            'current_player': 'X',
            'chat_id': call.message.chat.id,
            'size': size
        }
        
        keyboard = InlineKeyboardMarkup()
        join_button = InlineKeyboardButton("Join Game 🎮", callback_data=f"join_{game_id}")
        keyboard.add(join_button)
        
        sent = bot.edit_message_text(
            f"🎲 بازی {size}×{size} شروع شد!\nبرای پیوستن کلیک کنید:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
        active_games[game_id]['message_id'] = sent.message_id
        return True
    elif call.data.startswith('join_'):
        game_id = call.data.split('_')[1]
        if game_id not in active_games:
            bot.answer_callback_query(call.id, "Game not found!")
            return True
            
        game = active_games[game_id]
        player_name = call.from_user.first_name
        
        if game['players']['X'] is None:
            game['players']['X'] = call.from_user.id
            bot.edit_message_text(
                f"✅ {player_name} joined as X\n⏳ Waiting for player O...",
                call.message.chat.id,
                game['message_id'],
                reply_markup=call.message.reply_markup
            )
            bot.answer_callback_query(call.id, "You joined as X!")
            
        elif game['players']['O'] is None and game['players']['X'] != call.from_user.id:
            game['players']['O'] = call.from_user.id
            bot.edit_message_text(
                f"🎮 Game Started!\nX: {game['players']['X']}\nO: {player_name}\n\nX's turn!",
                call.message.chat.id,
                game['message_id'],
                reply_markup=create_keyboard(game_id)
            )
            bot.answer_callback_query(call.id, "You joined as O!")
            
        else:
            bot.answer_callback_query(call.id, "Game is full!")
        return True
            
    elif call.data.startswith('move_'):
        _, game_id, row, col = call.data.split('_')
        row, col = int(row), int(col)
        
        if game_id not in active_games:
            bot.answer_callback_query(call.id, "Game not found!")
            return True
            
        game = active_games[game_id]
        
        if call.from_user.id not in [game['players']['X'], game['players']['O']]:
            bot.answer_callback_query(call.id, "You're not in this game!")
            return True
            
        current_symbol = 'X' if game['players']['X'] == call.from_user.id else 'O'
        if current_symbol != game['current_player']:
            bot.answer_callback_query(call.id, "Not your turn!")
            return True
            
        if game['board'][row][col] == " ":
            game['board'][row][col] = current_symbol
            game['current_player'] = 'O' if current_symbol == 'X' else 'X'
            
            winner = check_winner(game['board'])
            if winner:
                if winner == "Draw":
                    msg = "🤝 Game Over - It's a Draw!"
                else:
                    msg = f"🏆 Game Over - {winner} Wins!"
                bot.edit_message_text(
                    msg,
                    call.message.chat.id,
                    game['message_id'],
                    reply_markup=create_keyboard(game_id)
                )
                del active_games[game_id]
            else:
                bot.edit_message_text(
                    f"Turn: {game['current_player']}",
                    call.message.chat.id,
                    game['message_id'],
                    reply_markup=create_keyboard(game_id)
                )
            bot.answer_callback_query(call.id)
        else:
            bot.answer_callback_query(call.id, "Cell already taken!")
        return True
    return False
