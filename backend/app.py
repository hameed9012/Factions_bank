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
# CHANGED: Use test database
DB_NAME = os.getenv("BANK_DB_NAME", "factions_bank_test_second")
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

# -------------------- HELPERS --------------------
def ensure_player_account(c, ign):
    c.execute("SELECT id FROM players WHERE ign=%s", (ign,))
    row = c.fetchone()
    if not row:
        c.execute("INSERT INTO players(ign) VALUES (%s)", (ign,))
        player_id = c.lastrowid
    else:
        player_id = row["id"]

    c.execute("SELECT id FROM accounts WHERE player_id=%s AND status='active'", (player_id,))
    acc = c.fetchone()
    if not acc:
        c.execute("INSERT INTO accounts(player_id) VALUES (%s)", (player_id,))
        account_id = c.lastrowid
    else:
        account_id = acc["id"]
    return account_id

# -------------------- API ROUTES --------------------

# Fetch players list (with balances, interest rate, premium status)
@app.get("/api/players")
def api_players():
    q = request.args.get("q", "")
    limit = min(int(request.args.get("limit", 200)), 1000)
    offset = int(request.args.get("offset", 0))
    
    print(f"📥 GET /api/players - query: '{q}', limit: {limit}")
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                # Get settings for premium calculation
                c.execute("""
                    SELECT normal_interest_rate, premium_interest_rate, 
                           premium_balance_requirement 
                    FROM settings WHERE id=1
                """)
                settings = c.fetchone()
                
                if not settings:
                    print("⚠️  No settings found, using defaults")
                    settings = {
                        'normal_interest_rate': 0.05,
                        'premium_interest_rate': 0.06,
                        'premium_balance_requirement': 1000000000.00
                    }
                
                # Build player query
                sql = """
                    SELECT p.ign, a.balance, a.last_compounded_at,
                           p.created_at
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
                
                print(f"✅ Found {len(players)} players")
                
                # Add premium status and interest rate to each player
                for player in players:
                    balance = float(player['balance'] or 0)
                    premium_req = float(settings['premium_balance_requirement'] or 0)
                    is_premium = balance >= premium_req
                    
                    player['is_premium'] = 1 if is_premium else 0
                    player['interest_rate'] = float(
                        settings['premium_interest_rate'] if is_premium 
                        else settings['normal_interest_rate']
                    )
                    
                    # Convert decimal to float
                    player['balance'] = float(player['balance'] or 0)
                    
                    # Convert datetime to ISO string
                    if player.get('last_compounded_at'):
                        player['last_compounded_at'] = player['last_compounded_at'].isoformat()
                    if player.get('created_at'):
                        player['created_at'] = player['created_at'].isoformat()
        
        return jsonify(players)
    
    except Exception as e:
        print(f"❌ Error in /api/players: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Fetch transactions
@app.get("/api/transactions")
def api_transactions():
    ign = request.args.get("ign", "")
    limit = min(int(request.args.get("limit", 200)), 1000)
    offset = int(request.args.get("offset", 0))
    
    print(f"📥 GET /api/transactions - ign: '{ign}', limit: {limit}")
    
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
                        ORDER BY t.id DESC
                        LIMIT %s OFFSET %s
                    """, (f"%{ign}%", limit, offset))
                else:
                    c.execute("""
                        SELECT t.*, p.ign,
                               (t.balance_after - t.effective_delta) AS before_balance
                        FROM transactions t
                        JOIN accounts a ON a.id=t.account_id
                        JOIN players p ON p.id=a.player_id
                        ORDER BY t.id DESC
                        LIMIT %s OFFSET %s
                    """, (limit, offset))
                
                txns = c.fetchall()
                
                print(f"✅ Found {len(txns)} transactions")
                
                # Convert types
                for t in txns:
                    # Convert decimals to floats
                    if 'amount' in t:
                        t['amount'] = float(t['amount'] or 0)
                    if 'effective_delta' in t:
                        t['effective_delta'] = float(t['effective_delta'] or 0)
                    if 'balance_after' in t:
                        t['balance_after'] = float(t['balance_after'] or 0)
                    if 'before_balance' in t:
                        t['before_balance'] = float(t['before_balance'] or 0)
                    if 'fee_pct' in t and t['fee_pct'] is not None:
                        t['fee_pct'] = float(t['fee_pct'])
                    
                    # Convert datetime to ISO string
                    if t.get('created_at'):
                        t['created_at'] = t['created_at'].isoformat()
        
        return jsonify(txns)
    
    except Exception as e:
        print(f"❌ Error in /api/transactions: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Settings (interest & payout) - FIXED to match frontend expectations
@app.get("/api/settings")
def api_settings():
    print(f"📥 GET /api/settings")
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                # Get bank settings
                c.execute("""
                    SELECT payout_fee_pct, normal_interest_rate, 
                           premium_interest_rate, premium_balance_requirement
                    FROM settings WHERE id=1
                """)
                bank_settings = c.fetchone()
                
                if not bank_settings:
                    print("⚠️  No bank settings found, using defaults")
                    bank_settings = {
                        'payout_fee_pct': 0.07,
                        'normal_interest_rate': 0.05,
                        'premium_interest_rate': 0.06,
                        'premium_balance_requirement': 1000000000.00
                    }
                
                # Get horse race settings
                c.execute("""
                    SELECT winner_cut_pct, second_cut_pct, third_cut_pct,
                           entry_fee, imperial_cut_pct, rules
                    FROM horse_race_settings WHERE id=1
                """)
                race_settings = c.fetchone()
                
                if not race_settings:
                    print("⚠️  No race settings found, using defaults")
                    race_settings = {
                        'winner_cut_pct': 50.00,
                        'second_cut_pct': 30.00,
                        'third_cut_pct': 20.00,
                        'entry_fee': 100.00,
                        'imperial_cut_pct': 10.00,
                        'rules': 'No rules set'
                    }
                
                # Calculate total bank debt
                c.execute("""
                    SELECT COALESCE(SUM(balance), 0) AS total 
                    FROM accounts WHERE status='active'
                """)
                debt = c.fetchone()
                
                # Format response to match frontend expectations
                response = {
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
                }
                
                print(f"✅ Settings loaded - Total debt: ${response['total_bank_debt']:,.2f}")
        
        return jsonify(response)
    
    except Exception as e:
        print(f"❌ Error in /api/settings: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Interest rate history
@app.get("/api/interest/history")
def api_interest_history():
    limit = min(int(request.args.get("limit", 1000)), 5000)
    
    print(f"📥 GET /api/interest/history - limit: {limit}")
    
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("""
                    SELECT id, created_at AS changed_at, 
                           normal_interest_rate AS rate_normal_pct, 
                           premium_interest_rate AS rate_premium_pct,
                           premium_balance_requirement AS premium_min_balance
                    FROM interest_rate_history 
                    ORDER BY created_at ASC 
                    LIMIT %s
                """, (limit,))
                rows = c.fetchall()
                
                print(f"✅ Found {len(rows)} history entries")
                
                # Convert types
                for r in rows:
                    if 'rate_normal_pct' in r:
                        r['rate_normal_pct'] = float(r['rate_normal_pct'] or 0)
                    if 'rate_premium_pct' in r:
                        r['rate_premium_pct'] = float(r['rate_premium_pct'] or 0)
                    if 'premium_min_balance' in r:
                        r['premium_min_balance'] = float(r['premium_min_balance'] or 0)
                    
                    # Convert datetime to ISO string
                    if r.get('changed_at'):
                        r['changed_at'] = r['changed_at'].isoformat()
        
        return jsonify(rows)
    
    except Exception as e:
        print(f"❌ Error in /api/interest/history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Races - FIXED to match frontend expectations
@app.get("/api/races")
def get_races():
    print(f"📥 GET /api/races")
    
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
                    FROM horse_races r
                    ORDER BY r.id DESC
                """)
                races = c.fetchall()
                
                print(f"✅ Found {len(races)} races")
                
                # Get jockey names and winner names for each race
                for race in races:
                    race_id = race['id']
                    
                    # Convert prize_pool to float
                    race['prize_pool'] = float(race['prize_pool'] or 0)
                    
                    # Get jockeys
                    c.execute("""
                        SELECT p.ign 
                        FROM horse_jockeys hj
                        JOIN players p ON p.id = hj.player_id
                        WHERE hj.race_id = %s
                        ORDER BY hj.joined_at
                    """, (race_id,))
                    jockeys = [j['ign'] for j in c.fetchall()]
                    race['jockeys'] = jockeys
                    
                    # Get winner names
                    if race['winner1_id']:
                        c.execute("SELECT ign FROM players WHERE id=%s", (race['winner1_id'],))
                        w = c.fetchone()
                        race['winner1'] = w['ign'] if w else None
                    else:
                        race['winner1'] = None
                    
                    if race['winner2_id']:
                        c.execute("SELECT ign FROM players WHERE id=%s", (race['winner2_id'],))
                        w = c.fetchone()
                        race['winner2'] = w['ign'] if w else None
                    else:
                        race['winner2'] = None
                    
                    if race['winner3_id']:
                        c.execute("SELECT ign FROM players WHERE id=%s", (race['winner3_id'],))
                        w = c.fetchone()
                        race['winner3'] = w['ign'] if w else None
                    else:
                        race['winner3'] = None
                    
                    # Convert datetimes to ISO strings
                    if race.get('scheduled_at'):
                        race['scheduled_at'] = race['scheduled_at'].isoformat()
                    if race.get('ends_at'):
                        race['ends_at'] = race['ends_at'].isoformat()
                    if race.get('created_at'):
                        race['created_at'] = race['created_at'].isoformat()
                    
                    # Remove ID fields
                    race.pop('winner1_id', None)
                    race.pop('winner2_id', None)
                    race.pop('winner3_id', None)
        
        return jsonify(races)
    
    except Exception as e:
        print(f"❌ Error in /api/races: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# Health check
@app.get("/healthz")
def health():
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("SELECT 1")
        return jsonify({"ok": True, "database": DB_NAME})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

# Test endpoint to check what data is being returned
@app.get("/api/debug")
def debug():
    try:
        with db() as cx:
            with cx.cursor() as c:
                c.execute("SELECT COUNT(*) as count FROM players")
                players_count = c.fetchone()
                
                c.execute("SELECT COUNT(*) as count FROM accounts WHERE status='active'")
                accounts_count = c.fetchone()
                
                c.execute("SELECT COUNT(*) as count FROM transactions")
                txn_count = c.fetchone()
                
                c.execute("SELECT * FROM settings WHERE id=1")
                settings = c.fetchone()
        
        return jsonify({
            "database": DB_NAME,
            "players": players_count['count'],
            "active_accounts": accounts_count['count'],
            "transactions": txn_count['count'],
            "settings": settings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# -------------------- MAIN --------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8085"))
    print(f"🌐 Starting server on http://0.0.0.0:{port}")
    print(f"🔍 Test endpoints at:")
    print(f"   - http://localhost:{port}/healthz")
    print(f"   - http://localhost:{port}/api/debug")
    print(f"   - http://localhost:{port}/api/players")
    print(f"   - http://localhost:{port}/api/settings")
    app.run(host="127.0.0.1", port=port, debug=True)