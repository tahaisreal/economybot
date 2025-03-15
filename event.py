import sqlite3
import random
from discord.ext import commands

class Event(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        db = sqlite3.connect("eco.sqlite")
        cursor = db.cursor()
        
        # Création de la table principale des utilisateurs
        cursor.execute('''CREATE TABLE IF NOT EXISTS eco(
                           user_id INTEGER PRIMARY KEY, 
                           portemonnaie INTEGER, 
                           banque INTEGER,
                           last_daily TEXT,
                           portefeuille TEXT DEFAULT '{}')''')  

        # Vérifier si les colonnes last_daily et portefeuille existent, sinon les ajouter
        cursor.execute("PRAGMA table_info(eco)")
        columns = [col[1] for col in cursor.fetchall()]
        if 'last_daily' not in columns:
            cursor.execute("ALTER TABLE eco ADD COLUMN last_daily TEXT")
        if 'portefeuille' not in columns:
            cursor.execute("ALTER TABLE eco ADD COLUMN portefeuille TEXT DEFAULT '{}'")

        # Créer la table pour les cours des cryptomonnaies
        cursor.execute('''CREATE TABLE IF NOT EXISTS crypto_prices (
                            crypto_name TEXT PRIMARY KEY,
                            price REAL
                          )''')
        cryptos = ["OTH", "ELS", "MST", "CUM", "BTEC"]
        for crypto in cryptos:
            cursor.execute('INSERT OR IGNORE INTO crypto_prices (crypto_name, price) VALUES (?, ?)', (crypto, random.uniform(400, 10000)))


        # Créer la table pour les transactions d'achat de cryptomonnaies
        cursor.execute('''CREATE TABLE IF NOT EXISTS crypto_transactions (
                            user_id INTEGER,
                            crypto_name TEXT,
                            amount REAL,
                            buy_price REAL,
                            FOREIGN KEY(user_id) REFERENCES eco(user_id)
                          )''')

        print("Le bot est en ligne")
        db.commit()
        cursor.close()
        db.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        try:
            author = message.author
            db = sqlite3.connect("eco.sqlite")
            cursor = db.cursor()
            cursor.execute("SELECT user_id FROM eco WHERE user_id = ?", (author.id,))
            result = cursor.fetchone()
            if result is None:
                cursor.execute("INSERT INTO eco(user_id, portemonnaie, banque, last_daily, portefeuille) VALUES(?, ?, ?, ?, ?)", 
                               (author.id, 100, 0, None, '{}'))
                print(f"Utilisateur {author.id} ajouté à la base de données.")
            else:
                print(f"Utilisateur {author.id} déjà présent dans la base de données.")

            db.commit()
            cursor.close()
            db.close()
        except Exception as e:
            print(f"Erreur lors de l'accès à la base de données : {e}")

def setup(bot):
    bot.add_cog(Event(bot))