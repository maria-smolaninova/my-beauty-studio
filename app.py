from flask import Flask, render_template, request, redirect, url_for, jsonify, session  # Добавили session для авторизации
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.secret_key = 'super_secret_beauty_key_2026'  # Секретный ключ для защиты сессий администратора

# Имя файла, где будут вечно храниться наши записи клиентов
DATA_FILE = 'appointments.json'

# Услуги с категориями и длительностью из твоей БД Access
SERVICES = [
    {"id": 1, "name": "Женская стрижка + укладка", "description": "Создание идеальной формы и профессиональная укладка.", "price": 2500, "category": "hair", "duration": 60},
    {"id": 2, "name": "Сложное окрашивание (Airtouch)", "description": "Плавные переходы, бережное осветление и роскошный цвет.", "price": 7500, "category": "hair", "duration": 180},
    {"id": 3, "name": "Маникюр с покрытием гель-лак", "description": "Аккуратный уход за кутикулой и стойкое цветное покрытие.", "price": 2000, "category": "nails", "duration": 90},
    {"id": 4, "name": "Смарт-педикюр", "description": "Инновационный уход за стопами с использованием смарт-дисков.", "price": 2800, "category": "nails", "duration": 80},
    {"id": 5, "name": "Классическое наращивание ресниц", "description": "Естественный и выразительный взгляд с качественными материалами.", "price": 2200, "category": "lashes", "duration": 120},
    {"id": 6, "name": "Ламинирование бровей и ресниц", "description": "Глубокий уход, фиксация формы и яркий изгиб.", "price": 3000, "category": "lashes", "duration": 90},
    {"id": 7, "name": "Мужская стрижка + оформление бороды", "description": "Стильный образ, четкие линии и уход за бородой.", "price": 1800, "category": "barber", "duration": 45},
    {"id": 8, "name": "Комбинированный педикюр с покрытием", "description": "Полная обработка пальчиков и стопы плюс стойкий лак.", "price": 3200, "category": "nails", "duration": 90},
    {"id": 9, "name": "Окрашивание и архитектура бровей хной", "description": "Подбор идеальной формы и стойкое натуральное окрашивание.", "price": 1500, "category": "brows", "duration": 40},
]

# Мастера из твоей базы данных Access
MASTERS = [
    {"id": 1, "name": "Ковалева Алина Игоревна", "specialization": "Парикмахер-стилист", "category": "hair"},
    {"id": 2, "name": "Морозова Дарья Сергеевна", "specialization": "Мастер-маникюра", "category": "nails"},
    {"id": 3, "name": "Петрова Ксения Викторовна", "specialization": "Лешмейкер", "category": "lashes"},
    {"id": 4, "name": "Тихонов Дмитрий Алексеевич", "specialization": "Топ-барбер / Мужской мастер", "category": "barber"},
    {"id": 5, "name": "Соколова Елена Николаевна", "specialization": "Мастер педикюра и подолог", "category": "nails"},
    {"id": 6, "name": "Васина Алена Игоревна", "specialization": "Бровист-визажист", "category": "brows"},
    {"id": 7, "name": "Кузнецова Ольга Владимировна", "specialization": "Парикмахер-колорист", "category": "hair"}
]

def load_appointments():
    """Загружает все записи из файла JSON. Если файла нет, возвращает пустой список."""
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []

def save_appointment(appointment):
    """Добавляет новую запись в файл JSON."""
    appointments = load_appointments()
    appointments.append(appointment)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(appointments, f, ensure_ascii=False, indent=4)

