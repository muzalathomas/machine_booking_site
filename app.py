from flask import Flask, render_template, request, session, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = "travis_secret_2024"

YOUR_PHONE = "260963329816"
ADMIN_PASSWORD = "travis123"

VEHICLES_DATA = [
    ("LB 02-MH47", 100),
    ("LB 03-MH29", 100),
    ("LB 04-MH41", 100),
    ("LB 05-MH42", 100),
    ("LB 16-MH63", 100),
    ("LB 17-MH64", 100),
    ("LB 18-MH65", 100),
    ("T07-MH46", 100),
    ("TA 08 05-MH37", 100),
    ("TA 76-MH66", 100)
]


def init_db():
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS vehicles (id INTEGER PRIMARY KEY, name TEXT, price INTEGER)')
    c.execute('CREATE TABLE IF NOT EXISTS bookings (id INTEGER PRIMARY KEY, vehicle_id INTEGER, customer TEXT, phone TEXT, start TEXT, end TEXT, total_price INTEGER, days INTEGER)')
    c.execute("SELECT count(*) FROM vehicles")
    if c.fetchone()[0] == 0:
        c.executemany("INSERT INTO vehicles (name, price) VALUES (?,?)", VEHICLES_DATA)
        conn.commit()
    conn.close()

# THIS LINE FIXES RENDER - create DB on startup
init_db()

def is_available(vehicle_id, new_start, new_end):
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("SELECT start, end FROM bookings WHERE vehicle_id=?", (vehicle_id,))
    for s, e in c.fetchall():
        if new_start < e and new_end > s:
            conn.close()
            return False, f"Booked from {s} to {e}"
    conn.close()
    return True, "Available"

def calc_days_price(start_str, end_str, price_per_day):
    s = datetime.strptime(start_str, "%Y-%m-%d")
    e = datetime.strptime(end_str, "%Y-%m-%d")
    days = (e - s).days
    if days < 1: days = 1
    total = days * price_per_day
    return days, total

@app.route("/", methods=["GET", "POST"])
def index():
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    message = ""
    whatsapp_link = ""
    if request.method == "POST":
        vid = request.form["vehicle_id"]
        customer = request.form["customer"]
        cust_phone = request.form["cust_phone"]
        start = request.form["start"]
        end = request.form["end"]
        c.execute("SELECT name, price FROM vehicles WHERE id=?", (vid,))
        row = c.fetchone()
        if not row:
            message = "Vehicle not found"
        else:
            vname, vprice = row[0], row[1]
            if start >= end:
                message = "ERROR: End date must be after start date"
            else:
                ok, msg = is_available(vid, start, end)
                if not ok:
                    message = f"NOT AVAILABLE - {msg}"
                else:
                    days, total = calc_days_price(start, end, vprice)
                    c.execute("INSERT INTO bookings (vehicle_id, customer, phone, start, end, total_price, days) VALUES (?,?,?,?,?,?,?)", (vid, customer, cust_phone, start, end, total, days))
                    conn.commit()
                    message = f"SUCCESS! {vname} booked for {customer} - {days} day(s) = K{total}"
                    text = f"NEW BOOKING!%0AVehicle: {vname}%0ACustomer: {customer} ({cust_phone})%0AFrom: {start} To: {end}%0A{days} days = K{total}"
                    whatsapp_link = f"https://wa.me/{YOUR_PHONE}?text={text}"
    c.execute("SELECT * FROM vehicles")
    vehicles = c.fetchall()
    conn.close()
    return render_template("index.html", vehicles=vehicles, message=message, whatsapp_link=whatsapp_link)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin"] = True
        else:
            return render_template("admin_login.html", error="Wrong password")
    if not session.get("admin"):
        return render_template("admin_login.html")
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("SELECT b.id, v.name, v.price, b.customer, b.phone, b.start, b.end, b.days, b.total_price FROM bookings b JOIN vehicles v ON b.vehicle_id=v.id ORDER BY b.start DESC")
    bookings = c.fetchall()
    total_income = sum([b[8] for b in bookings]) if bookings else 0
    conn.close()
    return render_template("admin.html", bookings=bookings, total_income=total_income)

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("index"))

@app.route("/delete/<int:bid>")
def delete_booking(bid):
    if not session.get("admin"):
        return redirect(url_for("admin"))
    conn = sqlite3.connect('booking.db')
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (bid,))
    conn.commit()
    conn.close()
    return redirect(url_for("admin"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
