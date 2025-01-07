from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import time

active_games = {}

def create_board():
    return [[" " for _ in range(3)] for _ in range(3)]

def create_keyboard(game_id):
    keyboard = InlineKeyboardMarkup()
    board = active_games[game_id]['board']
    
    for i in range(3):
        row = []
        for j in range(3):
            cell = board[i][j] if board[i][j] != " " else "·"
            row.append(InlineKeyboardButton(cell, callback_data=f"move_{game_id}_{i}_{j}"))
        keyboard.row(*row)
    return keyboard

def check_winner(board):
    for row in board:
        if row.count(row[0]) == 3 and row[0] != " ":
            return row[0]
    
    for col in range(3):
        if board[0][col] == board[1][col] == board[2][col] != " ":
            return board[0][col]
    
    if board[0][0] == board[1][1] == board[2][2] != " ":
        return board[0][0]
    if board[0][2] == board[1][1] == board[2][0] != " ":
        return board[0][2]
    
    if all(cell != " " for row in board for cell in row):
        return "Draw"
    
    return None

def start_game(bot, message):
    game_id = str(time.time())
    active_games[game_id] = {
        'board': create_board(),
        'players': {'X': None, 'O': None},
        'current_player': 'X',
        'chat_id': message.chat.id
    }
    
    keyboard = InlineKeyboardMarkup()
    join_button = InlineKeyboardButton("Join Game 🎮", callback_data=f"join_{game_id}")
    keyboard.add(join_button)
    
    sent = bot.send_message(
        message.chat.id,
        "🎲 New XO Game Started!\nClick to join:",
        reply_markup=keyboard
    )
    active_games[game_id]['message_id'] = sent.message_id

def handle_callback(bot, call):
    if call.data.startswith('join_'):
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
