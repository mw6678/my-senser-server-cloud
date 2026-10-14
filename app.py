from flask import Flask, request, jsonify, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)

# 데이터베이스 초기화 (온습도, 수위 데이터에 맞춘 테이블 생성)
def init_db():
    conn = sqlite3.connect('sensor_integrated.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS sensor_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id TEXT,
            device_id TEXT,
            temp REAL,
            humi REAL,
            water INTEGER,
            time TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# 1. ESP32가 데이터를 전송하는 API 주소 (POST)
# 예: /api/v1/data/companyA/device_001
@app.route('/api/v1/data/<company_id>/<device_id>', methods=['POST'])
def receive_sensor_data(company_id, device_id):
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No data provided"}), 400

    temp = data.get('temp', 0.0)
    humi = data.get('humi', 0.0)
    water = data.get('water', 0)
    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # DB에 저장
    conn = sqlite3.connect('sensor_integrated.db')
    conn.execute('''
        INSERT INTO sensor_logs (company_id, device_id, temp, humi, water, time)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (company_id, device_id, temp, humi, water, current_time))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success", 
        "company": company_id, 
        "device": device_id, 
        "time": current_time
    })

# 2. 회사별 / 기기별 실시간 관제 대시보드 (GUI)
# 예: http://서버주소/dashboard/companyA/device_001
@app.route('/dashboard/<company_id>/<device_id>')
def device_dashboard(company_id, device_id):
    conn = sqlite3.connect('sensor_integrated.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT temp, humi, water, time 
        FROM sensor_logs 
        WHERE company_id = ? AND device_id = ? 
        ORDER BY id DESC LIMIT 1
    ''', (company_id, device_id))
    latest = cursor.fetchone()
    conn.close()

    if not latest:
        latest = (0.0, 0.0, 0, "데이터 수신 이력 없음")

    # 웹 화면 HTML 렌더링
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>{company_id} - {device_id} 모니터링</title>
        <meta http-equiv="refresh" content="5"> <!-- 5초마다 새로고침 -->
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f6f9; text-align: center; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); }}
            h1 {{ color: #333; font-size: 20px; }}
            .badge {{ background: #007bff; color: white; padding: 5px 10px; border-radius: 4px; font-size: 14px; }}
            .card {{ background: #e9ecef; margin: 15px 0; padding: 20px; border-radius: 8px; font-size: 20px; font-weight: bold; display: flex; justify-content: space-between; }}
            .time {{ color: #666; font-size: 13px; margin-top: 15px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>환경 및 수위 모니터링</h1>
            <p>회사: <span class="badge">{company_id}</span> | 기기 ID: <span class="badge">{device_id}</span></p>
            
            <div class="card" style="background: #e3f2fd;"><span>온도 (Temperature)</span> <span>{latest[0]} °C</span></div>
            <div class="card" style="background: #e8f5e9;"><span>습도 (Humidity)</span> <span>{latest[1]} %</span></div>
            <div class="card" style="background: #fff3e0;"><span>수위 센서 (HW-038)</span> <span>{latest[2]}</span></div>
            
            <div class="time">마지막 수신 시간: {latest[3]}</div>
        </div>
    </body>
    </html>
    """
    return render_template_string(html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)