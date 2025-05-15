from flask import Flask, render_template, redirect, url_for, request, session, flash, g
from flask_bcrypt import Bcrypt
import random
from werkzeug.exceptions import NotFound
import pymysql
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from itsdangerous import URLSafeSerializer as Serializer


app = Flask(__name__)
bcrypt = Bcrypt(app)
app.secret_key = "advpjsh"


ACCOUNT_SID = 'ACcfdb118333e0dca09eabacbb2310f371'
AUTH_TOKEN = 'd610e608f03572a47e8c1c00477790a7'
TWILIO_PHONE_NUMBER = '+19109712991'
client = Client(ACCOUNT_SID, AUTH_TOKEN)
serializer = Serializer(app.secret_key, salt="password-reset-salt")


def get_db():
    if "db" not in g:
        try:
            g.db = pymysql.connect(
                host="localhost",
                user="root",
                password="12072022",
                database="sector_transporte",
                cursorclass=pymysql.cursors.DictCursor
            )
            g.cursor = g.db.cursor()
        except pymysql.MySQLError as err:
            raise Exception(f"Error al conectar a la base de datos: {err}")
    return g.db, g.cursor

@app.teardown_appcontext
def close_connection(exception=None):
    cursor = g.pop("cursor", None)
    db = g.pop("db", None)

    if cursor is not None:
        try:
            cursor.close()
        except pymysql.MySQLError:
            pass

    if db is not None:
        try:
            db.close()
        except pymysql.MySQLError:
            pass



def generar_codigo_verificacion():
    return str(random.randint(100000, 999999))


def formatear_numero(numero):
    if not numero.startswith('+'):
        numero = '+57' + numero.lstrip('0')
    return numero


def enviar_mensaje_texto(destinatario, cuerpo):
    try:
        numero_formateado = formatear_numero(destinatario)
        mensaje = client.messages.create(
            body=cuerpo,
            from_=TWILIO_PHONE_NUMBER,
            to=numero_formateado
        )
        print(f"📤 Mensaje enviado con éxito! SID: {mensaje.sid}")
        return mensaje.sid
    except TwilioRestException as e:
        print(f" Error al enviar el mensaje: {str(e)}")
        return None


