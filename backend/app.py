#!/usr/bin/env python3
import os
from datetime import datetime
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import pymysql

# -------------------- CONFIG --------------------
DB_HOST = os.getenv("BANK_DB_HOST", "127.0.0.1")
DB_USER = os.getenv("BANK_DB_USER", "factions_test")
DB_PASS = os.getenv("BANK_DB_PASS", "SuperSecureTestPass123")
DB_NAME = os.getenv("BANK_DB_NAME", "factions_bank")
API_KEY = os.getenv("BANK_API_KEY", "d6892971-aada-4ab6-ac14-76cd4c77054b")

def db():
    return pymysql.connect(
        host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
        autocommit=False, cursorclass=pymysql.cursors.DictCursor
    )

app = Flask(__name__)
CORS(app)

print(f"🚀 Starting Factions Bank API")
print(f"📊 Database: {DB_NAME}")
print(f"🔌 Host: {DB_HOST}")

# -------------------- AUTH --------------------
def require_api_key():
    k = request.headers.get("X-API-Key") or request.args.get("key")
    if not k or k != API_KEY:
        abort(401, "invalid or missing API key")

# -------------------- BANK ROUTES --------------------

@app.get("/api/players")
def api_players():
    q = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 200)), 1000)
    offset = int(request.args.get("offset", 0))
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT interest_rate_per_period as normal_interest_rate, 
                           premium_interest_rate_per_period as premium_interest_rate, 
                           premium_min_balance as premium_balance_requirement 
                    FROM settings WHERE id=1
                """)
                settings = c.fetchone() or {
                    'normal_interest_rate': 0.05,
                    'premium_interest_rate': 0.06,
                    'premium_balance_requirement': 1000000000.00
                }
                
                sql = """
                    SELECT p.ign, a.balance, a.last_compounded_at, p.created_at
                    FROM players p
                    JOIN accounts a ON a.player_id = p.id AND a.status='active'
                """
                params = []
                
                if q:
                    sql += " WHERE p.ign LIKE %s"
                    params.append(f"%{q}%")
                
                sql += " ORDER BY a.balance DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])
                
                c.execute(sql, params)
                players = c.fetchall()
                
                for player in players:
                    balance = float(player['balance'] or 0)
                    premium_req = float(settings['premium_balance_requirement'] or 0)
                    is_premium = balance >= premium_req
                    
                    player['is_premium'] = 1 if is_premium else 0
                    player['interest_rate'] = float(
                        settings['premium_interest_rate'] if is_premium 
                        else settings['normal_interest_rate']
                    )
                    player['balance'] = balance
                    
                    if player.get('last_compounded_at'):
                        player['last_compounded_at'] = player['last_compounded_at'].isoformat()
                    if player.get('created_at'):
                        player['created_at'] = player['created_at'].isoformat()
        
        return jsonify(players)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.get("/api/transactions")
def api_transactions():
    ign = request.args.get("ign", "")
    limit = min(int(request.args.get("limit", 200)), 1000)
    offset = int(request.args.get("offset", 0))
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                if ign:
                    c.execute("""
                        SELECT t.*, p.ign,
                               (t.balance_after - t.effective_delta) AS before_balance
                        FROM transactions t
                        JOIN accounts a ON a.id=t.account_id
                        JOIN players p ON p.id=a.player_id
                        WHERE p.ign LIKE %s
                        ORDER BY t.id DESC LIMIT %s OFFSET %s
                    """, (f"%{ign}%", limit, offset))
                else:
                    c.execute("""
                        SELECT t.*, p.ign,
                               (t.balance_after - t.effective_delta) AS before_balance
                        FROM transactions t
                        JOIN accounts a ON a.id=t.account_id
                        JOIN players p ON p.id=a.player_id
                        ORDER BY t.id DESC LIMIT %s OFFSET %s
                    """, (limit, offset))
                
                txns = c.fetchall()
                
                for t in txns:
                    for field in ['amount', 'effective_delta', 'balance_after', 'before_balance']:
                        if field in t:
                            t[field] = float(t[field] or 0)
                    if 'fee_pct' in t and t['fee_pct'] is not None:
                        t['fee_pct'] = float(t['fee_pct'])
                    if t.get('created_at'):
                        t['created_at'] = t['created_at'].isoformat()
        
        return jsonify(txns)
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.get("/api/settings")
def api_settings():
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT payout_fee_pct, 
                           interest_rate_per_period as normal_interest_rate, 
                           premium_interest_rate_per_period as premium_interest_rate, 
                           premium_min_balance as premium_balance_requirement
                    FROM settings WHERE id=1
                """)
                bank_settings = c.fetchone() or {
                    'payout_fee_pct': 0.07,
                    'normal_interest_rate': 0.05,
                    'premium_interest_rate': 0.06,
                    'premium_balance_requirement': 1000000000.00
                }
                
                c.execute("""
                    SELECT winner_cut_pct, second_cut_pct, third_cut_pct,
                           entry_fee, imperial_cut_pct, rules
                    FROM horse_race_settings WHERE id=1
                """)
                race_settings = c.fetchone() or {
                    'winner_cut_pct': 50.00,
                    'second_cut_pct': 30.00,
                    'third_cut_pct': 20.00,
                    'entry_fee': 100.00,
                    'imperial_cut_pct': 10.00,
                    'rules': 'No rules set'
                }
                
                c.execute("""
                    SELECT COALESCE(SUM(balance), 0) AS total 
                    FROM accounts WHERE status='active'
                """)
                debt = c.fetchone()
                
                return jsonify({
                    "bank": {
                        "payout_fee_pct": float(bank_settings['payout_fee_pct'] or 0),
                        "interest_rate_normal": float(bank_settings['normal_interest_rate'] or 0),
                        "interest_rate_premium": float(bank_settings['premium_interest_rate'] or 0),
                        "premium_min_balance": float(bank_settings['premium_balance_requirement'] or 0)
                    },
                    "horse_race": {
                        "winner1_pct": float(race_settings['winner_cut_pct'] or 0),
                        "winner2_pct": float(race_settings['second_cut_pct'] or 0),
                        "winner3_pct": float(race_settings['third_cut_pct'] or 0),
                        "entry_fee": float(race_settings['entry_fee'] or 0),
                        "imperial_cut": float(race_settings['imperial_cut_pct'] or 0),
                        "rules": race_settings['rules'] or ""
                    },
                    "total_bank_debt": float(debt['total'] or 0)
                })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.get("/api/interest/history")