def get_booked_slots_dict():
    """
    Преобразует список записей из файла в удобный формат для проверки коллизий:
    { 'YYYY-MM-DD': { master_id: [ (start_min, end_min), ... ] } }
    """
    appointments = load_appointments()
    booked = {}
    
    for appt in appointments:
        date = appt['date']
        master_id = appt['master_id']
        start_time = appt['time']
        service_id = appt['service_id']
        
        # Находим услугу, чтобы узнать длительность
        service = next((s for s in SERVICES if s['id'] == service_id), None)
        if not service:
            continue
            
        duration = service['duration']
        
        # Переводим ЧЧ:ММ в минуты от начала дня
        start_h, start_m = map(int, start_time.split(':'))
        start_total = start_h * 60 + start_m
        end_total = start_total + duration
        
        if date not in booked:
            booked[date] = {}
        if master_id not in booked[date]:
            booked[date][master_id] = []
            
        booked[date][master_id].append((start_total, end_total))
        
    return booked

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html', services=SERVICES)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        date = request.form['date']
        time = request.form['time']
        service_id = int(request.form['service'])
        master_id = int(request.form.get('master', 0))
        
        service = next((s for s in SERVICES if s['id'] == service_id), None)
        master = next((m for m in MASTERS if m['id'] == master_id), None)
        
        if service and master:
            # Создаем структуру записи, идеальную для последующего экспорта
            new_booking = {
                "client_name": name,
                "client_phone": phone,
                "date": date,
                "time": time,
                "service_id": service_id,
                "service_name": service['name'],
                "master_id": master_id,
                "master_name": master['name'],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "imported": False  # Маркер! Покажет, что запись еще не перенесена в Access
            }
            # Сохраняем в бэкэнд-файл
            save_appointment(new_booking)
        
        return render_template('confirmation.html', name=name, phone=phone, date=date, time=time, service=service, master=master)
        
    return render_template('booking.html', services=SERVICES, masters=MASTERS)

@app.route('/available_times', methods=['POST'])
def available_times():
    date = request.form['date']
    service_id = int(request.form.get('service_id', 0))
    master_id = int(request.form.get('master_id', 0))
    
    service = next((s for s in SERVICES if s['id'] == service_id), None)
    if not service:
        return jsonify({'available': []})
        
    duration = service['duration']
    
    OPEN_TIME = 10 * 60  # 10:00
    CLOSE_TIME = 21 * 60 # 21:00
    STEP = 30 
    
    # Динамически подгружаем занятые интервалы из сохраненных файлов
    booked_slots = get_booked_slots_dict()
    master_booked = booked_slots.get(date, {}).get(master_id, [])
    
    available = []
    
    for start_min in range(OPEN_TIME, CLOSE_TIME, STEP):
        end_min = start_min + duration
        
        if end_min > CLOSE_TIME:
            continue
            
        has_collision = False
        for b_start, b_end in master_booked:
            if start_min < b_end and end_min > b_start:
                has_collision = True
                break
                
        if not has_collision:
            h = start_min // 60
            m = start_min % 60
            available.append(f"{h:02d}:{m:02d}")
            
    return jsonify({'available': available})

# ==========================================
# МОДУЛЬ АДМИНИСТРАТОРА И БЕЗОПАСНОСТИ
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Данные авторизации (можно изменить на свои)
        if username == 'admin' and password == 'beauty123':
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            error = 'Неверный логин или пароль. Доступ заблокирован!'
            
    return render_template('admin_login.html', error=error)

@app.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)  # Стираем сессию при выходе
    return redirect(url_for('index'))

@app.route('/admin/dashboard')
def admin_dashboard():
    # Проверяем, авторизован ли пользователь как админ
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
        
    appointments = load_appointments()
    
    # Разделяем записи на новые и уже обработанные
    new_orders = [a for a in appointments if not a.get('imported', False)]
    imported_orders = [a for a in appointments if a.get('imported', False)]
    
    return render_template('admin_dashboard.html', new_orders=new_orders, imported_orders=imported_orders)

@app.route('/admin/mark_imported', methods=['POST'])
def mark_imported():
    # Защита обработчика кнопки
    if not session.get('logged_in'):
        return redirect(url_for('admin_login'))
        
    appointments = load_appointments()
    
    # Помечаем ВСЕ текущие новые записи как импортированные
    for appt in appointments:
        if not appt.get('imported', False):
            appt['imported'] = True
            
    # Перезаписываем файл JSON с обновленными статусами
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(appointments, f, ensure_ascii=False, indent=4)
        
    return redirect(url_for('admin_dashboard'))
    
if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)