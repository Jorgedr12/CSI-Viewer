import os
from datetime import datetime, timedelta
# CÓDIGO CORREGIDO (Después)
from flask import (Flask, render_template, request, send_from_directory, abort,
                   url_for, redirect, flash)
from flask_login import (LoginManager, UserMixin, login_user, logout_user,
                       login_required, current_user)
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash



# ==========================
# 1. CONFIGURACIÓN INICIAL
# ==========================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'El-pirata-de-culiacan-nunca-debio-de-haber-muerto'
app.config['BASE_PATH'] = "imagenes"

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = "Por favor, inicie sesión para acceder a esta página."
login_manager.login_message_category = "danger"


# ==========================================================
# === AÑADIR ESTE BLOQUE PARA EL AÑO AUTOMÁTICO EN EL FOOTER ===
# ==========================================================
@app.context_processor
def inject_year():
    """ Inyecta el año actual en todas las plantillas. """
    return {'current_year': datetime.utcnow().year}
# ==========================================================

# ==========================
# 2. MODELO DE USUARIO Y BASE DE DATOS SIMULADA
# ==========================
class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def set_password(password):
        return generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

users_db = {
    "1": User(id="1", username="admin", password_hash=generate_password_hash("@Cebiche123"))
}

@login_manager.user_loader
def load_user(user_id):
    return users_db.get(user_id)

# ==========================
# 3. FORMULARIO DE LOGIN
# ==========================
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Iniciar Sesión')

# ==========================
# 4. RUTAS
# ==========================
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = next((u for u in users_db.values() if u.username == form.username.data), None)
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('index'))
        else:
            flash('Usuario o contraseña inválidos')
            return redirect(url_for('login'))
    
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route("/")
@login_required
def index():
    weeks = group_by_weeks()
    return render_template('index.html', weeks=weeks)

@app.route("/day/<day>")
@login_required
def show_day(day):
    day_path = os.path.join(app.config['BASE_PATH'], day)
    if not os.path.exists(day_path): abort(404)
    display_day = datetime.strptime(day, "%Y-%m-%d").strftime('%d/%m/%Y')
    hours_with_data = get_hour_data(day_path)
    return render_template('day.html', day=day, display_day=display_day, hours=hours_with_data)

@app.route("/day/<day>/hour/<hour>")
@login_required
def show_hour(day, hour):
    hour_path = os.path.join(app.config['BASE_PATH'], day, hour)
    if not os.path.exists(hour_path):
        abort(404)

    # --- FUNCIÓN PARA ORDENAR LAS HORAS ---
    # SE ELIMINA LA FUNCIÓN 'sort_key' DE AQUÍ PORQUE NO SE USABA

    # --- INICIO DE CAMBIOS PARA PAGINACIÓN ---

    # 1. Obtener el número de página de la URL (ej. ?page=2), por defecto es 1.
    page = request.args.get('page', 1, type=int)
    IMAGES_PER_PAGE = 12  # Define cuántas imágenes mostrar por página.

    # 2. Obtener la lista completa de imágenes ORDENADAS
    all_images = sorted(os.listdir(hour_path)) # Se ordena alfabéticamente que es correcto para los nombres de archivo
    total_images = len(all_images)

    # ... (el resto de la función sigue igual) ...
    start_index = (page - 1) * IMAGES_PER_PAGE
    end_index = start_index + IMAGES_PER_PAGE
    images_on_page = all_images[start_index:end_index]

    total_pages = (total_images + IMAGES_PER_PAGE - 1) // IMAGES_PER_PAGE

    time_range = ""
    if images_on_page:
        def format_time(filename):
            base = os.path.splitext(filename)[0]
            return base.replace("m", "m ").replace("s", "s")

        first_time = format_time(images_on_page[0])
        last_time = format_time(images_on_page[-1])
        time_range = f"({first_time} - {last_time})"

    display_day = datetime.strptime(day, "%Y-%m-%d").strftime('%d/%m/%Y')
    
    return render_template(
        'hour.html', 
        day=day, 
        display_day=display_day, 
        hour=hour, 
        images=images_on_page,
        page=page,
        total_pages=total_pages,
        time_range=time_range,
        IMAGES_PER_PAGE=IMAGES_PER_PAGE
    )


@app.route("/images/<path:filepath>")
@login_required
def serve_image_path(filepath):
    safe_path = os.path.abspath(os.path.join(app.config['BASE_PATH'], filepath))
    if not safe_path.startswith(os.path.abspath(app.config['BASE_PATH'])): abort(404)
    directory, filename = os.path.split(safe_path)
    return send_from_directory(directory, filename)

# ==========================
# 5. FUNCIONES DE AYUDA
# ==========================
def group_by_weeks():
    # ... (esta función no cambia)
    base_path = app.config['BASE_PATH']
    if not os.path.exists(base_path): return {}
    items = sorted(os.listdir(base_path), reverse=True)
    weeks = {}
    for item in items:
        if os.path.isdir(os.path.join(base_path, item)):
            try:
                date = datetime.strptime(item, "%Y-%m-%d")
                monday = date - timedelta(days=date.weekday())
                sunday = monday + timedelta(days=6)
                week_label = f"{monday.strftime('%d/%m/%Y')} - {sunday.strftime('%d/%m/%Y')}"
                if week_label not in weeks: weeks[week_label] = []
                weeks[week_label].append({'path': item, 'display': date.strftime('%d/%m/%Y')})
            except ValueError: continue
    return weeks

def get_hour_data(day_path):
    hour_data = []
    if not os.path.isdir(day_path): return hour_data
    hours_list = os.listdir(day_path)
    
    # --- LÓGICA DE ORDENAMIENTO CORREGIDA ---
    # Esta es la función que sí entiende "07_am", "12_pm", etc.
    def sort_key(hour_str):
        try:
            parts = hour_str.lower().split("_")
            hour_num = int(parts[0])
            ampm = parts[1] if len(parts) > 1 else "am"
            # Convierte a formato 24 horas para ordenar fácil
            if ampm == "pm" and hour_num != 12:
                hour_num += 12
            if ampm == "am" and hour_num == 12: # Medianoche
                hour_num = 0
            return hour_num
        except Exception:
            return 99  # Si algo falla (ej. un archivo .DS_Store), se va al final

    sorted_hours = sorted(hours_list, key=sort_key)
    # --- FIN DE LA CORRECCIÓN ---

    for hour in sorted_hours:
        hour_path = os.path.join(day_path, hour)
        if os.path.isdir(hour_path):
            images = sorted(os.listdir(hour_path))
            thumbnail = images[0] if images else None
            hour_data.append({"hour": hour, "thumbnail": thumbnail})
    return hour_data

# ==========================
# 6. EJECUCIÓN
# ==========================
if __name__ == "__main__":
    if not os.path.exists(app.config['BASE_PATH']):
        os.makedirs(app.config['BASE_PATH'])
    app.run(host="0.0.0.0", port=8080, debug=True)