@app.route('/')
def pagina_principal():
    if 'email' in session:
        return redirect(url_for('index'))
    return render_template('base.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        primer_N = request.form.get('primer_N')
        segundo_N = request.form.get('segundo_N', '')
        primer_A = request.form.get('primer_A')
        segundo_A = request.form.get('segundo_A', '')
        celular = request.form.get('celular')
        email = request.form.get('email')
        cedula = request.form.get('cedula')
        tipo_usu = request.form.get('tipo_usu')
        password = request.form.get('password')
        if not all([primer_N, primer_A, celular, email, cedula, tipo_usu, password]):
            flash("Por favor, complete todos los campos obligatorios.", "error")
            return render_template('register.html')
        celular = celular.strip()
        if not celular.startswith('+57'):
            if celular.startswith('0'):
                celular = '+57' + celular[1:]
            elif celular.startswith('3'):
                celular = '+57' + celular
            else:
                celular = '+57' + celular  
        db, cursor = get_db()
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
        if cursor.fetchone():
            flash("El correo electrónico ya está registrado.", "error")
            return render_template('register.html')
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        try:
            cursor.execute(
                "INSERT INTO usuarios (primer_N, segundo_N, primer_A, segundo_A, celular, email, cedula, tipo_usu, password) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (primer_N, segundo_N, primer_A, segundo_A, celular, email, cedula, tipo_usu, hashed_password)
            )
            db.commit()
            session['email'] = email
            session['primer_N'] = primer_N
            session['primer_A'] = primer_A
            flash("Registro exitoso. Bienvenido!", "success")
            return redirect(url_for('login'))
        except pymysql.Error as e:
            db.rollback()
            flash(f"Error al registrar: {str(e)}", "error")
            return render_template('register.html')
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        tipo_usu = request.form.get('tipo_usu') 
        email = request.form.get('email')
        password = request.form.get('password')
        if not tipo_usu or not email or not password:
            flash("Por favor, complete todos los campos.", "error")
            return render_template('login.html')
        db, cursor = get_db()
        try:
            cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user and bcrypt.check_password_hash(user['password'], password):
                if user['tipo_usu'] == tipo_usu:
                    session['email'] = user['email']
                    session['primer_N'] = user['primer_N']
                    session['primer_A'] = user['primer_A']
                    session['tipo_usu'] = user['tipo_usu']
                    if user['tipo_usu'] == 'Administrador':
                        return redirect(url_for('index_admin'))
                    else:
                        return redirect(url_for('index'))
                else:
                    flash("El rol seleccionado no coincide con el registrado.", "error")
                    return render_template('login.html')
            else:
                flash("Rol, Usuario o contraseña incorrectos.", "error")
                return render_template('login.html')
        except pymysql.Error as e:
            flash(f"Error en la base de datos: {str(e)}", "error")
            return render_template('login.html')
    return render_template('login.html')




@app.route('/index')
def index():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('index.html', usuario=usuario)


@app.route('/mi_perfil')
def mi_perfil():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    email = session['email']
    db, cursor = get_db()
    cursor.execute("SELECT primer_N, segundo_N, primer_A, segundo_A, celular, email, cedula, tipo_usu FROM usuarios WHERE email = %s", (email,))
    user_data = cursor.fetchone()
    if not user_data:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    return render_template('mi_perfil.html', usuario=user_data)


@app.route('/actualizar_perfil', methods=['GET', 'POST'])
def actualizar_perfil():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    email_sesion = session['email']
    db, cursor = get_db()
    if request.method == 'POST':
        primer_N = request.form.get('primer_N')
        segundo_N = request.form.get('segundo_N', '')
        primer_A = request.form.get('primer_A')
        segundo_A = request.form.get('segundo_A', '')
        celular = request.form.get('celular')
        if not all([primer_N, segundo_N, primer_A, segundo_A, celular]):
            flash("Los campos obligatorios no pueden estar vacíos.", "error")
            return redirect(url_for('actualizar_perfil'))
        celular = celular.strip()
        if not celular.startswith('+57'):
            if celular.startswith('0'):
                celular = '+57' + celular[1:]
            elif celular.startswith('3'):
                celular = '+57' + celular
            else:
                celular = '+57' + celular 
        try:
            cursor.execute(
                "UPDATE usuarios SET primer_N = %s, segundo_N = %s, primer_A = %s, segundo_A = %s, celular = %s WHERE email = %s",
                (primer_N, segundo_N, primer_A, segundo_A, celular, email_sesion)
            )
            db.commit()
            session['primer_N'] = primer_N
            session['primer_A'] = primer_A
            flash("Perfil actualizado exitosamente.", "success")
            return redirect(url_for('mi_perfil'))
        except pymysql.Error as e:
            db.rollback()
            flash(f"Error en la base de datos: {str(e)}", "error")
            return redirect(url_for('actualizar_perfil'))
    cursor.execute("SELECT primer_N, segundo_N, primer_A, segundo_A, celular, email, cedula, tipo_usu FROM usuarios WHERE email = %s", (email_sesion,))
    user_data = cursor.fetchone()
    if not user_data:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('login'))
    return render_template('actualizar_perfil.html', usuario=user_data)


@app.route('/recuperar_password', methods=['GET', 'POST'])
def recuperar_password():
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    if request.method == 'POST':
        celular = request.form.get('celular')
        if not celular:
            return render_template('recuperar_password.html', usuario=usuario)
        celular = celular.strip()
        if not celular.startswith('+57'):
            if celular.startswith('0'):
                celular = '+57' + celular[1:]
            elif celular.startswith('3'):
                celular = '+57' + celular
            else:
                celular = '+57' + celular 
        try:
            db, cursor = get_db()
            cursor.execute("SELECT * FROM usuarios WHERE celular = %s", (celular,))
            usuario_db = cursor.fetchone()
            if usuario_db:
                usuario = usuario_db
                codigo = generar_codigo_verificacion()
                session['codigo_verificacion'] = codigo
                session['celular'] = celular
                mensaje = f"El código de verificación para restablecer su contraseña es: {codigo}"
                if enviar_mensaje_texto(celular, mensaje):
                    flash("le hemos enviado un código de verificación por mensaje de texto.", "success")
                    return redirect(url_for('verificar_codigo'))
                else:
                    flash("Error al enviar el mensaje de texto. Intenta de nuevo.", "error")
            else:
                flash("El número de teléfono no está registrado.", "error")
        except pymysql.Error as e:
            flash(f"Error en la base de datos: {str(e)}", "error")
        finally:
            cursor.close()
            db.close()

    return render_template('recuperar_password.html', usuario=usuario)


