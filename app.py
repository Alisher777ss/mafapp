from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import random
import uuid
from datetime import datetime
import time
import re

app = Flask(__name__)
app.secret_key = 'mafia-game-secret-key-' + str(uuid.uuid4())

games = {}

class MafiaGame:
    def __init__(self, room_code, host_id, host_name):
        self.room_code = room_code
        self.host_id = host_id
        self.players = []
        self.phase = "waiting"
        self.day_number = 0
        self.votes = {}
        self.night_target = None
        self.host_name = host_name
        self.last_eliminated = None
        self.last_eliminated_by = None
        self.game_log = []
        self.phase_start_time = None
        self.phase_duration = 60
        self.selected_target = None
        self.winner = None
        self.detective_check = None
        self.doctor_save = None
        self.detective_result = {}
        self.chat_messages = []
        self.chat_id_counter = 0
        
    def add_player(self, player_id, name):
        if any(p['id'] == player_id for p in self.players):
            return False
        player = {
            'id': player_id,
            'name': name,
            'role': None,
            'alive': True
        }
        self.players.append(player)
        self.game_log.append(f"{name} o'yinga qo'shildi")
        return True
        
    def assign_roles(self):
        random.shuffle(self.players)
        num_players = len(self.players)
        num_mafia = max(1, num_players // 3)
        
        for i in range(num_mafia):
            self.players[i]['role'] = 'mafia'
        
        has_detective = False
        has_doctor = False
        
        if num_players >= 5 and num_players - num_mafia > 0:
            self.players[num_mafia]['role'] = 'detective'
            has_detective = True
            
        if num_players >= 7 and num_players - num_mafia > 1:
            offset = 1 if has_detective else 0
            self.players[num_mafia + offset]['role'] = 'doctor'
            has_doctor = True
            
        start_idx = num_mafia + (1 if has_detective else 0) + (1 if has_doctor else 0)
        for i in range(start_idx, num_players):
            self.players[i]['role'] = 'civilian'
            
        self.phase = "role_reveal"
        self.day_number = 1
        self.phase_start_time = time.time()
        
        role_summary = f"O'yin boshlandi! {num_mafia} ta mafia"
        if has_detective:
            role_summary += ", 1 ta komissar"
        if has_doctor:
            role_summary += ", 1 ta doktor"
        num_civilians = num_players - num_mafia - (1 if has_detective else 0) - (1 if has_doctor else 0)
        if num_civilians > 0:
            role_summary += f", {num_civilians} ta oddiy fuqaro"
        self.game_log.append(role_summary)
    
    def get_time_remaining(self):
        if not self.phase_start_time:
            return 0
        elapsed = time.time() - self.phase_start_time
        remaining = max(0, self.phase_duration - int(elapsed))
        return remaining
        
    def vote(self, voter_id, target_id):
        if self.phase != "voting":
            return False
        voter = self.get_player(voter_id)
        if not voter or not voter['alive']:
            return False
        self.votes[voter_id] = target_id
        return True
        
    def get_player(self, player_id):
        return next((p for p in self.players if p['id'] == player_id), None)
        
    def count_votes(self):
        if not self.votes:
            return None
        vote_counts = {}
        for target_id in self.votes.values():
            vote_counts[target_id] = vote_counts.get(target_id, 0) + 1
        return max(vote_counts, key=vote_counts.get)
        
    def eliminate_player(self, player_id, killed_by='vote'):
        player = self.get_player(player_id)
        if player:
            player['alive'] = False
            self.last_eliminated = player['name']
            self.last_eliminated_by = killed_by
            if killed_by == 'mafia':
                self.game_log.append(f"{player['name']} don tomonidan o'ldirildi")
            else:
                self.game_log.append(f"{player['name']} ovoz orqali o'yindan chiqarildi (Rol: {player['role']})")
            return player
        return None
        
    def check_win_condition(self):
        alive_mafia = [p for p in self.players if p['alive'] and p['role'] == 'mafia']
        alive_good = [p for p in self.players if p['alive'] and p['role'] in ['civilian', 'detective', 'doctor']]
        
        if not alive_mafia:
            self.phase = "game_over"
            self.winner = "civilian"
            self.game_log.append("Oddiy fuqarolar g'alaba qozondi!")
            return "civilian"
        elif len(alive_mafia) >= len(alive_good):
            self.phase = "game_over"
            self.winner = "mafia"
            self.game_log.append("Mafiya g'alaba qozondi!")
            return "mafia"
        return None
        
    def next_phase(self):
        self.phase_start_time = time.time()
        if self.phase == "role_reveal":
            self.phase = "night"
        elif self.phase == "night":
            self.phase = "day"
            self.selected_target = None
            self.detective_check = None
            self.doctor_save = None
        elif self.phase == "day":
            self.phase = "voting"
        elif self.phase == "voting":
            self.votes = {}
            self.selected_target = None
            winner = self.check_win_condition()
            if not winner:
                self.day_number += 1
                self.phase = "night"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_game', methods=['POST'])
def create_game():
    data = request.json
    player_name = data.get('name')
    if not player_name:
        return jsonify({'error': 'Ismingizni kiriting'}), 400
        
    room_code = str(uuid.uuid4())[:6].upper()
    player_id = str(uuid.uuid4())
    
    game = MafiaGame(room_code, player_id, player_name)
    game.add_player(player_id, player_name)
    games[room_code] = game
    
    session['player_id'] = player_id
    session['room_code'] = room_code
    
    return jsonify({
        'room_code': room_code,
        'player_id': player_id
    })

@app.route('/join_game', methods=['POST'])
def join_game():
    data = request.json
    room_code = data.get('room_code', '').upper()
    player_name = data.get('name')
    
    if not room_code or not player_name:
        return jsonify({'error': 'Xona kodi va ismingizni kiriting'}), 400
        
    game = games.get(room_code)
    if not game:
        return jsonify({'error': 'Xona topilmadi'}), 404
        
    if game.phase != "waiting":
        return jsonify({'error': "O'yin allaqachon boshlangan"}), 400
        
    player_id = str(uuid.uuid4())
    if not game.add_player(player_id, player_name):
        return jsonify({'error': 'Xatolik yuz berdi'}), 400
        
    session['player_id'] = player_id
    session['room_code'] = room_code
    
    return jsonify({
        'room_code': room_code,
        'player_id': player_id
    })

@app.route('/game/<room_code>')
def game_page(room_code):
    game = games.get(room_code.upper())
    if not game:
        return redirect(url_for('index'))
    return render_template('game.html', room_code=room_code.upper())

@app.route('/game_state/<room_code>')
def game_state(room_code):
    game = games.get(room_code.upper())
    if not game:
        return jsonify({'error': 'Xona topilmadi'}), 404
        
    player_id = session.get('player_id')
    player = game.get_player(player_id) if player_id else None
    
    alive_players = [{'id': p['id'], 'name': p['name'], 'alive': p['alive']} 
                     for p in game.players]
    
    show_target = (player and player['role'] == 'mafia' and game.phase == 'night') if game.selected_target else False
    
    detective_result = None
    if player and player_id in game.detective_result:
        detective_result = game.detective_result[player_id]
    
    return jsonify({
        'phase': game.phase,
        'day_number': game.day_number,
        'players': alive_players,
        'player_role': player['role'] if player else None,
        'player_alive': player['alive'] if player else False,
        'player_id': player_id,
        'last_eliminated': game.last_eliminated,
        'last_eliminated_by': game.last_eliminated_by,
        'game_log': game.game_log[-5:],
        'is_host': player_id == game.host_id,
        'time_remaining': game.get_time_remaining(),
        'selected_target': game.selected_target if show_target else None,
        'player_vote': game.votes.get(player_id) if game.phase == 'voting' else None,
        'winner': game.winner,
        'detective_result': detective_result,
        'detective_check': game.detective_check if player and player['role'] == 'detective' else None,
        'doctor_save': game.doctor_save if player and player['role'] == 'doctor' else None
    })

@app.route('/start_game/<room_code>', methods=['POST'])
def start_game(room_code):
    game = games.get(room_code.upper())
    if not game:
        return jsonify({'error': 'Xona topilmadi'}), 404
    
    player_id = session.get('player_id')
    if player_id != game.host_id:
        return jsonify({'error': 'Faqat host o\'yinni boshlashi mumkin'}), 403
        
    if len(game.players) < 3:
        return jsonify({'error': "Kamida 3 ta o'yinchi kerak"}), 400
        
    game.assign_roles()
    return jsonify({'success': True})

@app.route('/night_action/<room_code>', methods=['POST'])
def night_action(room_code):
    game = games.get(room_code.upper())
    if not game or game.phase != "night":
        return jsonify({'error': 'Noto\'g\'ri bosqich'}), 400
        
    data = request.json
    target_id = data.get('target_id')
    player_id = session.get('player_id')
    
    player = game.get_player(player_id)
    if not player or player['role'] != 'mafia' or not player['alive']:
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    target = game.get_player(target_id)
    if not target or not target['alive']:
        return jsonify({'error': 'Noto\'g\'ri nishon'}), 400
        
    game.night_target = target_id
    game.selected_target = target_id
    return jsonify({'success': True})

@app.route('/detective_action/<room_code>', methods=['POST'])
def detective_action(room_code):
    game = games.get(room_code.upper())
    if not game or game.phase != "night":
        return jsonify({'error': 'Noto\'g\'ri bosqich'}), 400
        
    data = request.json
    target_id = data.get('target_id')
    player_id = session.get('player_id')
    
    player = game.get_player(player_id)
    if not player or player['role'] != 'detective' or not player['alive']:
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    target = game.get_player(target_id)
    if not target or not target['alive']:
        return jsonify({'error': 'Noto\'g\'ri nishon'}), 400
        
    game.detective_check = target_id
    is_mafia = target['role'] == 'mafia'
    game.detective_result[player_id] = {
        'target_name': target['name'],
        'is_mafia': is_mafia
    }
    return jsonify({'success': True})

@app.route('/doctor_action/<room_code>', methods=['POST'])
def doctor_action(room_code):
    game = games.get(room_code.upper())
    if not game or game.phase != "night":
        return jsonify({'error': 'Noto\'g\'ri bosqich'}), 400
        
    data = request.json
    target_id = data.get('target_id')
    player_id = session.get('player_id')
    
    player = game.get_player(player_id)
    if not player or player['role'] != 'doctor' or not player['alive']:
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    target = game.get_player(target_id)
    if not target or not target['alive']:
        return jsonify({'error': 'Noto\'g\'ri nishon'}), 400
        
    game.doctor_save = target_id
    return jsonify({'success': True})

@app.route('/execute_night/<room_code>', methods=['POST'])
def execute_night(room_code):
    game = games.get(room_code.upper())
    if not game or game.phase != "night":
        return jsonify({'error': 'Noto\'g\'ri bosqich'}), 400
    
    player_id = session.get('player_id')
    if player_id != game.host_id:
        return jsonify({'error': 'Faqat host bosqichni o\'zgartirishi mumkin'}), 403
        
    if game.night_target:
        if game.doctor_save and game.doctor_save == game.night_target:
            target = game.get_player(game.night_target)
            if target:
                game.game_log.append(f"Doktor {target['name']}ni qutqardi!")
        else:
            game.eliminate_player(game.night_target, killed_by='mafia')
        game.night_target = None
        
    winner = game.check_win_condition()
    if not winner:
        game.next_phase()
        
    return jsonify({'success': True})

@app.route('/vote/<room_code>', methods=['POST'])
def vote(room_code):
    game = games.get(room_code.upper())
    if not game or game.phase != "voting":
        return jsonify({'error': 'Noto\'g\'ri bosqich'}), 400
        
    data = request.json
    target_id = data.get('target_id')
    player_id = session.get('player_id')
    
    if not game.vote(player_id, target_id):
        return jsonify({'error': 'Ovoz berishda xatolik'}), 400
    
    game.selected_target = target_id
    return jsonify({'success': True})

@app.route('/execute_vote/<room_code>', methods=['POST'])
def execute_vote(room_code):
    game = games.get(room_code.upper())
    if not game or game.phase != "voting":
        return jsonify({'error': 'Noto\'g\'ri bosqich'}), 400
    
    player_id = session.get('player_id')
    if player_id != game.host_id:
        return jsonify({'error': 'Faqat host ovozlarni hisoblashi mumkin'}), 403
        
    eliminated_id = game.count_votes()
    if eliminated_id:
        game.eliminate_player(eliminated_id)
        
    winner = game.check_win_condition()
    if not winner:
        game.next_phase()
        
    return jsonify({'success': True})

@app.route('/next_phase/<room_code>', methods=['POST'])
def next_phase(room_code):
    game = games.get(room_code.upper())
    if not game:
        return jsonify({'error': 'Xona topilmadi'}), 404
    
    player_id = session.get('player_id')
    if player_id != game.host_id:
        return jsonify({'error': 'Faqat host bosqichni o\'zgartirishi mumkin'}), 403
        
    game.next_phase()
    return jsonify({'success': True})

BANNED_PATTERNS = [
    r'\b(men|я|i am|i\'m)\s*[-,.]?\s*(mafiya|mafia|мафия|mafiyaman)\b',
    r'\b(men|я|i am|i\'m)\s*[-,.]?\s*(aholi|fuqaro|civilian|мирный|житель|aholiman|fuqaroman)\b',
    r'\b(men|я|i am|i\'m)\s*[-,.]?\s*(komissar|detective|комиссар|детектив|komissarman)\b',
    r'\b(men|я|i am|i\'m)\s*[-,.]?\s*(doktor|doctor|врач|док|doktorman)\b',
    r'\b(mafiyaman|komissarman|doktorman|aholiman|fuqaroman)\b',
    r'\b(я|i\'m|i am)\s+(mafia|detective|doctor|civilian)\b',
]

def is_role_claim(message):
    message_lower = message.lower()
    for pattern in BANNED_PATTERNS:
        if re.search(pattern, message_lower, re.IGNORECASE):
            return True
    return False

@app.route('/chat/<room_code>')
def get_chat(room_code):
    game = games.get(room_code.upper())
    if not game:
        return jsonify({'error': 'Xona topilmadi'}), 404
    
    player_id = session.get('player_id')
    if not player_id or not game.get_player(player_id):
        return jsonify({'error': 'Ruxsat yo\'q'}), 403
    
    since_id = request.args.get('since_id', 0, type=int)
    new_messages = [msg for msg in game.chat_messages if msg['id'] > since_id]
    
    return jsonify({'messages': new_messages})

@app.route('/chat/<room_code>', methods=['POST'])
def send_chat(room_code):
    game = games.get(room_code.upper())
    if not game:
        return jsonify({'error': 'Xona topilmadi'}), 404
    
    player_id = session.get('player_id')
    player = game.get_player(player_id)
    if not player:
        return jsonify({'error': 'O\'yinchi topilmadi'}), 404
    
    if not player['alive']:
        return jsonify({'error': 'O\'lgan o\'yinchilar yozisha olmaydi'}), 403
    
    data = request.json
    message_text = data.get('message', '').strip()
    
    if not message_text or len(message_text) > 200:
        return jsonify({'error': 'Xabar bo\'sh yoki juda uzun'}), 400
    
    if is_role_claim(message_text):
        return jsonify({'error': 'O\'zingizning kimligingizni aytish mumkin emas!'}), 400
    
    game.chat_id_counter += 1
    new_message = {
        'id': game.chat_id_counter,
        'timestamp': time.time(),
        'player_id': player_id,
        'name': player['name'],
        'text': message_text
    }
    
    game.chat_messages.append(new_message)
    
    if len(game.chat_messages) > 200:
        game.chat_messages = game.chat_messages[-200:]
    
    return jsonify({'success': True, 'message': new_message})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
