from flask import Flask,render_template,request,redirect
import sqlite3
import pandas as pd
from sklearn.linear_model import LinearRegression
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
import os
import requests
import threading
import time
from sklearn.cluster import KMeans
from sklearn.tree import DecisionTreeClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
app=Flask(__name__)

@app.route('/')
def accueil():
    return render_template('accueil.html')

@app.route('/formulaire')
def formulaire():
    return render_template('formulaire.html')

@app.route('/donnees',methods=['GET','POST'])
def données():
    if request.method == 'POST':
        # Récupérer les données du formulaire
        region = request.form['region']
        culture = request.form['culture']
        surface= float(request.form['surface'])
        rendement = float(request.form['rendement'])
        obstacle = request.form['obstacle']
        credit = request.form['credit']
        engrais = request.form['engrais']
        transport = request.form['transport']
        perte = float(request.form['perte'])
        revenu = float(request.form['revenu'])

        # Insérer les données dans la base de données
        connexion = sqlite3.connect('agridata.db')
        curseur = connexion.cursor()
        curseur.execute('''
        INSERT INTO agriculteurs (region, culture,surface, rendement, obstacle, credit, engrais, transport, perte, revenu)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (region, culture,surface, rendement, obstacle, credit, engrais, transport, perte, revenu))
        connexion.commit()
        connexion.close()
        return redirect('/')
    connexion = sqlite3.connect('agridata.db')
    curseur = connexion.cursor()
    curseur.execute('SELECT * FROM agriculteurs')
    toutes_donnees = curseur.fetchall()
    connexion.close()
    return render_template('donnees.html', donnees=toutes_donnees)
    
def keep_alive():
    def ping():
        while True:
            try:
                url = os.environ.get(
                    "RENDER_URL")
                requests.get(url,timeout=10)
                print('Ping Reussi')
            except Exception as e:
                print('Ping echoue')
                time.sleep(600)
    t = threading.Thread(target=ping)
    t.daemon = True
    t.start()
				

@app.route('/analyse')
def analyse():
    connexion = sqlite3.connect('agridata.db')
    curseur = connexion.cursor()
    curseur.execute('SELECT * FROM agriculteurs')
    toutes_donnees = curseur.fetchall()
    connexion.close()

    df = pd.DataFrame(toutes_donnees, columns=['id', 'region', 'culture','surface', 'rendement', 'obstacle', 'credit', 'engrais', 'transport', 'perte', 'revenu'])

    stats= {
        'rendement_moyen':  round(df['rendement'].mean(),2),
        'surface_moyenne': round (df['surface'].mean(),2),
        'perte_moyenne': round(df['perte'].mean(),2),
        'revenu_moyen': round(df['revenu'].mean(),2),
    
        'max_rendement':  round(df['rendement'].max(),2),
        'min_rendement':  round(df['rendement'].min(),2),
        'max_revenu':  round(df['revenu'].max(),2),
        'min_revenu':  round(df['revenu'].min(),2),
    }
    X = df[['surface']]
    Y = df['rendement']

    modele = LinearRegression()
    modele.fit(X, Y)
    regression = {
        'coefficient': round(modele.coef_[0], 2),
        'intercept': round(modele.intercept_, 2),
        'score': round(modele.score(X, Y), 2)
    }

    df['engrais_num'] = df['engrais'].map({'Oui': 1, 'Non': 0})

    X_multiple = df[['surface', 'perte', 'engrais_num']]
    Y_multiple = df['rendement']

    modele_multiple = LinearRegression()
    modele_multiple.fit(X_multiple, Y_multiple)

    regression_multiple = {
        'score': round(modele_multiple.score(X_multiple, Y_multiple), 2),
        'coef_surface': round(modele_multiple.coef_[0], 2),
        'coef_perte': round(modele_multiple.coef_[1], 2),
        'coef_engrais': round(modele_multiple.coef_[2], 2),
    }
    
    plt.figure(figsize=(8, 5))
    plt.scatter(df['surface'], df['rendement'], color='green', label='Données réelles')
    plt.plot(df['surface'], modele.predict(X), color='red', label='Droite de régression')
    plt.xlabel('Surface (ha)')
    plt.ylabel('Rendement (kg/ha)')
    plt.title('Régression linéaire : Surface → Rendement')
    plt.legend()


    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    graphique = base64.b64encode(buffer.getvalue()).decode()
    plt.close()

    X_cluster = df[['surface', 'rendement', 'revenu']]
    kmeans = KMeans(n_clusters=3, random_state=0, n_init=10)
    kmeans.fit(X_cluster)
    df['groupe'] = kmeans.labels_

    groupes = df[['region', 'culture', 'groupe']].to_dict('records')

    

    # Classification supervisée
    df['credit_num'] = df['credit'].map({'Oui': 1, 'Non': 0})

    X_class = df[['surface', 'rendement', 'revenu']]
    Y_class = df['credit_num']

    arbre = DecisionTreeClassifier(random_state=0)
    arbre.fit(X_class, Y_class)

    score_classification = round(arbre.score(X_class, Y_class), 2)

    # Réduction de dimensionnalité
    X_pca = df[['surface', 'rendement', 'revenu', 'perte']]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_pca)

    pca = PCA(n_components=2)
    X_reduit = pca.fit_transform(X_scaled)

    variance = [round(v, 2) for v in pca.explained_variance_ratio_]

    # Histogramme - Rendement par région
    plt.figure(figsize=(8, 5))
    df.groupby('region')['rendement'].mean().plot(kind='bar', color='#2d6a4f')
    plt.title('Rendement moyen par région')
    plt.xlabel('Région')
    plt.ylabel('Rendement (kg/ha)')
    plt.xticks(rotation=45)
    plt.tight_layout()
    buffer2 = io.BytesIO()
    plt.savefig(buffer2, format='png')
    buffer2.seek(0)
    histogramme = base64.b64encode(buffer2.getvalue()).decode()
    plt.close()

    # Diagramme circulaire - Répartition des obstacles
    plt.figure(figsize=(7, 7))
    df['obstacle'].value_counts().plot(kind='pie', autopct='%1.1f%%', colors=['#2d6a4f','#f4a90d','#52b788','#ffd166'])
    plt.title('Répartition des obstacles')
    plt.ylabel('')
    buffer3 = io.BytesIO()
    plt.savefig(buffer3, format='png')
    buffer3.seek(0)
    camembert = base64.b64encode(buffer3.getvalue()).decode()
    plt.close()
    return render_template('analyse.html',
    stats=stats,
    regression=regression,
    regression_multiple=regression_multiple,
    graphique=graphique,
    histogramme=histogramme,
    camembert=camembert,
    groupes=groupes,
    variance=variance,
    score_classification=score_classification)
if __name__=="__main__":
    keep_alive()
    app.run (debug='False',host='0.0.0.0',port=3000)