@app.route('/restablecer_password', methods=['GET', 'POST'])
def restablecer_password():
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    if 'celular' not in session or 'codigo_verificacion' not in session:
        flash("Sesión expirada. Intenta recuperar la contraseña de nuevo.", "error")
        return redirect(url_for('recuperar_password'))
    if request.method == 'POST':
        nueva_password = request.form.get('nueva_password')
        if not nueva_password:
            flash("Debes ingresar una nueva contraseña.", "error")
            return render_template('restablecer_password.html', usuario=usuario)
        celular = session['celular']
        hashed_password = bcrypt.generate_password_hash(nueva_password).decode('utf-8')
        db = None
        cursor = None
        try:
            db, cursor = get_db()
            cursor.execute("UPDATE usuarios SET password = %s WHERE celular = %s", (hashed_password, celular))
            db.commit()
            session.pop('codigo_verificacion', None)
            session.pop('celular', None)
            flash("Tu contraseña ha sido restablecida exitosamente.", "success")
            return redirect(url_for('login'))
        except pymysql.Error as e:
            if db:
                db.rollback()
            flash(f"Error en la base de datos: {str(e)}", "error")
            return render_template('restablecer_password.html', usuario=usuario)
        finally:
            if cursor:
                cursor.close()
            if db:
                db.close()
    return render_template('restablecer_password.html', usuario=usuario)


@app.route('/verificar_codigo', methods=['GET', 'POST'])
def verificar_codigo():
    if 'codigo_verificacion' not in session:
        flash("Sesión expirada. Intenta recuperar la contraseña de nuevo.", "error")
        return redirect(url_for('recuperar_password'))
    if request.method == 'POST':
        codigo_ingresado = request.form.get('codigo')
        codigo_guardado = session.get('codigo_verificacion')
        if codigo_ingresado == codigo_guardado:
            flash("Código verificado correctamente.", "success")
            return redirect(url_for('restablecer_password'))
        else:
            flash("Código incorrecto. Intenta de nuevo.", "error")
    return render_template('verificar_codigo.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/vehiculos')
def vehiculos():
    return render_template('vehiculos.html')


@app.route('/rutas')
def rutas():
    return render_template('rutas.html')


@app.route('/reservas')
def reservas():
    return render_template('reservas.html')


@app.route('/index_admin', methods=['GET', 'POST'])
def index_admin():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    db, cursor = get_db() 
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    cursor.execute("SELECT COUNT(*) AS total FROM usuarios")
    total_usuarios = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) AS total FROM vehiculos")
    total_vehiculos = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) AS total FROM conductores")
    total_conductores= cursor.fetchone()['total']    

    cursor.execute("SELECT COUNT(*) AS total FROM rutas")
    total_rutas= cursor.fetchone()['total'] 

    cursor.execute("SELECT COUNT(*) AS total FROM reservas")
    total_reservas= cursor.fetchone()['total'] 

    return render_template('index_admin.html', usuario=usuario, total_usuarios=total_usuarios, 
    total_vehiculos=total_vehiculos, total_conductores=total_conductores, total_rutas=total_rutas, total_reservas=total_reservas)


@app.route('/usuarios', methods=['GET', 'POST'])
def usuarios():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    db, cursor = get_db()
    search_term = request.form.get('search', '').strip() if request.method == 'POST' else ''
    base_query = "SELECT * FROM usuarios"
    params = []
    if search_term:
        search_query = """
            WHERE primer_N LIKE %s
            OR segundo_N LIKE %s
            OR primer_A LIKE %s
            OR segundo_A LIKE %s
            OR email LIKE %s
            OR cedula LIKE %s
        """
        like_pattern = f"%{search_term}%"
        params = [like_pattern] * 6
        base_query += search_query
    cursor.execute(base_query, params)
    lista_usuarios = cursor.fetchall()
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    return render_template('usuarios.html', usuario=usuario, usuarios=lista_usuarios)


@app.route('/editar_usuarios/<int:id>')
def editar_usuarios(id):
    db, cursor = get_db()
    cursor.execute("SELECT id_usu, primer_N, segundo_N, primer_A, segundo_A, celular, email, cedula, tipo_usu FROM usuarios WHERE id_usu= %s", (id,))
    usuario = cursor.fetchone()
    if not usuario:
        flash("Usuario no encontrado.", "error")
        return redirect(url_for('usuarios'))
    return render_template('editar_usuarios.html', usuario=usuario)


