from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from flask_cors import CORS
import psycopg2
from requests_oauthlib import OAuth1Session

app = Flask(__name__)
app.secret_key = 'your_secret_key'
CORS(app)

# PostgreSQL connection
db = psycopg2.connect(
    host="aws-0-eu-north-1.pooler.supabase.com",
    user="postgres.skmiwdszvamupuvpluvm",
    password="Accordapp123!",
    dbname="postgres"
)

# Discogs OAuth credentials
client_key = 'YzMQsyLkAPJZWnSEgHQz'
client_secret = 'aNfbZhxjxvQMFHGGAHIoYmbTiwioqbGM'
access_token = 'eFTqUCPqJCcjBBbNDlNCIbStLKzIOMcafPBVYaDm'
access_token_secret = 'ZSgsHMXzuBaaAjKhCPmREXufottKWckyMEadFFnn'

# Discogs-søgning med OAuth
@app.route('/discogs_search', methods=['GET'])
def discogs_search():
    titel = request.args.get('titel')
    kunstner = request.args.get('kunstner')

    auth = OAuth1Session(client_key, client_secret,
                         resource_owner_key=access_token,
                         resource_owner_secret=access_token_secret)

    base_url = 'https://api.discogs.com/database/search'
    params = {
        'q': titel if titel else kunstner,
        'type': 'release',
        'format': 'vinyl'
    }

    response = auth.get(base_url, params=params)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({'error': 'Fejl ved forespørgsel til Discogs'}), response.status_code

# Autocomplete function
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')

    sql = """
    SELECT Titel, Kunstner, Type, Genre, Udgivelsesaar, Label
    FROM Produkt
    WHERE Titel LIKE %s OR Kunstner LIKE %s OR Genre LIKE %s OR Label LIKE %s
    """

    cursor = db.cursor()
    cursor.execute(sql, ('%' + query + '%', '%' + query + '%', '%' + query + '%', '%' + query + '%'))
    results = cursor.fetchall()
    cursor.close()

    formatted_results = []
    for row in results:
        formatted_results.append({
            "Titel": row[0],
            "Kunstner": row[1],
            "Type": row[2],
            "Genre": row[3],
            "Udgivelsesaar": row[4],
            "Label": row[5]
        })

    return jsonify(formatted_results)

@app.route('/forespoergsel', methods=['GET', 'POST'])
def forespoergsel():
    if request.method == 'POST':
        data = request.json
        kunde_navn = data.get('KundeNavn')
        email = data.get('Email')
        besked = data.get('Besked')
        albums = data.get('Albums', [])

        cursor = db.cursor()

        for album in albums:
            titel = album['titel']
            kunstner = album['kunstner']
            type = album['type']
            genre = album['genre']
            udgivelsesaar = album['udgivelsesaar']

            sql = """
            INSERT INTO Forespørgsler (Titel, Kunstner, Type, Genre, Udgivelsesaar, KundeNavn, Email, Besked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            values = (titel, kunstner, type, genre, udgivelsesaar, kunde_navn, email, besked)
            cursor.execute(sql, values)

        db.commit()
        cursor.close()

        return jsonify({"message": "Salgsforespørgsel indsendt og albums gemt!"}), 201

    return render_template('forespoergsel.html')

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    section = request.args.get('section', 'forespørgsler')
    sort_by = request.args.get('sort_by', 'Dato')
    sort_order = request.args.get('sort_order', 'ASC')

    new_sort_order = 'DESC' if sort_order == 'ASC' else 'ASC'

    cursor = db.cursor()

    if section == 'forespørgsler':
        query = f"""
            SELECT Titel, Kunstner, Type, Genre, Udgivelsesaar, KundeNavn, Email, Besked, Dato
            FROM Forespørgsler
            ORDER BY {sort_by} {sort_order}
        """
        cursor.execute(query)
        inquiries = cursor.fetchall()
        cursor.close()

        return render_template('admin_dashboard.html', inquiries=inquiries, wishlists=[], section='forespørgsler', new_sort_order=new_sort_order, current_sort_by=sort_by)

    elif section == 'ønskelister':
        query = f"""
            SELECT Titel, Kunstner, Type, Genre, Udgivelsesaar, KundeNavn, Email, Besked, Dato
            FROM Wishlist
            ORDER BY {sort_by} {sort_order}
        """
        cursor.execute(query)
        wishlists = cursor.fetchall()
        cursor.close()

        return render_template('admin_dashboard.html', inquiries=[], wishlists=wishlists, section='ønskelister', new_sort_order=new_sort_order, current_sort_by=sort_by)

    return render_template('admin_dashboard.html', inquiries=[], wishlists=[], section='forespørgsler', new_sort_order=new_sort_order, current_sort_by=sort_by)

# rute til ønskelisten/købsforespørgselsformular
@app.route('/wishlist', methods=['GET', 'POST'])
def wishlist():
    if request.method == 'GET':
        return render_template('oenskeliste.html')

    if request.method == 'POST':
        try:
            data = request.get_json()

            if not data or 'Albums' not in data:
                return jsonify({"error": "Ingen albums modtaget eller forkert format"}), 400

            cursor = db.cursor()

            for album in data.get('Albums', []):
                titel = album.get('titel')
                kunstner = album.get('kunstner')
                type = album.get('type')
                genre = album.get('genre')
                udgivelsesaar = album.get('udgivelsesaar')
                besked = data.get('Besked', '')
                kunde_navn = data.get('KundeNavn')
                email = data.get('Email')

                if not titel or not kunstner or not kunde_navn or not email:
                    return jsonify({"error": "Et eller flere felter er tomme"}), 400

                sql_insert_wishlist = """
                INSERT INTO Wishlist (Titel, Kunstner, Type, Genre, Udgivelsesaar, Besked, KundeNavn, Email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert_wishlist, (titel, kunstner, type, genre, udgivelsesaar, besked, kunde_navn, email))

            db.commit()
            cursor.close()

            return jsonify({"message": "Ønskeliste sendt!"}), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500

# Admin login
admin_username = 'accord_admin'
admin_password = 'admin1234'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == admin_username and password == admin_password:
            session['admin'] = username
            return redirect(url_for('admin_dashboard'))
        else:
            return "Login mislykkedes, prøv igen."

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('admin', None)
    return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/old-form')
def oldForm():
    return render_template('old-form.html')

if __name__ == '__main__':
    app.run(debug=True)