def api_interest_history():
    limit = min(int(request.args.get("limit", 1000)), 5000)
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT id, changed_at, 
                           normal_rate AS rate_normal_pct, 
                           premium_rate AS rate_premium_pct,
                           premium_min_balance
                    FROM interest_rate_history 
                    ORDER BY changed_at ASC LIMIT %s
                """, (limit,))
                rows = c.fetchall()
                
                for r in rows:
                    for field in ['rate_normal_pct', 'rate_premium_pct', 'premium_min_balance']:
                        if field in r:
                            r[field] = float(r[field] or 0)
                    if r.get('changed_at'):
                        r['changed_at'] = r['changed_at'].isoformat()
        
        return jsonify(rows)
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.get("/api/races")
def get_races():
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT r.id, COALESCE(r.name, r.race_name, 'Unnamed Race') AS name,
                           r.prize_pool, r.starts_at AS scheduled_at, r.ends_at,
                           r.winner1_id, r.winner2_id, r.winner3_id, r.created_at,
                           CASE 
                               WHEN r.ends_at IS NOT NULL AND r.ends_at <= NOW() THEN 'finished'
                               WHEN r.starts_at IS NOT NULL AND r.starts_at <= NOW() AND (r.ends_at IS NULL OR r.ends_at > NOW()) THEN 'live'
                               ELSE 'scheduled'
                           END AS status,
                           (SELECT COUNT(*) FROM horse_jockeys hj WHERE hj.race_id = r.id) AS jockey_count
                    FROM horse_races r ORDER BY r.id DESC
                """)
                races = c.fetchall()
                
                for race in races:
                    race_id = race['id']
                    race['prize_pool'] = float(race['prize_pool'] or 0)
                    
                    c.execute("""
                        SELECT p.ign FROM horse_jockeys hj
                        JOIN players p ON p.id = hj.player_id
                        WHERE hj.race_id = %s ORDER BY hj.joined_at
                    """, (race_id,))
                    race['jockeys'] = [j['ign'] for j in c.fetchall()]
                    
                    for i in range(1, 4):
                        if race[f'winner{i}_id']:
                            c.execute("SELECT ign FROM players WHERE id=%s", (race[f'winner{i}_id'],))
                            w = c.fetchone()
                            race[f'winner{i}'] = w['ign'] if w else None
                        else:
                            race[f'winner{i}'] = None
                        race.pop(f'winner{i}_id', None)
                    
                    for field in ['scheduled_at', 'ends_at', 'created_at']:
                        if race.get(field):
                            race[field] = race[field].isoformat()
        
        return jsonify(races)
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------- HORSE RACE ROUTES --------------------