@app.route('/actualizar_usuario', methods=['GET','POST'])
def actualizar_usuario():
    db, cursor = get_db()
    try:
        id_usu = request.form['id_usu']
        primer_N =request.form['primer_N']
        segundo_N = request.form['segundo_N']
        primer_A = request.form['primer_A']
        segundo_A = request.form['segundo_A']
        celular = request.form['celular']
        email = request.form['email']
        cedula = request.form['cedula']
        tipo_usu = request.form['tipo_usu']
        cursor.execute("""
            UPDATE usuarios SET primer_N = %s,segundo_N = %s, primer_A = %s, segundo_A = %s, celular = %s, email = %s, cedula = %s, tipo_usu = %s
            WHERE id_usu = %s
        """, (primer_N, segundo_N, primer_A, segundo_A, celular, email, cedula, tipo_usu, id_usu))
        db.commit()
        flash("Usuario actualizado con éxito.", "success")
    except Exception as e:
        flash(f"Error al actualizar usuario: {str(e)}", "error")
    return redirect(url_for('usuarios'))


@app.route('/eliminar_usuario/', methods=['GET','POST'])
def eliminar_usuario():
    db, cursor = get_db()
    try:
        id_usu = request.form['id_usu']
        cursor.execute("DELETE FROM usuarios WHERE id_usu = %s", (id_usu,))
        db.commit()
        flash("Usuario eliminado correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar usuario: {str(e)}", "error")
    return redirect(url_for('usuarios'))


@app.route('/vehiculos_registrados', methods=['GET', 'POST'])
def vehiculos_registrados():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    db, cursor = get_db()
    search_term = request.form.get('search', '').strip() if request.method == 'POST' else ''
    base_query = "SELECT * FROM vehiculos"
    params = []
    if search_term:
        search_query = " WHERE placa LIKE %s OR marca LIKE %s"
        like_pattern = f"%{search_term}%"
        params = [like_pattern] * 2
        base_query += search_query
    cursor.execute(base_query, params)
    lista_vehiculos = cursor.fetchall()
    
    return render_template('vehiculos_registrados.html', usuario=usuario, vehiculos=lista_vehiculos)


@app.route('/editar_vehiculos/<int:id>')
def editar_vehiculos(id):
    db, cursor = get_db()
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    cursor.execute("""
        SELECT id_vehiculo, marca, modelo, placa, capacidad, tipo_vehiculo
        FROM vehiculos
        WHERE id_vehiculo = %s
    """, (id,))
    vehiculo = cursor.fetchone()
    if not vehiculo:
        flash("Vehículo no encontrado.", "error")
        return redirect(url_for('vehiculos_registrados'))
    return render_template('editar_vehiculos.html', usuario=usuario, vehiculo=vehiculo)


@app.route('/actualizar_vehiculo', methods=['POST'])
def actualizar_vehiculo():
    db, cursor = get_db()
    try:
        id_vehiculo = request.form['id_vehiculo']
        placa = request.form['placa']
        marca = request.form['marca']
        modelo = request.form['modelo']
        capacidad = request.form['capacidad']
        tipo_vehiculo= request.form['tipo_vehiculo']
        cursor.execute("""
            UPDATE vehiculos
            SET placa = %s, marca = %s, modelo = %s, capacidad = %s, tipo_vehiculo=%s
            WHERE id_vehiculo = %s
        """, (placa, marca, modelo, capacidad, tipo_vehiculo, id_vehiculo))
        db.commit()
        flash("Vehículo actualizado con éxito.", "success")
    except Exception as e:
        flash(f"Error al actualizar el vehículo: {str(e)}", "error")
    return redirect(url_for('vehiculos_registrados'))


@app.route('/eliminar_vehiculo/', methods=['GET','POST'])
def eliminar_vehiculo():
    db, cursor = get_db()
    try:
        id_vehiculo = request.form['id_vehiculo']
        cursor.execute("DELETE FROM vehiculos WHERE id_vehiculo = %s", (id_vehiculo,))
        db.commit()
        flash("vehiculo eliminado correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar Vehiculo: {str(e)}", "error")
    return redirect(url_for('vehiculos_registrados'))


