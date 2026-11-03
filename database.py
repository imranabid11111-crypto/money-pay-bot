import sqlite3, os
DB = os.getenv("DATABASE_PATH", "money_pay.sqlite3")

def conn():
    c = sqlite3.connect(DB, timeout=20)
    c.execute("PRAGMA foreign_keys=ON")
    return c

def init_db():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          user_id INTEGER PRIMARY KEY, balance REAL NOT NULL DEFAULT 0,
          referred_by INTEGER, referral_paid INTEGER NOT NULL DEFAULT 0,
          joined_at TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS withdrawals(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
          amount REAL NOT NULL, method TEXT NOT NULL, account TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending', created_at TEXT DEFAULT CURRENT_TIMESTAMP);
        """)

def save_pending_ref(uid, referrer):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id, referred_by) VALUES(?, ?)", (uid, referrer))
        if referrer:
            c.execute("UPDATE users SET referred_by=? WHERE user_id=? AND referral_paid=0 AND referred_by IS NULL", (referrer, uid))

def complete_referral(uid, reward):
    with conn() as c:
        row = c.execute("SELECT referred_by, referral_paid FROM users WHERE user_id=?", (uid,)).fetchone()
        if not row or row[1] or not row[0]:
            return
        referrer = row[0]
        c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (referrer,))
        c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (reward, referrer))
        c.execute("UPDATE users SET referral_paid=1 WHERE user_id=?", (uid,))

def get_user(uid, reward, minimum):
    with conn() as c:
        c.execute("INSERT OR IGNORE INTO users(user_id) VALUES(?)", (uid,))
        balance = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()[0]
        referrals = c.execute("SELECT COUNT(*) FROM users WHERE referred_by=? AND referral_paid=1", (uid,)).fetchone()[0]
        return {"balance": balance, "referrals": referrals, "per_referral": reward, "minimum_withdraw": minimum}

def create_withdrawal(uid, minimum, method, account):
    with conn() as c:
        balance = c.execute("SELECT balance FROM users WHERE user_id=?", (uid,)).fetchone()
        if not balance or balance[0] < minimum:
            return False, f"Minimum withdrawal ৳{minimum}; insufficient balance."
        pending = c.execute("SELECT COUNT(*) FROM withdrawals WHERE user_id=? AND status='pending'", (uid,)).fetchone()[0]
        if pending:
            return False, "You already have a pending withdrawal request."
        c.execute("UPDATE users SET balance=balance-? WHERE user_id=?", (minimum, uid))
        c.execute("INSERT INTO withdrawals(user_id,amount,method,account) VALUES(?,?,?,?)", (uid, minimum, method, account))
        return True, "Withdrawal request submitted."

def list_withdrawals(status):
    with conn() as c:
        return c.execute("SELECT id,user_id,amount,method,account FROM withdrawals WHERE status=? ORDER BY id", (status,)).fetchall()

def update_withdrawal(wid, status):
    with conn() as c:
        row = c.execute("SELECT user_id,amount,status FROM withdrawals WHERE id=?", (wid,)).fetchone()
        if not row or row[2] != "pending":
            return None
        c.execute("UPDATE withdrawals SET status=? WHERE id=?", (status, wid))
        if status == "rejected":
            c.execute("UPDATE users SET balance=balance+? WHERE user_id=?", (row[1], row[0]))
        return row[0], row[1]

def get_stats():
    with conn() as c:
        return {
          "users": c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
          "referrals": c.execute("SELECT COUNT(*) FROM users WHERE referral_paid=1").fetchone()[0],
          "pending": c.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'").fetchone()[0]
        }
