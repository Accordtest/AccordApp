from flask import Flask, jsonify, request, render_template, redirect, url_for, session, flash
from flask_cors import CORS
import mysql.connector
from requests_oauthlib import OAuth1Session

# app = Flask(__name__, template_folder='C:/Users/TRM/OneDrive - Københavns Erhvervsakademi/Skrivebord/accord_frontend/templates')
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Nødvendig for session-håndtering
CORS(app) # Aktivér CORS for hele applikationen

# Opret forbindelse til MySQL-databasen
db = mysql.connector.connect(
    host="sql7.freemysqlhosting.net",
    user="sql7736049",
    password="R7DeYpK2SE",
    database="sql7736049"
)

cursor = db.cursor()

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

    # OAuth session med gemte access token
    auth = OAuth1Session(client_key, client_secret,
                         resource_owner_key=access_token,
                         resource_owner_secret=access_token_secret)

    base_url = 'https://api.discogs.com/database/search'
    params = {
        'q': titel if titel else kunstner,  # Søg enten på titel eller kunstner
        'type': 'release',
        'format': 'vinyl'
    }

    response = auth.get(base_url, params=params)

    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({'error': 'Fejl ved forespørgsel til Discogs'}), response.status_code


# Autocomplete funktion
@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('query', '')
    sql = """
    SELECT Titel, Kunstner, Type, Genre, Udgivelsesaar, Label
    FROM Produkt
    WHERE Titel LIKE %s OR Kunstner LIKE %s OR Genre LIKE %s OR Label LIKE %s
    """
    cursor.execute(sql, ('%' + query + '%', '%' + query + '%', '%' + query + '%', '%' + query + '%'))
    results = cursor.fetchall()

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
        # Behandling af POST-forespørgsel (form indsendelse)
        data = request.json
        kunde_navn = data.get('KundeNavn')  # Hent kundenavn fra indsendte data
        email = data.get('Email')  # Hent email fra indsendte data
        besked = data.get('Besked')  # Hent besked fra indsendte data
        albums = data.get('Albums', [])  # Hent liste af albums fra indsendte data

        # Gennemgå alle albums og indsæt dem i databasen
        for album in albums:
            titel = album['titel']
            kunstner = album['kunstner']
            type = album['type']
            genre = album['genre']
            udgivelsesaar = album['udgivelsesaar']

            # SQL-query til at indsætte data i SQL-databasen
            sql = """
            INSERT INTO Forespørgsler (Titel, Kunstner, Type, Genre, Udgivelsesaar, KundeNavn, Email, Besked)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            # Sæt værdierne ind i SQL-query
            values = (titel, kunstner, type, genre, udgivelsesaar, kunde_navn, email, besked)
            cursor.execute(sql, values)
            db.commit()  # Gem ændringerne i databasen

        # Returner en JSON-besked, når forespørgslen er gemt
        return jsonify({"message": "Salgsforespørgsel indsendt og albums gemt!"}), 201

    # Hvis det er en GET-anmodning, vis forespørgselsformularen
    return render_template('forespoergsel.html')

@app.route('/admin', methods=['GET'])
def admin_dashboard():
    if 'admin' not in session:
        return redirect(url_for('login'))

    # Hent sektion, sorteringskolonne og sorteringsorden fra URL-parametre
    section = request.args.get('section', 'forespørgsler')  # Standard er at vise forespørgsler
    sort_by = request.args.get('sort_by', 'Dato')  # Standard er at sortere efter Dato
    sort_order = request.args.get('sort_order', 'ASC')  # Standard er stigende orden (ASC)

    # Send den modsatte sorteringsorden til frontend, så den skifter ved næste klik
    new_sort_order = 'DESC' if sort_order == 'ASC' else 'ASC'

    # Hent data baseret på den valgte sektion (forespørgsler eller ønskelister)
    if section == 'forespørgsler':
        query = f"""
            SELECT Titel, Kunstner, Type, Genre, Udgivelsesaar, KundeNavn, Email, Besked, Dato
            FROM Forespørgsler
            ORDER BY {sort_by} {sort_order}
        """
        cursor.execute(query)
        inquiries = cursor.fetchall()
        return render_template('admin_dashboard.html', inquiries=inquiries, wishlists=[], section='forespørgsler', new_sort_order=new_sort_order, current_sort_by=sort_by)

    elif section == 'ønskelister':
        query = f"""
            SELECT Titel, Kunstner, Type, Genre, Udgivelsesaar, KundeNavn, Email, Besked, Dato
            FROM Wishlist
            ORDER BY {sort_by} {sort_order}
        """
        cursor.execute(query)
        wishlists = cursor.fetchall()
        return render_template('admin_dashboard.html', inquiries=[], wishlists=wishlists, section='ønskelister', new_sort_order=new_sort_order, current_sort_by=sort_by)

    # Hvis ingen af dem er valgt, vis en tom forespørgsler-sektion som standard
    return render_template('admin_dashboard.html', inquiries=[], wishlists=[], section='forespørgsler', new_sort_order=new_sort_order, current_sort_by=sort_by)

# rute til ønskelisten/købsforespørgselsformular
@app.route('/wishlist', methods=['GET', 'POST'])
def wishlist():
    if request.method == 'GET':
        # Returner HTML-siden for at oprette ønskelisten
        return render_template('oenskeliste.html')
    
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Debugging: Udskriv modtagne data
            print("Modtaget data:", data)

            # Tjek om data er modtaget korrekt
            if not data or 'Albums' not in data:
                return jsonify({"error": "Ingen albums modtaget eller forkert format"}), 400

            # Loop igennem alle albums i ønskelisten
            for album in data.get('Albums', []):
                titel = album.get('titel')
                kunstner = album.get('kunstner') 
                type = album.get('type')
                genre = album.get('genre')
                udgivelsesaar = album.get('udgivelsesaar')
                besked = data.get('Besked', '')  # Valgfri besked
                kunde_navn = data.get('KundeNavn')
                email = data.get('Email')

                # Debugging: Udskriv albumdata
                print(f"Titel: {titel}, Kunstner: {kunstner}, Type: {type}, Genre: {genre}, Udgivelsesår: {udgivelsesaar}, Kunde: {kunde_navn}, Email: {email}")

                # Tjek om de krævede felter er tomme
                if not titel or not kunstner or not kunde_navn or not email:
                    return jsonify({"error": "Et eller flere felter er tomme"}), 400

                # Indsæt data i databasen
                sql_insert_wishlist = """
                INSERT INTO Wishlist (Titel, Kunstner, Type, Genre, Udgivelsesaar, Besked, KundeNavn, Email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql_insert_wishlist, (titel, kunstner, type, genre, udgivelsesaar, besked, kunde_navn, email))
                db.commit()

            return jsonify({"message": "Ønskeliste sendt!"}), 201

        except Exception as e:
            print(f"Fejl: {e}")
            return jsonify({"error": str(e)}), 500

# Admin login
admin_username = 'accord_admin'
admin_password = 'admin1234'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print("POST forespørgsel modtaget i login-ruten")
        username = request.form['username']
        password = request.form['password']
        
        # Debug: udskriv loginoplysninger
        print(f"Indtastet brugernavn: {username}, Indtastet adgangskode: {password}")
        
        if username == admin_username and password == admin_password:
            session['admin'] = username  # Opret admin-session
            print("Login succesfuldt, omdirigerer til admin-dashboard")
            return redirect(url_for('admin_dashboard'))  # Omdirigér til admin-dashboard
        else:
            print("Login mislykkedes")
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