@app.route('/conductores', methods=['GET', 'POST'])
def conductores():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    db, cursor = get_db()
    search_term = request.form.get('search', '').strip() if request.method == 'POST' else ''
    base_query = """
    SELECT * 
    FROM conductores c
    LEFT JOIN vehiculos v ON c.placa = v.placa
    """
    params = []
    if search_term:
        search_query = """
            WHERE nombre LIKE %s
            OR cedula LIKE %s
            OR telefono LIKE %s
            OR licencia LIKE %s
        """
        like_pattern = f"%{search_term}%"
        params = [like_pattern] * 4
        base_query += search_query
    cursor.execute(base_query, params)
    lista_conductores = cursor.fetchall()
    return render_template('conductores.html', usuario=usuario, conductores=lista_conductores)


@app.route('/editar_conductor/<int:id>', methods=['GET'])
def editar_conductor(id):
    db, cursor = get_db()
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }

    cursor.execute("""
        SELECT id_conductor, nombre, apellido, cedula, telefono, licencia, placa 
        FROM conductores
        WHERE id_conductor = %s
    """, (id,))
    conductor = cursor.fetchone()
    if not conductor:
        flash("Conductor no encontrado.", "error")
        return redirect(url_for('conductores'))
    return render_template('editar_conductor.html', usuario=usuario, conductor=conductor)


@app.route('/actualizar_conductor', methods=['POST'])
def actualizar_conductor():
    db, cursor = get_db()
    try:
        id_conductor = request.form['id_conductor']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        cedula = request.form['cedula']
        telefono = request.form['telefono']
        licencia = request.form['licencia']
        placa = request.form['placa']
        cursor.execute("""
            UPDATE conductores
            SET nombre = %s, apellido = %s, cedula = %s, telefono = %s, licencia = %s, placa = %s
            WHERE id_conductor = %s
        """, (nombre, apellido, cedula, telefono, licencia, placa, id_conductor))
        db.commit()
        flash("Conductor actualizado con éxito.", "success")
    except Exception as e:
        flash(f"Error al actualizar el Conductor: {str(e)}", "error")
    return redirect(url_for('conductores'))


@app.route('/eliminar_conductor/', methods=['GET','POST'])
def eliminar_conductor():
    db, cursor = get_db()
    try:
        id_conductor = request.form['id_conductor']
        cursor.execute("DELETE FROM conductores WHERE id_conductor= %s", (id_conductor,))
        db.commit()
        flash("Conductor eliminado correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar conductor: {str(e)}", "error")
    return redirect(url_for('conductores'))


@app.route('/rutas_activas', methods=['GET', 'POST'])
def rutas_activas():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    db, cursor = get_db()
    search_term = request.form.get('search', '').strip() if request.method == 'POST' else ''
    base_query = "SELECT * FROM rutas"
    params = []
    if search_term:
        search_query = " WHERE origen LIKE %s OR destino LIKE %s"
        like_pattern = f"%{search_term}%"
        params = [like_pattern] * 2
        base_query += search_query
    cursor.execute(base_query, params)
    lista_rutas = cursor.fetchall()
    
    return render_template('rutas_activas.html', usuario=usuario, rutas=lista_rutas)


@app.route('/editar_rutas/<int:id>')
def editar_rutas(id):
    db, cursor = get_db()
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    cursor.execute("SELECT *  FROM rutas WHERE id_ruta = %s", (id,))
    rutas = cursor.fetchone()
    if not rutas:
        flash("Vehículo no encontrado.", "error")
        return redirect(url_for('rutas_activas'))
    return render_template('editar_rutas.html', usuario=usuario, rutas=rutas)


@app.route('/actualizar_rutas', methods=['POST'])
def actualizar_rutas():
    db, cursor = get_db()
    try:
        id_ruta= request.form['id_ruta']
        origen = request.form['origen']
        destino = request.form['destino']
        distancia_km = request.form['distancia_km']
        duracion_aprox = request.form['duracion_aprox']
        dias_servicio= request.form['dias_servicio']
        estado= request.form['estado']
        cursor.execute("""
            UPDATE rutas
            SET origen = %s, destino = %s, distancia_km = %s, duracion_aprox = %s, dias_servicio = %s, estado = %s
            WHERE id_ruta = %s
        """, (origen, destino, distancia_km, duracion_aprox, dias_servicio, estado, id_ruta))
        db.commit()
        flash("Ruta actualizada con éxito.", "success")
    except Exception as e:
        flash(f"Error al actualizar el vehículo: {str(e)}", "error")
    return redirect(url_for('rutas_activas'))


