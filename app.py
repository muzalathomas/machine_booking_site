import os, sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime

app = Flask(__name__)
app.secret_key = "travis123_secret"

DB_PATH = os.path.join(os.path.dirname(__file__), "booking.db")

VEHICLES_DATA = [
    ("Toyota Hilux", 100),
    ("Tipper Truck", 100),
    ("Land Cruiser", 100),
    ("Komatsu Loader", 100)
]

OWNER_PHONE = "260963329816"
ADMIN_PASSWORD = "travis123"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS vehicles (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, vehicle_id INTEGER, vehicle_name TEXT, customer TEXT, cust_phone TEXT, start_date TEXT, end_date TEXT, days INTEGER, total INTEGER)")
    c.execute("SELECT count(*) FROM vehicles")
    count = c.fetchone()[0]
    if count == 0:
        c.executemany("INSERT INTO vehicles (name, price) VALUES (?,?)", VEHICLES_DATA)
    else:
        c.execute("DELETE FROM vehicles")
        c.executemany("INSERT INTO vehicles (name, price) VALUES (?,?)", VEHICLES_DATA)
    conn.commit()
    conn.close()

init_db()

@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM vehicles")
    vehicles = c.fetchall()
    message = None
    whatsapp_link = None
    if request.method == "POST":
        v_id = int(request.form["vehicle_id"])
        customer = request.form["customer"]
        cust_phone = request.form["cust_phone"]
        start = request.form["start"]
        end = request.form["end"]
        c.execute("SELECT * FROM vehicles WHERE id=?", (v_id,))
        veh = c.fetchone()
        if not veh:
            message = "Vehicle not found"
        else:
            try:
                d1 = datetime.strptime(start, "%Y-%m-%d")
                d2 = datetime.strptime(end, "%Y-%m-%d")
                days = (d2 - d1).days + 1
                if days <= 0:
                    message = "End date must be after start date"
                else:
                    c.execute("SELECT * FROM bookings WHERE vehicle_id=? AND NOT (end_date <? OR start_date >?)", (v_id, start, end))
                    if c.fetchone():
                        message = f"Sorry, {veh[1]} already booked on those dates"
                    else:
                        total = days * veh[2]
                        c.execute("INSERT INTO bookings (vehicle_id, vehicle_name, customer, cust_phone, start_date, end_date, days, total) VALUES (?,?,?,?,?,?,?,?)", (v_id, veh[1], customer, cust_phone, start, end, days, total))
                        conn.commit()
                        message = f"Booked! {veh[1]} for {days} days. Total: ${total}"
                        wa_text = f"NEW BOOKING: {veh[1]} booked by {customer} ({cust_phone}) from {start} to {end}. Total ${total}"
                        whatsapp_link = f"https://wa.me/{OWNER_PHONE}?text={wa_text.replace(' ', '%20')}"
            except Exception as e:
                message = f"Error: {e}"
    conn.close()
    return render_template("index.html", vehicles=vehicles, message=message, whatsapp_link=whatsapp_link)

@app.route("/admin", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
            return redirect(url_for("admin"))
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM bookings ORDER BY id DESC")
    bookings = c.fetchall()
    c.execute("SELECT SUM(total) FROM bookings")
    total_income = c.fetchone()[0] or 0
    conn.close()
    return render_template("admin.html", bookings=bookings, total_income=total_income)

@app.route("/admin/delete/<int:bid>")
def delete_booking(bid):
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (bid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

@app.route("/admin/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

if __name__ == "__main__":
    app.run(debug=True)
