import sqlite3
def creer_base():
    connexion = sqlite3.connect('agridata.db')
    curseur = connexion.cursor()

    curseur.execute('''
        CREATE TABLE IF NOT EXISTS agriculteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region TEXT,
            culture TEXT,
            surface REAL,
            rendement REAL,
            obstacle TEXT, 
            credit TEXT, 
            engrais TEXT,
            transport TEXT,
            perte REAL, 
            revenu REAL 
        )  
    ''')
    connexion.commit()
    connexion.close()
creer_base()