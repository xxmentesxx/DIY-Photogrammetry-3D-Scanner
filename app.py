from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
from PIL import Image
import io, base64, os, requests, threading, logging, socket, time, json

# --- AYARLAR ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SETTINGS_FILE = os.path.join(BASE_DIR, "ayarlar.json")
PHOTOS_DIR = os.path.join(BASE_DIR, "Photos")

session = requests.Session()

def load_data():
    default = {
        'esp_ip': "192.168.1.XX",
        'total_photos': 50,
        'z_levels': 5, 
        'capture_delay': 1.5,
        'manual_steps_z': 500,
        'manual_steps_t': 500,
        'crop': {'active': False, 'x': 0.0, 'y': 0.0, 'w': 1.0, 'h': 1.0},
        'table': {'delay': 3000, 'full_steps': 6150}, 
        'elevator': {'delay': 5000, 'max_limit': 5800, 'current_pos': 0},
        'servo': {'pos': 0, 'start_angle': 0, 'end_angle': 45}
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                data = json.load(f)
                if 'table' not in data: data['table'] = default['table']
                if 'elevator' not in data: data['elevator'] = default['elevator']
                if 'max_limit' not in data['elevator']: data['elevator']['max_limit'] = 5800
                if 'full_steps' not in data['table']: data['table']['full_steps'] = 6150
                return data
        except: return default
    return default

DATA = load_data()
POSITIONS = {
    'table_index': 0,
    'elevator': int(DATA['elevator']['current_pos']),
    'servo': int(DATA['servo']['pos'])
}
STATE = { 'running': False, 'paused': False, 'current_photo': 0, 'total': 0, 'current_level': 1 }

log = logging.getLogger('werkzeug'); log.setLevel(logging.ERROR)
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*", max_http_buffer_size=10000000, async_mode='threading')

def save_data():
    DATA['elevator']['current_pos'] = POSITIONS['elevator']
    DATA['servo']['pos'] = POSITIONS['servo']
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(DATA, f, indent=4)
    except: pass

def proje_hazirla():
    if not os.path.exists(PHOTOS_DIR): os.makedirs(PHOTOS_DIR)
    mevcut = [d for d in os.listdir(PHOTOS_DIR) if d.startswith("scan_")]
    max_num = 0
    for k in mevcut:
        try: num = int(k.split("_")[1]); max_num = max(max_num, num)
        except: pass
    yeni_ad = f"scan_{max_num+1:03d}"
    os.makedirs(os.path.join(PHOTOS_DIR, yeni_ad))
    return os.path.join(PHOTOS_DIR, yeni_ad), yeni_ad

AKTIF_YOL, AKTIF_AD = proje_hazirla()

@app.route('/')
def index(): return render_template('camera.html')

@app.route('/monitor')
def monitor(): return render_template('monitor.html')

# --- KAMERA YAYINI ---
@socketio.on('yayin_karesi')
def yayin(data): 
    socketio.emit('monitor_guncelle', data)

# --- AYARLAR ---
@app.route('/save_crop', methods=['POST'])
def save_crop():
    try:
        req = request.json
        DATA['crop'] = req
        save_data()
        socketio.emit('crop_update', DATA['crop'])
        return jsonify({"status": "ok"})
    except: return jsonify({"status": "error"})

@app.route('/settings', methods=['POST'])
def update_settings():
    req = request.json
    if 'z_levels' in req: DATA['z_levels'] = int(req['z_levels'])
    if 'esp_ip' in req: DATA['esp_ip'] = req['esp_ip']
    if 'total_photos' in req: DATA['total_photos'] = int(req['total_photos'])
    if 'capture_delay' in req: DATA['capture_delay'] = req['capture_delay']
    if 'manual_steps_z' in req: DATA['manual_steps_z'] = int(req['manual_steps_z'])
    if 'manual_steps_t' in req: DATA['manual_steps_t'] = int(req['manual_steps_t'])
    
    if 'elevator' in req:
        if 'delay' in req['elevator']: DATA['elevator']['delay'] = req['elevator']['delay']
        DATA['elevator']['max_limit'] = 5800
    
    if 'table' in req:
        if 'delay' in req['table']: DATA['table']['delay'] = req['table']['delay']
        if 'full_steps' in req['table']: DATA['table']['full_steps'] = int(req['table']['full_steps'])
        
    save_data()
    return jsonify({"status": "saved"})

# --- MOTORLAR ---
@app.route('/set_servo_angle', methods=['POST'])
def set_servo_angle():
    try: 
        angle = int(request.json['val'])
        # Timeout artırıldı
        session.get(f"http://{DATA['esp_ip']}/action", params={"type": "servo", "val": angle}, timeout=5)
        POSITIONS['servo'] = angle
        save_data()
        socketio.emit('pos_update', POSITIONS)
        return jsonify({"status": "ok"})
    except: return jsonify({"status": "error"})

@app.route('/save_servo_calib', methods=['POST'])
def save_servo_calib():
    type = request.json['type']
    if type == 'start': DATA['servo']['start_angle'] = POSITIONS['servo']
    elif type == 'end': DATA['servo']['end_angle'] = POSITIONS['servo']
    save_data()
    socketio.emit('load_settings', DATA)
    return jsonify({"status": "ok"})

@app.route('/move_elevator', methods=['POST'])
def move_elevator():
    direction = request.json['dir']
    try: steps = int(request.json['steps'])
    except: steps = 500
    
    current = POSITIONS['elevator']
    max_limit = 5800

    if direction == 'zero':
        if current > 0:
            try: 
                # Z Eksenini 0'a indirmek uzun sürebilir, timeout 20 saniye yapıldı
                session.get(f"http://{DATA['esp_ip']}/action", params={"type": "step", "motor": "elevator", "dir": "cw", "steps": current, "delay": DATA['elevator']['delay']}, timeout=20)
            except: pass
        POSITIONS['elevator'] = 0
        save_data()
        socketio.emit('pos_update', POSITIONS)
        return jsonify({"status": "ok"})

    if direction == 'ccw': # Yukarı
        if current >= max_limit: return jsonify({"status": "limit"})
        if current + steps > max_limit: steps = max_limit - current
        new_pos = current + steps
    elif direction == 'cw': # Aşağı
        if current <= 0: return jsonify({"status": "limit"})
        if current - steps < 0: steps = current
        new_pos = current - steps

    if steps > 0:
        try:
            # Normal hareket için timeout 15 saniye yapıldı
            session.get(f"http://{DATA['esp_ip']}/action", params={"type": "step", "motor": "elevator", "dir": direction, "steps": steps, "delay": DATA['elevator']['delay']}, timeout=15)
            POSITIONS['elevator'] = new_pos
            save_data()
            socketio.emit('pos_update', POSITIONS)
        except: pass

    return jsonify({"status": "ok"})

@app.route('/move_table_photo', methods=['POST'])
def move_table_photo():
    direction = request.json['dir']
    
    if direction == 'zero':
        POSITIONS['table_index'] = 0
        socketio.emit('pos_update', POSITIONS)
        return jsonify({"status": "ok"})

    full = int(DATA['table']['full_steps'])
    total = int(DATA['total_photos'])
    if total == 0: total = 50
    step_size = int(full / total)
    
    dir_cmd = 'cw' if direction == 'next' else 'ccw'
    if 'steps' in request.json and request.json['steps']:
        step_size = int(request.json['steps'])

    try:
        # Timeout 15 saniye yapıldı
        session.get(f"http://{DATA['esp_ip']}/action", params={"type": "step", "motor": "table", "dir": dir_cmd, "steps": step_size, "delay": DATA['table']['delay']}, timeout=15)
        if direction == 'next': POSITIONS['table_index'] += 1
        else: POSITIONS['table_index'] -= 1
        socketio.emit('pos_update', POSITIONS)
    except: pass
    return jsonify({"status": "ok"})

@app.route('/set_home', methods=['POST'])
def set_home():
    motor = request.json['motor']
    if motor == 'elevator': POSITIONS['elevator'] = 0
    elif motor == 'table': POSITIONS['table_index'] = 0
    elif motor == 'servo': POSITIONS['servo'] = 0
    save_data()
    socketio.emit('pos_update', POSITIONS)
    return jsonify({"status": "ok"})

# --- SIFIRLAMA (RESTART) ---
def go_home_and_reset():
    """Motorları sıfıra götürür ve sistemi 'Start'a basılacak hale getirir."""
    socketio.emit('alert', "Sıfırlanıyor... Lütfen Bekleyin.")
    
    # 1. Asansör
    if POSITIONS['elevator'] > 0:
        # Timeout 20 saniye
        try: session.get(f"http://{DATA['esp_ip']}/action", params={"type": "step", "motor": "elevator", "dir": "cw", "steps": POSITIONS['elevator'], "delay": DATA['elevator']['delay']}, timeout=20)
        except: pass
        POSITIONS['elevator'] = 0
        socketio.emit('pos_update', POSITIONS)
        time.sleep(1)

    # 2. Servo
    start_angle = int(DATA['servo']['start_angle'])
    try: session.get(f"http://{DATA['esp_ip']}/action", params={"type": "servo", "val": start_angle}, timeout=5)
    except: pass
    POSITIONS['servo'] = start_angle
    socketio.emit('pos_update', POSITIONS)
    time.sleep(1)

    # 3. Tabla Sayacı
    POSITIONS['table_index'] = 0
    socketio.emit('pos_update', POSITIONS)
    
    # 4. Durumu Boşa Çıkar
    global STATE
    STATE['running'] = False
    STATE['paused'] = False
    STATE['current_photo'] = 0
    STATE['current_level'] = 1
    
    socketio.emit('durum_guncelle', STATE)
    socketio.emit('alert', "Sıfırlandı. Ayarlarınızı yapıp BAŞLAT'a basın.")

# --- TARAMA SENARYOSU ---
def tarama_baslat_logic():
    photos = int(DATA['total_photos'])
    levels = int(DATA['z_levels'])
    start_angle = int(DATA['servo']['start_angle'])
    end_angle = int(DATA['servo']['end_angle'])
    max_z = 5800
    
    z_step = 0
    if levels > 1: z_step = int(max_z / (levels - 1))
    
    full_turn = int(DATA['table']['full_steps'])
    step_per = int(full_turn / photos)
    remain = full_turn - (step_per * photos)
    
    STATE['total'] = photos * levels
    
    # Başlangıç Kontrol
    if POSITIONS['servo'] != start_angle:
        try: session.get(f"http://{DATA['esp_ip']}/action", params={"type": "servo", "val": start_angle}, timeout=5)
        except: pass
        POSITIONS['servo'] = start_angle
        socketio.emit('pos_update', POSITIONS)
        time.sleep(1)

    for level in range(levels):
        while STATE['paused']: 
            if not STATE['running']: break
            socketio.emit('durum_guncelle', STATE)
            time.sleep(0.5)
        if not STATE['running']: break

        STATE['current_level'] = level + 1
        
        if level > 0:
            socketio.emit('alert', f"Katman {level+1} Hazırlanıyor...")
            
            # Z Hareketi
            current_step = z_step
            if POSITIONS['elevator'] + z_step > max_z: current_step = max_z - POSITIONS['elevator']
            
            if current_step > 0:
                # Timeout 15 saniye
                try: session.get(f"http://{DATA['esp_ip']}/action", params={"type": "step", "motor": "elevator", "dir": "ccw", "steps": current_step, "delay": DATA['elevator']['delay']}, timeout=15)
                except: pass
                time.sleep(1) 
                POSITIONS['elevator'] += current_step
                socketio.emit('pos_update', POSITIONS)
                save_data()
            
            # Servo Hareketi
            ratio = level / (levels - 1)
            target = int(start_angle + (ratio * (end_angle - start_angle)))
            if POSITIONS['servo'] != target:
                try: session.get(f"http://{DATA['esp_ip']}/action", params={"type": "servo", "val": target}, timeout=5)
                except: pass
                POSITIONS['servo'] = target
                socketio.emit('pos_update', POSITIONS)
                time.sleep(1)

        for i in range(1, photos + 1):
            while STATE['paused']: 
                if not STATE['running']: break
                socketio.emit('durum_guncelle', STATE)
                time.sleep(0.5)
            if not STATE['running']: break

            STATE['current_photo'] = (level * photos) + i
            socketio.emit('durum_guncelle', STATE)
            
            # Çek
            socketio.emit('foto_cek')
            time.sleep(float(DATA['capture_delay']))
            
            # Dön
            curr_s = step_per
            if i == photos: curr_s += remain
            
            try:
                # Timeout 15 saniye
                session.get(f"http://{DATA['esp_ip']}/action", params={"type": "step", "motor": "table", "dir": "cw", "steps": curr_s, "delay": DATA['table']['delay']}, timeout=15)
                POSITIONS['table_index'] = i
                socketio.emit('pos_update', POSITIONS)
            except: pass
        
        POSITIONS['table_index'] = 0
        socketio.emit('pos_update', POSITIONS)

    STATE['running'] = False
    socketio.emit('durum_guncelle', STATE)
    
    # Bittiğinde de sıfıra dön ve bekle
    if STATE['current_photo'] >= STATE['total']:
        threading.Thread(target=go_home_and_reset).start()

@app.route('/yukle', methods=['POST'])
def yukle():
    try:
        data = request.json
        img_data = data['resim']; _, encoded = img_data.split(",", 1)
        binary = base64.b64decode(encoded); image = Image.open(io.BytesIO(binary))
        
        if DATA['crop']['active']:
            w, h = image.size
            cx = int(DATA['crop']['x'] * w)
            cy = int(DATA['crop']['y'] * h)
            cw = int(DATA['crop']['w'] * w)
            ch = int(DATA['crop']['h'] * h)
            if cw > 0 and ch > 0: image = image.crop((cx, cy, cx + cw, cy + ch))

        ad = f"{AKTIF_AD}_L{STATE['current_level']}_P{STATE['current_photo']:03d}.jpg"
        image.save(os.path.join(AKTIF_YOL, ad), quality=95)
        socketio.emit('foto_tamamlandi')
        return jsonify({"durum": "ok"})
    except: return jsonify({"durum": "hata"}), 500

@socketio.on('connect')
def on_connect():
    socketio.emit('pos_update', POSITIONS)
    socketio.emit('load_settings', DATA)
    socketio.emit('crop_update', DATA['crop'])
    socketio.emit('durum_guncelle', STATE)
    socketio.emit('alert', f"Klasör: {AKTIF_AD}")

@socketio.on('komut')
def komut_islet(data):
    cmd = data.get('tur')
    
    if cmd == 'start': 
        if STATE['paused']: 
            STATE['paused'] = False
            socketio.emit('durum_guncelle', STATE)
        elif not STATE['running']: 
            global AKTIF_YOL, AKTIF_AD
            AKTIF_YOL, AKTIF_AD = proje_hazirla()
            socketio.emit('alert', f"Yeni Klasör: {AKTIF_AD}")
            STATE['running'] = True
            STATE['paused'] = False
            socketio.emit('durum_guncelle', STATE)
            threading.Thread(target=tarama_baslat_logic).start()
    
    elif cmd == 'pause':
        if STATE['running']: 
            STATE['paused'] = True
            socketio.emit('durum_guncelle', STATE)
    
    elif cmd == 'restart': 
        STATE['running'] = True 
        threading.Thread(target=go_home_and_reset).start()
        
    elif cmd == 'new': 
        AKTIF_YOL, AKTIF_AD = proje_hazirla()
        socketio.emit('alert', f"Yeni Klasör: {AKTIF_AD}")

@socketio.on('yayin_karesi')
def yayin(data): socketio.emit('monitor_guncelle', data)

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try: s.connect(("8.8.8.8", 80)); ip = s.getsockname()[0]
    except: ip = "127.0.0.1"
    s.close()
    print(f"BAĞLANTI ADRESİ: https://{ip}:5000")
    socketio.run(app, host='0.0.0.0', port=5000, ssl_context='adhoc', debug=False)