@app.route('/eliminar_ruta/', methods=['GET','POST'])
def eliminar_rutas():
    db, cursor = get_db()
    try:
        id_ruta = request.form['ruta']
        cursor.execute("DELETE FROM rutas WHERE id_ruta= %s", (id_ruta,))
        db.commit()
        flash("Ruta eliminado correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar Rutao: {str(e)}", "error")
    return redirect(url_for('rutas_activas'))


@app.route('/reservas_realizadas', methods=['GET', 'POST'])
def reservas_realizadas():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    
    db, cursor = get_db()
    search_term = request.form.get('search', '').strip() if request.method == 'POST' else ''
    base_query = "SELECT * FROM reservas"
    params = []
    
    if search_term:
        search_query = """
            WHERE estado LIKE %s
        """
        like_pattern = f"%{search_term}%"
        params = [like_pattern] * 1
        base_query += search_query

    cursor.execute(base_query, params)
    lista_reservas = cursor.fetchall()
    usuario = {'primer_N': session.get('primer_N', 'Usuario')}
    return render_template('reservas_realizadas.html', usuario=usuario, reservas=lista_reservas)


@app.route('/editar_reserva/<int:id>')
def editar_reserva(id):
    db, cursor = get_db()
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
    }
    cursor.execute("SELECT * FROM reservas WHERE id_reserva = %s", (id,))
    reservas = cursor.fetchone()
    if not reservas:
        flash("Reserva no encontrada.", "error")
        return redirect(url_for('reservas_realizadas'))
    cursor.execute("SELECT id_vehiculo, placa FROM vehiculos")
    vehiculos = cursor.fetchall()
    db.close()  
    return render_template('editar_reserva.html', usuario=usuario, reservas=reservas, vehiculos=vehiculos)


@app.route('/actualizar_reserva', methods=['POST'])
def actualizar_reserva():
    db, cursor = get_db()
    try:
        id_reserva = request.form.get('id_reserva')
        nombre_completo = request.form.get('Nombre_completo') 
        cedula = request.form.get('cedula')
        celular = request.form.get('celular')
        origen = request.form.get('origen')
        destino = request.form.get('destino')
        hora_salida = request.form.get('hora_salida')
        am_pm = request.form.get('am_pm')
        tipo_vehiculo = request.form.get('tipo_vehiculo')
        cant_pasajeros = request.form.get('cant_pasajeros')
        placa = request.form.get('placa')  
        precio = request.form.get('precio')
        estado = request.form.get('estado')
        cursor.execute("SELECT placa FROM vehiculos WHERE placa = %s", (placa,))
        if not cursor.fetchone():
            flash("El vehículo seleccionado no es válido.", "danger")
            return redirect(url_for('editar_reserva', id=id_reserva))
        cursor.execute("""
            UPDATE reservas
            SET nombre_completo = %s, cedula = %s, celular = %s, origen = %s, destino = %s, 
                hora_salida = %s, am_pm = %s, tipo_vehiculo = %s, cant_pasajeros = %s, 
                placa = %s, precio = %s, estado = %s
            WHERE id_reserva = %s
        """, (
            nombre_completo, cedula, celular, origen, destino,
            hora_salida, am_pm, tipo_vehiculo, cant_pasajeros,
            placa, precio, estado, id_reserva
        ))
        db.commit()
        flash("Reserva actualizada con éxito.", "success")
    except Exception as e:
        flash(f"Error al actualizar la reserva: {str(e)}", "danger")
    finally:
        db.close()
    return redirect(url_for('reservas_realizadas'))



@app.route('/eliminar_reserva', methods=['POST'])
def eliminar_reserva():
    db, cursor = get_db()
    try:
        id_reserva = request.form['id_reserva']
        cursor.execute("DELETE FROM reservas WHERE id_reserva = %s", (id_reserva,))
        db.commit()
        flash("Reserva eliminada correctamente.", "success")
    except Exception as e:
        flash(f"Error al eliminar reserva: {str(e)}", "error")
    return redirect(url_for('conductoras_realizadas'))


