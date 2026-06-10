from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)
DB_NAME = 'sleep_db.db'

def init_db():
    """Membuat tabel dengan kolom lengkap untuk semua sensor."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            suhu REAL,
            kelembapan REAL,
            cahaya REAL,
            suara TEXT,
            total_skor INTEGER,
            status TEXT
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def dashboard():
    """Mengambil data terakhir untuk KPI dan histori grafik."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Ambil 20 data terakhir untuk grafik
    cursor.execute("""
        SELECT timestamp, suhu, kelembapan, cahaya, suara, total_skor, status 
        FROM sensor_data ORDER BY id DESC LIMIT 20
    """)
    rows = cursor.fetchall()
    conn.close()
    rows.reverse() 
    
    # Siapkan data default jika database masih kosong
    kpi = {"suhu": "--", "kelembapan": "--", "cahaya": "--", "suara": "--", "status": "Menunggu Data...", "skor": 0}
    if rows:
        last = rows[-1] # Data paling terakhir untuk KPI atas
        kpi = {
            "suhu": f"{last[1]:.1f}°C" if last[1] is not None else "ERR",
            "kelembapan": f"{last[2]:.1f}%" if last[2] is not None else "ERR",
            "cahaya": f"{int(last[3])} lx" if last[3] is not None else "ERR",
            "suara": last[4],
            "status": last[6],
            "skor": last[5]
        }

    # Ekstrak data untuk grafik
    data_grafik = {
        "timestamps": [r[0].split()[1] for r in rows], # Ambil jamnya saja (HH:MM:SS)
        "suhu": [r[1] for r in rows],
        "kelembapan": [r[2] for r in rows],
        "cahaya": [r[3] for r in rows],
        # Ubah "BISING" jadi 1 dan "TENANG" jadi 0 untuk Bar Plot
        "suara": [1 if r[4] == "BISING" else 0 for r in rows]
    }
    
    return render_template('dashboard.html', kpi=kpi, grafik=data_grafik)

@app.route('/api/data', methods=['POST'])
def receive_data():
    """Menerima struktur data lengkap dari ESP32."""
    try:
        data = request.get_json()
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sensor_data (suhu, kelembapan, cahaya, suara, total_skor, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (data['suhu'], data['kelembapan'], data['cahaya'], data['suara'], data['total_skor'], data['status']))
        conn.commit()
        conn.close()
        
        return jsonify({"status": "success"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=5000, debug=True)