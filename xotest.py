import telebot
from telebot import types
import uuid

# Initialize the bot with your token
bot = telebot.TeleBot('YOUR_BOT_TOKEN_HERE')

# Dictionary to store active games
active_games = {}

# Function to create a game board of specified size
def create_board(size):
    """Create a game board filled with empty spaces."""
    return [[" " for _ in range(size)] for _ in range(size)]

# Function to create an inline keyboard for the game
def create_keyboard(game_id):
    """Create an inline keyboard for the game board and restart button."""
    game = active_games[game_id]
    board = game['board']
    size = len(board)
    keyboard = types.InlineKeyboardMarkup(row_width=size)
    
    # Create buttons for each cell in the board
    for i in range(size):
        row = []
        for j in range(size):
            cell = board[i][j] if board[i][j] != " " else "·"
            row.append(types.InlineKeyboardButton(cell, callback_data=f"xo_move_{game_id}_{i}_{j}"))
        keyboard.row(*row)
    
    # Add a restart button
    restart_btn = types.InlineKeyboardButton("🔄 شروع مجدد", callback_data=f"xo_restart_{game_id}")
    keyboard.row(restart_btn)
    
    return keyboard

# Function to check for a winner or a draw
def check_winner(board):
    """Check if there is a winner or the game is a draw."""
    size = len(board)
    
    # Check rows and columns
    for i in range(size):
        if all(cell == board[i][0] and cell != " " for cell in board[i]):
            return board[i][0]
        if all(board[j][i] == board[0][i] and board[j][i] != " " for j in range(size)):
            return board[0][i]
    
    # Check diagonals
    if all(board[i][i] == board[0][0] and board[i][i] != " " for i in range(size)):
        return board[0][0]
    if all(board[i][size-1-i] == board[0][size-1] and board[i][size-1-i] != " " for i in range(size)):
        return board[0][size-1]
    
    # Check for a draw
    if all(cell != " " for row in board for cell in row):
        return "draw"
    
    return None

# Function to start a new game
def start_game(message):
    """Handle the /start command and let the user choose the game size."""
    markup = types.InlineKeyboardMarkup(row_width=3)
    size3_btn = types.InlineKeyboardButton("3x3", callback_data="xo_size_3")
    size4_btn = types.InlineKeyboardButton("4x4", callback_data="xo_size_4")
    size5_btn = types.InlineKeyboardButton("5x5", callback_data="xo_size_5")
    markup.add(size3_btn, size4_btn, size5_btn)
    
    bot.send_message(
        message.chat.id,
        "لطفا سایز بازی را انتخاب کنید:",
        reply_markup=markup
    )

# Function to handle callback queries
def handle_callback(call):
    """Handle various callback queries from the game buttons."""
    if call.data.startswith('xo_size_'):
        # Handle game size selection
        size = int(call.data.split('_')[2])
        game_id = uuid.uuid4().hex  # Generate a unique game ID
        active_games[game_id] = {
            'board': create_board(size),
            'current_player': "X",
            'players': {"X": call.from_user.id, "O": None},
            'size': size,
            'waiting_for_player': True
        }
        
        markup = types.InlineKeyboardMarkup()
        join_btn = types.InlineKeyboardButton("🎮 پیوستن به بازی", callback_data=f"xo_join_{game_id}")
        markup.add(join_btn)
        
        bot.edit_message_text(
            f"بازی {size}x{size} ایجاد شد! منتظر بازیکن دوم...",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=markup
        )
    
    elif call.data.startswith('xo_join_'):
        # Handle joining the game
        game_id = call.data.split('_')[2]
        game = active_games.get(game_id)
        
        if not game:
            bot.answer_callback_query(call.id, "بازی پیدا نشد!")
            return
        
        if game['players']["O"] is not None:
            bot.answer_callback_query(call.id, "بازی پر است!")
            return
        
        if call.from_user.id == game['players']["X"]:
            bot.answer_callback_query(call.id, "شما نمی‌توانید به بازی خود بپیوندید!")
            return
        
        game['players']["O"] = call.from_user.id
        game['waiting_for_player'] = False
        
        bot.edit_message_text(
            f"بازی شروع شد!\nX: {call.from_user.first_name}\nO: {bot.get_chat(game['players']['X']).first_name}\n\nنوبت: X",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_keyboard(game_id)
        )
    
    elif call.data.startswith('xo_move_'):
        # Handle player moves
        _, _, game_id, row, col = call.data.split('_')
        row, col = int(row), int(col)
        game = active_games.get(game_id)
        
        if not game:
            bot.answer_callback_query(call.id, "بازی پیدا نشد!")
            return
        
        if game['waiting_for_player']:
            bot.answer_callback_query(call.id, "منتظر بازیکن دوم...")
            return
        
        if call.from_user.id != game['players'][game['current_player']]:
            bot.answer_callback_query(call.id, "نوبت شما نیست!")
            return
        
        if game['board'][row][col] != " ":
            bot.answer_callback_query(call.id, "این خانه قبلا انتخاب شده!")
            return
        
        game['board'][row][col] = game['current_player']
        winner = check_winner(game['board'])
        
        if winner:
            if winner == "draw":
                bot.edit_message_text(
                    "بازی مساوی شد!",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=create_keyboard(game_id)
                )
            else:
                bot.edit_message_text(
                    f"بازیکن {winner} برنده شد!",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=create_keyboard(game_id)
                )
            del active_games[game_id]
        else:
            game['current_player'] = "O" if game['current_player'] == "X" else "X"
            bot.edit_message_text(
                f"نوبت: {game['current_player']}",
                call.message.chat.id,
                call.message.message_id,
                reply_markup=create_keyboard(game_id)
            )
    
    elif call.data.startswith('xo_restart_'):
        # Handle game restart
        game_id = call.data.split('_')[2]
        game = active_games.get(game_id)
        
        if not game:
            bot.answer_callback_query(call.id, "بازی پیدا نشد!")
            return
        
        game['board'] = create_board(game['size'])
        game['current_player'] = "X"
        bot.edit_message_text(
            "بازی مجدد شروع شد! نوبت: X",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_keyboard(game_id)
        )

# Set up message and callback handlers
@bot.message_handler(commands=['start'])
def handle_start(message):
    """Handle the /start command."""
    start_game(message)

@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    """Handle all callback queries."""
    handle_callback(call)

# Start the bot
bot.polling()