@app.route('/mis_reservas', methods=['GET', 'POST'])
def mis_reservas():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    db, cursor = get_db()
    try:
        cursor.execute("SELECT cedula FROM usuarios WHERE email = %s", (session['email'],))
        usuario = cursor.fetchone()
        if not usuario:
            flash("Usuario no encontrado.", "error")
            return redirect(url_for('login'))
        cedula = usuario['cedula']
        cursor.execute("""
            SELECT id_reserva, Nombre_completo, cedula, celular, origen, destino, hora_salida, 
            am_pm, tipo_vehiculo, cant_pasajeros, placa, precio, estado
            FROM reservas
            WHERE cedula = %s
            ORDER BY id_reserva DESC
        """, (cedula,))
        reservas = cursor.fetchall()
        usuario_data = {
            'primer_N': session.get('primer_N', 'Usuario'),
            'primer_A': session.get('primer_A', '')
        }
        return render_template('mis_reservas.html', usuario=usuario_data, reservas=reservas)
    finally:
        cursor.close()
        db.close()




@app.route('/vehiculos_usables')
def vehiculos_usables():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('vehiculos_usables.html', usuario=usuario)


@app.route('/rutas_a_elegir')
def rutas_a_elegir():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('rutas_a_elegir.html', usuario=usuario)


@app.route('/reservas_a_realizar', methods=['GET','POST'])
def reservas_a_realizar():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', ''),
        'cedula': session.get('cedula')
    }
    if request.method == 'POST':
        Nombre_completo = request.form.get('Nombre_completo')
        cedula = request.form.get('cedula')
        celular = request.form.get('celular')
        origen = request.form.get('origen')
        destino = request.form.get('destino')
        fecha_salida= request.form.get('fecha_salida')
        hora_salida = request.form.get('hora_salida')
        fecha_salida = request.form.get('fecha_salida')
        am_pm = request.form.get('am_pm')
        tipo_vehiculo = request.form.get('tipo_vehiculo')
        cant_pasajeros = request.form.get('cant_pasajeros')
        try:
            if celular.startswith('0'):
                celular = '+57' + celular[1:]
            elif not celular.startswith('+57'):
                celular = '+57' + celular
        except Exception as e:
            flash(f"Error al formatear el número de celular: {str(e)}", "error")
            return render_template('reservas_a_realizar.html', usuario=usuario)
        db, cursor = get_db()
        try:
            cursor.execute(
            "INSERT INTO reservas (Nombre_completo, cedula, celular, origen, destino, fecha_salida, hora_salida, am_pm, tipo_vehiculo, cant_pasajeros) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (Nombre_completo, cedula, celular, origen, destino, fecha_salida, hora_salida, am_pm, tipo_vehiculo, cant_pasajeros)
            )
            db.commit()
            flash("Reserva procesada exitosamente.", "success")
        except pymysql.Error as e:
            db.rollback()
            flash(f"Error al procesar la reserva: {str(e)}", "error")
            print(f"Error al insertar datos: {str(e)}")
            return render_template('reservas_a_realizar.html', usuario=usuario)
    return render_template('reservas_a_realizar.html', usuario=usuario)


@app.route('/bucaramanga')
def bucaramanga():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('bucaramanga.html', usuario=usuario)


@app.route('/puerto_wilches')
def puerto_wilches():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('puerto_wilches.html', usuario=usuario)


@app.route('/yondo')
def yondo():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('yondo.html', usuario=usuario)


@app.route('/puerto_parra')
def puerto_parra():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('puerto_parra.html', usuario=usuario)


@app.route('/barranca')
def barranca():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('barranca.html', usuario=usuario)


@app.route('/aeropuerto')
def aeropuerto():
    if 'email' not in session:
        flash("Por favor, inicia sesión para continuar.", "error")
        return redirect(url_for('login'))
    usuario = {
        'primer_N': session.get('primer_N', 'Usuario'),
        'primer_A': session.get('primer_A', '')
    }
    return render_template('aeropuerto.html', usuario=usuario)



@app.errorhandler(404)
def pagina_no_encontrada(error):
    usuario = session.get("usuario")
    tipo_usu= session.get("tipo_usu") 
    return render_template("errores/404.html", usuario=usuario, tipo_usu=tipo_usu), 404


@app.route('/test_404')
def test_404():
    raise NotFound()


if __name__ == '__main__':
    app.run(debug=True)