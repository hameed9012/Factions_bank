#!/usr/bin/env python3
"""
Imperial Horse Races Backend API
Add these routes to app.py or import them
"""
from datetime import datetime
from flask import request, jsonify, abort
import pymysql

def add_race_routes(app, db_func, require_api_key_func):
    """
    Add horse race routes to Flask app
    Usage in app.py:
        from horse_races import add_race_routes
        add_race_routes(app, db, require_api_key)
    """
    
    # Create new race
    @app.post("/api/races/new")
    def create_race():
        require_api_key_func()
        data = request.json
        
        race_name = data.get("name", f"Imperial Race {datetime.now().strftime('%Y-%m-%d')}")
        starts_at = data.get("starts_at")  # ISO datetime string
        
        if not starts_at:
            return jsonify({"error": "starts_at is required"}), 400
        
        try:
            starts_at_dt = datetime.fromisoformat(starts_at.replace('Z', '+00:00'))
        except:
            return jsonify({"error": "Invalid starts_at format. Use ISO 8601"}), 400
        
        print(f"🏇 Creating new race: {race_name} at {starts_at}")
        
        try:
            with db_func() as cx:
                with cx.cursor() as c:
                    c.execute("""
                        INSERT INTO horse_races (name, race_name, prize_pool, starts_at)
                        VALUES (%s, %s, 0.00, %s)
                    """, (race_name, race_name, starts_at_dt))
                    
                    race_id = c.lastrowid
                    cx.commit()
                    
                    print(f"✅ Race created with ID: {race_id}")
                    
                    return jsonify({
                        "success": True,
                        "race_id": race_id,
                        "name": race_name,
                        "starts_at": starts_at_dt.isoformat()
                    })
        
        except Exception as e:
            print(f"❌ Error creating race: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    # Enroll jockey in latest race
    @app.post("/api/races/enroll")
    def enroll_jockey():
        require_api_key_func()
        data = request.json
        
        player_name = data.get("player_name")
        if not player_name:
            return jsonify({"error": "player_name is required"}), 400
        
        print(f"🏇 Enrolling {player_name} in latest race")
        
        try:
            with db_func() as cx:
                with cx.cursor() as c:
                    # Get latest race that hasn't ended
                    c.execute("""
                        SELECT id, prize_pool, name
                        FROM horse_races 
                        WHERE ends_at IS NULL
                        ORDER BY id DESC 
                        LIMIT 1
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
                        return jsonify({"error": f"{player_name} is already enrolled in this race"}), 400
                    
                    # Get account
                    c.execute("""
                        SELECT id, balance 
                        FROM accounts 
                        WHERE player_id=%s AND status='active'
                    """, (player_id,))
                    account = c.fetchone()
                    
                    if not account:
                        return jsonify({"error": f"No active account for {player_name}"}), 404
                    
                    # Get entry fee and imperial cut
                    c.execute("""
                        SELECT entry_fee, imperial_cut_pct 
                        FROM horse_race_settings 
                        WHERE id=1
                    """)
                    settings = c.fetchone()
                    
                    entry_fee = float(settings['entry_fee'] or 100)
                    imperial_cut_pct = float(settings['imperial_cut_pct'] or 10) / 100
                    
                    # Check balance
                    if float(account['balance']) < entry_fee:
                        return jsonify({
                            "error": f"Insufficient balance. Required: ${entry_fee:,.2f}, Available: ${float(account['balance']):,.2f}"
                        }), 400
                    
                    # Calculate amounts
                    imperial_cut = entry_fee * imperial_cut_pct
                    prize_contribution = entry_fee - imperial_cut
                    
                    # Create transaction for entry fee
                    c.execute("""
                        INSERT INTO transactions (account_id, txn_type, amount, note)
                        VALUES (%s, 'payout', %s, %s)
                    """, (account['id'], entry_fee, f"Horse race entry fee - {race['name']}"))
                    
                    # Add jockey to race
                    c.execute("""
                        INSERT INTO horse_jockeys (race_id, player_id)
                        VALUES (%s, %s)
                    """, (race_id, player_id))
                    
                    # Update prize pool
                    new_prize_pool = float(race['prize_pool']) + prize_contribution
                    c.execute("""
                        UPDATE horse_races 
                        SET prize_pool = %s 
                        WHERE id = %s
                    """, (new_prize_pool, race_id))
                    
                    cx.commit()
                    
                    print(f"✅ {player_name} enrolled! Prize pool: ${new_prize_pool:,.2f}")
                    
                    return jsonify({
                        "success": True,
                        "player": player_name,
                        "race_id": race_id,
                        "entry_fee": entry_fee,
                        "prize_pool": new_prize_pool,
                        "imperial_cut": imperial_cut
                    })
        
        except Exception as e:
            print(f"❌ Error enrolling jockey: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    # Set winner 1
    @app.post("/api/races/winner1")
    def set_winner1():
        require_api_key_func()
        data = request.json
        
        player_name = data.get("player_name")
        if not player_name:
            return jsonify({"error": "player_name is required"}), 400
        
        return _set_winner(player_name, 1, db_func)
    
    # Set winner 2
    @app.post("/api/races/winner2")
    def set_winner2():
        require_api_key_func()
        data = request.json
        
        player_name = data.get("player_name")
        if not player_name:
            return jsonify({"error": "player_name is required"}), 400
        
        return _set_winner(player_name, 2, db_func)
    
    # Set winner 3
    @app.post("/api/races/winner3")
    def set_winner3():
        require_api_key_func()
        data = request.json
        
        player_name = data.get("player_name")
        if not player_name:
            return jsonify({"error": "player_name is required"}), 400
        
        return _set_winner(player_name, 3, db_func)
    
    # Get latest race info
    @app.get("/api/races/info")
    def race_info():
        print(f"📥 GET /api/races/info")
        
        try:
            with db_func() as cx:
                with cx.cursor() as c:
                    c.execute("""
                        SELECT r.id, COALESCE(r.name, r.race_name, 'Unnamed Race') AS name,
                               r.prize_pool, r.starts_at, r.ends_at,
                               r.winner1_id, r.winner2_id, r.winner3_id,
                               (SELECT COUNT(*) FROM horse_jockeys hj WHERE hj.race_id = r.id) AS jockey_count
                        FROM horse_races r
                        ORDER BY r.id DESC
                        LIMIT 1
                    """)
                    race = c.fetchone()
                    
                    if not race:
                        return jsonify({"error": "No races found"}), 404
                    
                    race_id = race['id']
                    
                    # Get jockeys
                    c.execute("""
                        SELECT p.ign 
                        FROM horse_jockeys hj
                        JOIN players p ON p.id = hj.player_id
                        WHERE hj.race_id = %s
                        ORDER BY hj.joined_at
                    """, (race_id,))
                    jockeys = [j['ign'] for j in c.fetchall()]
                    
                    # Get winners
                    winners = {}
                    for i, winner_id_col in enumerate(['winner1_id', 'winner2_id', 'winner3_id'], 1):
                        if race[winner_id_col]:
                            c.execute("SELECT ign FROM players WHERE id=%s", (race[winner_id_col],))
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
                        "winner1": winners['winner1'],
                        "winner2": winners['winner2'],
                        "winner3": winners['winner3'],
                        "prize_distribution": {
                            "winner1": prize_pool * (float(settings['winner_cut_pct']) / 100),
                            "winner2": prize_pool * (float(settings['second_cut_pct']) / 100),
                            "winner3": prize_pool * (float(settings['third_cut_pct']) / 100)
                        }
                    })
        
        except Exception as e:
            print(f"❌ Error getting race info: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500
    
    # End race
    @app.post("/api/races/end")
    def end_race():
        require_api_key_func()
        
        print(f"🏁 Ending latest race")
        
        try:
            with db_func() as cx:
                with cx.cursor() as c:
                    # Get latest race
                    c.execute("""
                        SELECT id, winner1_id, winner2_id, winner3_id
                        FROM horse_races 
                        WHERE ends_at IS NULL
                        ORDER BY id DESC 
                        LIMIT 1
                    """)
                    race = c.fetchone()
                    
                    if not race:
                        return jsonify({"error": "No active race found"}), 404
                    
                    if not race['winner1_id']:
                        return jsonify({"error": "Cannot end race without setting winner1"}), 400
                    
                    # End race
                    c.execute("""
                        UPDATE horse_races 
                        SET ends_at = NOW() 
                        WHERE id = %s
                    """, (race['id'],))
                    
                    cx.commit()
                    
                    print(f"✅ Race {race['id']} ended")
                    
                    return jsonify({
                        "success": True,
                        "race_id": race['id'],
                        "ended_at": datetime.now().isoformat()
                    })
        
        except Exception as e:
            print(f"❌ Error ending race: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": str(e)}), 500


def _set_winner(player_name, position, db_func):
    """Helper function to set a winner"""
    print(f"🏆 Setting winner {position}: {player_name}")
    
    try:
        with db_func() as cx:
            with cx.cursor() as c:
                # Get latest race
                c.execute("""
                    SELECT r.id, r.prize_pool, r.name,
                           r.winner1_id, r.winner2_id, r.winner3_id
                    FROM horse_races r
                    WHERE r.ends_at IS NULL
                    ORDER BY r.id DESC 
                    LIMIT 1
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
                
                # Check if player is a jockey in this race
                c.execute("""
                    SELECT id FROM horse_jockeys 
                    WHERE race_id=%s AND player_id=%s
                """, (race_id, player_id))
                
                if not c.fetchone():
                    return jsonify({"error": f"{player_name} is not enrolled in this race"}), 400
                
                # Check if already set as another position
                for i in range(1, 4):
                    if i != position and race[f'winner{i}_id'] == player_id:
                        return jsonify({"error": f"{player_name} is already set as winner {i}"}), 400
                
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
                
                # Get player account
                c.execute("""
                    SELECT id FROM accounts 
                    WHERE player_id=%s AND status='active'
                """, (player_id,))
                account = c.fetchone()
                
                if not account:
                    return jsonify({"error": f"No active account for {player_name}"}), 404
                
                # Update winner
                c.execute(f"""
                    UPDATE horse_races 
                    SET winner{position}_id = %s 
                    WHERE id = %s
                """, (player_id, race_id))
                
                # Add prize to account
                c.execute("""
                    INSERT INTO transactions (account_id, txn_type, amount, note)
                    VALUES (%s, 'deposit', %s, %s)
                """, (account['id'], prize_amount, f"Horse race prize - Position {position} - {race['name']}"))
                
                cx.commit()
                
                print(f"✅ {player_name} set as winner {position} and awarded ${prize_amount:,.2f}")
                
                return jsonify({
                    "success": True,
                    "player": player_name,
                    "position": position,
                    "prize": prize_amount,
                    "race_id": race_id
                })
    
    except Exception as e:
        print(f"❌ Error setting winner: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500