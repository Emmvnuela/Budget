from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from config import secret_key

app = Flask(__name__)
app.secret_key = secret_key  # Clé secrète nécessaire pour utiliser flash

# Fonction pour établir la connexion à la base de données MySQL de WAMP
def get_db_connection():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="budget"
    )
    conn.autocommit = True
    return conn

# Fonction pour vérifier si l'utilisateur est connecté
def is_logged_in():
    return 'user_id' in session

# Fonction pour récupérer les dernières dépenses de la base de données
def get_last_expenses(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT montant_produit, nom_categorie FROM depenses WHERE utilisateur_id = %s ORDER BY date DESC LIMIT 5', (user_id,))
    dernieres_depenses = cursor.fetchall()
    conn.close()
    return dernieres_depenses

# Fonction pour récupérer les derniers revenus de la base de données
def get_last_incomes(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT montant_revenu, source_revenu FROM revenus WHERE utilisateur_id = %s ORDER BY date DESC LIMIT 5', (user_id,))
    derniers_revenus = cursor.fetchall()
    conn.close()
    return derniers_revenus

# Fonction pour récupérer le solde actuel de la base de données
def get_current_balance(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(montant_revenu) FROM revenus WHERE utilisateur_id = %s', (user_id,))
    total_revenus = cursor.fetchone()[0] or 0
    cursor.execute('SELECT SUM(montant_produit) FROM depenses WHERE utilisateur_id = %s', (user_id,))
    total_depenses = cursor.fetchone()[0] or 0
    conn.close()
    solde = total_revenus - total_depenses
    return solde

# Fonction pour récupérer la liste des catégories spécifiques à l'utilisateur connecté
def get_categories_from_db():
    if not is_logged_in():
        return []

    utilisateur_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM categories WHERE utilisateur_id = %s', (utilisateur_id,))
    categories = cursor.fetchall()
    conn.close()
    return categories

@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT utilisateur_id FROM utilisateurs WHERE email = %s AND mot_de_passe = %s', (email, mot_de_passe))
        utilisateur = cursor.fetchone()
        utilisateur_id = utilisateur[0] if utilisateur else None  # Définir utilisateur_id à partir de la valeur récupérée
        conn.close()
        
        if utilisateur_id:
            session['user_id'] = utilisateur_id
            flash('Connexion réussie !', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Identifiants incorrects. Veuillez réessayer.', 'error')

    return render_template('connexion.html')

@app.route('/inscription', methods=['GET', 'POST'])
def inscription():
    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM utilisateurs WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Cet email est déjà utilisé. Veuillez en choisir un autre.', 'error')
        else:
            cursor.execute('INSERT INTO utilisateurs (nom, email, mot_de_passe) VALUES (%s, %s, %s)', (nom, email, mot_de_passe))
            flash('Nouvel utilisateur enregistré avec succès !', 'success')
        
        conn.close()
        return redirect(url_for('connexion'))

    return render_template('inscription.html')

@app.route('/')
def home():
    return render_template('accueil.html')

@app.route('/dashboard')
def dashboard():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))
    
    user_id = session['user_id']
    dernieres_depenses = get_last_expenses(user_id)
    derniers_revenus = get_last_incomes(user_id)
    solde = get_current_balance(user_id)
    return render_template('dashboard.html', dernieres_depenses=dernieres_depenses, derniers_revenus=derniers_revenus, solde=solde)

@app.route('/enregistrement', methods=['GET', 'POST'])
def enregistrement():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        montant_produit = request.form.get('montant_produit')
        categorie = request.form.get('categorie')
        date = request.form.get('date')
        
        if not montant_produit or not categorie or not date:
            flash('Tous les champs sont obligatoires.', 'error')
            return redirect(url_for('enregistrement'))
        
        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO depenses (montant_produit, nom_categorie, date, utilisateur_id) VALUES (%s, %s, %s, %s)', (montant_produit, categorie, date, user_id))
            conn.commit()
            flash('Transaction enregistrée avec succès !', 'success')
        except Exception as e:
            conn.rollback()
            flash('Une erreur est survenue lors de l\'enregistrement de la transaction.', 'error')
            print(f"Erreur: {e}")
        finally:
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template('enregistrement.html')

@app.route('/categories', methods=['GET', 'POST'])
def categories():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        nouvelle_categorie = request.form['nouvelle_categorie']
        utilisateur_id = session['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO categories (nom_categorie, utilisateur_id) VALUES (%s, %s)', (nouvelle_categorie, utilisateur_id))
        conn.close()
        
        flash('Catégorie ajoutée avec succès !', 'success')
        return redirect(url_for('categories'))

    categories = get_categories_from_db()
    return render_template('categories.html', categories=categories)

@app.route('/budgets', methods=['GET', 'POST'])
def budgets():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        category_id = request.form.get('category')  # Récupère l'ID de la catégorie
        montant_budget = request.form.get('montant_budget')

        if not category_id or not montant_budget:
            flash('Tous les champs doivent être remplis.', 'error')
            return redirect(url_for('budgets'))

        try:
            montant_budget = float(montant_budget)  # Convertir en float pour assurer le type correct
        except ValueError:
            flash('Le montant du budget doit être un nombre.', 'error')
            return redirect(url_for('budgets'))

        conn = get_db_connection()
        if conn is None:
            flash('Erreur de connexion à la base de données.', 'error')
            print('Impossible de se connecter à la base de données.')
            return redirect(url_for('budgets'))

        try:
            cursor = conn.cursor()
            utilisateur_id = session['user_id']  # Récupère l'ID de l'utilisateur depuis la session

            # Vérifie si la catégorie existe dans la base de données
            cursor.execute('SELECT id FROM categories WHERE id = %s AND utilisateur_id = %s', (category_id, utilisateur_id))
            result = cursor.fetchone()

            if not result:
                flash('La catégorie sélectionnée est invalide.', 'error')
                return redirect(url_for('budgets')) 

            # Si la catégorie existe, récupérer son id
            category_id = result[0] 

            print(f"Insertion des valeurs: utilisateur_id={utilisateur_id}, categorie_id={category_id}, montant_budget={montant_budget}")

            # Insérer dans la table budget
            cursor.execute(
                'INSERT INTO budgets (utilisateur_id, id, montant_budget) VALUES (%s, %s, %s)',
                (utilisateur_id, category_id, montant_budget)
            )
            conn.commit()
            flash('Budget ajouté avec succès.', 'success')
            return redirect(url_for('budgets'))
        except Exception as e:
            flash('Une erreur est survenue lors de l\'ajout du budget.', 'error')
            print(f"Erreur: {e}")
            return redirect(url_for('budgets'))
        finally:
            cursor.close()
            conn.close()

    categories = get_categories_from_db()
    return render_template('budgets.html', categories=categories)




@app.route('/parametres', methods=['GET', 'POST'])
def parametres():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        nom = request.form['nom']
        email = request.form['email']
        mot_de_passe = request.form['mot_de_passe']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM utilisateurs WHERE email = %s', (email,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            flash('Cet email est déjà utilisé. Veuillez en choisir un autre.', 'error')
        else:
            cursor.execute('INSERT INTO utilisateurs (nom, email, mot_de_passe) VALUES (%s, %s, %s)', (nom, email, mot_de_passe))
            flash('Nouvel utilisateur enregistré avec succès !', 'success')
        
        conn.close()
        return redirect(url_for('parametres'))

    return render_template('parametres.html')



@app.route('/revenus', methods=['GET', 'POST'])
def ajouter_revenu():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))

    if request.method == 'POST':
        source_revenu = request.form['source_revenu']
        montant_revenu = request.form['montant_revenu']
        date = request.form['date']

        if not source_revenu or not montant_revenu or not date:
            flash('Tous les champs sont obligatoires.', 'error')
            return redirect(url_for('revenus'))

        user_id = session['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('INSERT INTO revenus (source_revenu, montant_revenu, date, utilisateur_id) VALUES (%s, %s, %s, %s)', (source_revenu, montant_revenu, date, user_id))
            conn.commit()
            flash('Revenu ajouté avec succès !', 'success')
        except Exception as e:
            conn.rollback()
            flash('Une erreur est survenue lors de l\'ajout du revenu.', 'error')
            print(f"Erreur: {e}")
        finally:
            conn.close()

        return redirect(url_for('dashboard'))

    return render_template('revenus.html')



@app.route('/visualisation')
def visualisation():
    if not is_logged_in():
        flash('Veuillez vous connecter pour accéder à cette page.', 'error')
        return redirect(url_for('connexion'))

    

    return render_template('visualisation.html' )



@app.route('/deconnexion')
def deconnexion():
    session.pop('user_id', None)
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('connexion'))

if __name__ == '__main__':
    app.run(debug=True)