@app.post("/api/races/new")
def create_race():
    require_api_key()
    data = request.json
    
    race_name = data.get("name", f"Imperial Race {datetime.now().strftime('%Y-%m-%d')}")
    starts_at = data.get("starts_at")
    
    if not starts_at:
        return jsonify({"error": "starts_at is required"}), 400
    
    try:
        starts_at_dt = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
    except:
        return jsonify({"error": "Invalid starts_at format"}), 400
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    INSERT INTO horse_races (name, race_name, prize_pool, starts_at)
                    VALUES (%s, %s, 0.00, %s)
                """, (race_name, race_name, starts_at_dt))
                race_id = c.lastrowid
                cx.commit()
                
                return jsonify({
                    "success": True,
                    "race_id": race_id,
                    "name": race_name,
                    "starts_at": starts_at_dt.isoformat()
                })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.post("/api/races/enroll")
def enroll_jockey():
    require_api_key()
    data = request.json
    
    player_name = data.get("player_name")
    if not player_name:
        return jsonify({"error": "player_name is required"}), 400
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                # Get latest active race
                c.execute("""
                    SELECT id, prize_pool, name
                    FROM horse_races 
                    WHERE ends_at IS NULL
                    ORDER BY id DESC LIMIT 1
                """)
                race = c.fetchone()
                if not race:
                    return jsonify({"error": "No active race found"}), 404
                
                race_id = race['id']
                
                # Get player
                c.execute("SELECT id FROM players WHERE ign=%s", (player_name,))
                player = c.fetchone()
                if not player:
                    return jsonify({"error": f"Player {player_name} not found"}), 404
                
                player_id = player['id']
                
                # Check if already enrolled
                c.execute("""
                    SELECT id FROM horse_jockeys 
                    WHERE race_id=%s AND player_id=%s
                """, (race_id, player_id))
                if c.fetchone():
                    return jsonify({"error": f"{player_name} already enrolled"}), 400
                
                # Get account
                c.execute("""
                    SELECT id, balance FROM accounts 
                    WHERE player_id=%s AND status='active'
                """, (player_id,))
                account = c.fetchone()
                if not account:
                    return jsonify({"error": f"No active account for {player_name}"}), 404
                
                # Get settings
                c.execute("""
                    SELECT entry_fee, imperial_cut_pct 
                    FROM horse_race_settings WHERE id=1
                """)
                settings = c.fetchone()
                
                entry_fee = float(settings['entry_fee'] or 100)
                imperial_cut_pct = float(settings['imperial_cut_pct'] or 10) / 100
                
                # Check balance
                if float(account['balance']) < entry_fee:
                    return jsonify({
                        "error": f"Insufficient balance. Required: ${entry_fee:,.2f}"
                    }), 400
                
                # Calculate amounts
                imperial_cut = entry_fee * imperial_cut_pct
                prize_contribution = entry_fee - imperial_cut
                
                # Create transaction
                c.execute("""
                    INSERT INTO transactions (account_id, txn_type, amount, note)
                    VALUES (%s, 'payout', %s, %s)
                """, (account['id'], entry_fee, f"Horse race entry - {race['name']}"))
                
                # Add jockey
                c.execute("""
                    INSERT INTO horse_jockeys (race_id, player_id)
                    VALUES (%s, %s)
                """, (race_id, player_id))
                
                # Update prize pool
                new_prize_pool = float(race['prize_pool']) + prize_contribution
                c.execute("""
                    UPDATE horse_races SET prize_pool = %s WHERE id = %s
                """, (new_prize_pool, race_id))
                
                cx.commit()
                
                return jsonify({
                    "success": True,
                    "player": player_name,
                    "race_id": race_id,
                    "entry_fee": entry_fee,
                    "prize_pool": new_prize_pool,
                    "imperial_cut": imperial_cut
                })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

def _set_winner(player_name, position):
    """Helper to set winner and award prize"""
    try:
        with db() as cx:
            with cx.cursor() as c:
                # Get latest race
                c.execute("""
                    SELECT r.id, r.prize_pool, r.name,
                           r.winner1_id, r.winner2_id, r.winner3_id
                    FROM horse_races r
                    WHERE r.ends_at IS NULL
                    ORDER BY r.id DESC LIMIT 1
                """)
                race = c.fetchone()
                if not race:
                    return jsonify({"error": "No active race found"}), 404
                
                # Get player
                c.execute("SELECT id FROM players WHERE ign=%s", (player_name,))
                player = c.fetchone()
                if not player:
                    return jsonify({"error": f"Player {player_name} not found"}), 404
                
                player_id = player['id']
                
                # Check if enrolled
                c.execute("""
                    SELECT id FROM horse_jockeys 
                    WHERE race_id=%s AND player_id=%s
                """, (race['id'], player_id))
                if not c.fetchone():
                    return jsonify({"error": f"{player_name} not enrolled in race"}), 400
                
                # Check if already a winner
                for i in range(1, 4):
                    if i != position and race[f'winner{i}_id'] == player_id:
                        return jsonify({"error": f"{player_name} already winner {i}"}), 400
                
                # Get prize distribution
                c.execute("""
                    SELECT winner_cut_pct, second_cut_pct, third_cut_pct
                    FROM horse_race_settings WHERE id=1
                """)
                settings = c.fetchone()
                
                prize_pool = float(race['prize_pool'] or 0)
                pct_map = {
                    1: float(settings['winner_cut_pct']),
                    2: float(settings['second_cut_pct']),
                    3: float(settings['third_cut_pct'])
                }
                prize_amount = prize_pool * (pct_map[position] / 100)
                
                # Get account
                c.execute("""
                    SELECT id FROM accounts 
                    WHERE player_id=%s AND status='active'
                """, (player_id,))
                account = c.fetchone()
                if not account:
                    return jsonify({"error": f"No active account for {player_name}"}), 404
                
                # Set winner
                c.execute(f"""
                    UPDATE horse_races 
                    SET winner{position}_id = %s 
                    WHERE id = %s
                """, (player_id, race['id']))
                
                # Award prize
                c.execute("""
                    INSERT INTO transactions (account_id, txn_type, amount, note)
                    VALUES (%s, 'deposit', %s, %s)
                """, (account['id'], prize_amount, f"Horse race - Position {position} - {race['name']}"))
                
                cx.commit()
                
                return jsonify({
                    "success": True,
                    "player": player_name,
                    "position": position,
                    "prize": prize_amount,
                    "race_id": race['id']
                })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.post("/api/races/winner1")
def set_winner1():
    require_api_key()
    data = request.json
    player_name = data.get("player_name")
    if not player_name:
        return jsonify({"error": "player_name is required"}), 400
    return _set_winner(player_name, 1)

@app.post("/api/races/winner2")
def set_winner2():
    require_api_key()
    data = request.json
    player_name = data.get("player_name")
    if not player_name:
        return jsonify({"error": "player_name is required"}), 400
    return _set_winner(player_name, 2)

@app.post("/api/races/winner3")
def set_winner3():
    require_api_key()
    data = request.json
    player_name = data.get("player_name")
    if not player_name:
        return jsonify({"error": "player_name is required"}), 400
    return _set_winner(player_name, 3)

@app.get("/api/races/info")
def race_info():
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT r.id, COALESCE(r.name, r.race_name, 'Unnamed Race') AS name,
                           r.prize_pool, r.starts_at, r.ends_at,
                           r.winner1_id, r.winner2_id, r.winner3_id,
                           (SELECT COUNT(*) FROM horse_jockeys hj WHERE hj.race_id = r.id) AS jockey_count
                    FROM horse_races r ORDER BY r.id DESC LIMIT 1
                """)
                race = c.fetchone()
                if not race:
                    return jsonify({"error": "No races found"}), 404
                
                race_id = race['id']
                
                # Get jockeys
                c.execute("""
                    SELECT p.ign FROM horse_jockeys hj
                    JOIN players p ON p.id = hj.player_id
                    WHERE hj.race_id = %s ORDER BY hj.joined_at
                """, (race_id,))
                jockeys = [j['ign'] for j in c.fetchall()]
                
                # Get winners
                winners = {}
                for i in range(1, 4):
                    if race[f'winner{i}_id']:
                        c.execute("SELECT ign FROM players WHERE id=%s", (race[f'winner{i}_id'],))
                        w = c.fetchone()
                        winners[f'winner{i}'] = w['ign'] if w else None
                    else:
                        winners[f'winner{i}'] = None
                
                # Get prize distribution
                c.execute("""
                    SELECT winner_cut_pct, second_cut_pct, third_cut_pct
                    FROM horse_race_settings WHERE id=1
                """)
                settings = c.fetchone()
                
                prize_pool = float(race['prize_pool'] or 0)
                
                return jsonify({
                    "race_id": race_id,
                    "name": race['name'],
                    "prize_pool": prize_pool,
                    "starts_at": race['starts_at'].isoformat() if race['starts_at'] else None,
                    "ends_at": race['ends_at'].isoformat() if race['ends_at'] else None,
                    "jockey_count": race['jockey_count'],
                    "jockeys": jockeys,
                    **winners,
                    "prize_distribution": {
                        "winner1": prize_pool * (float(settings['winner_cut_pct']) / 100),
                        "winner2": prize_pool * (float(settings['second_cut_pct']) / 100),
                        "winner3": prize_pool * (float(settings['third_cut_pct']) / 100)
                    }
                })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.post("/api/races/end")
def end_race():
    require_api_key()
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT id, winner1_id FROM horse_races 
                    WHERE ends_at IS NULL
                    ORDER BY id DESC LIMIT 1
                """)
                race = c.fetchone()
                if not race:
                    return jsonify({"error": "No active race found"}), 404
                
                if not race['winner1_id']:
                    return jsonify({"error": "Must set winner1 before ending race"}), 400
                
                c.execute("""
                    UPDATE horse_races SET ends_at = NOW() WHERE id = %s
                """, (race['id'],))
                cx.commit()
                
                return jsonify({
                    "success": True,
                    "race_id": race['id'],
                    "ended_at": datetime.now().isoformat()
                })
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({"error": str(e)}), 500

@app.get("/healthz")
def health():
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("SELECT 1")
        return jsonify({"ok": True, "database": DB_NAME})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# -------------------- MAIN --------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8085"))
    print(f"🌐 Server: http://0.0.0.0:{port}")
    print(f"🔗 Endpoints:")
    print(f"   - http://localhost:{port}/healthz")
    print(f"   - http://localhost:{port}/api/players")
    print(f"   - http://localhost:{port}/api/races")
    print(f"   - http://localhost:{port}/api/races/info")
    app.run(host="127.0.0.1", port=port, debug=True)