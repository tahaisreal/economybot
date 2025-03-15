import discord
import asyncio
from discord.ext import commands
import sqlite3
import random
from event import Event
from datetime import datetime, timedelta
from discord import app_commands
import threading
import time
import json
from discord.ext import commands, tasks



crypto_prices_history = {}
permanent_message = None


crypto_trends = {
    "OTH": random.uniform(-0.01, 0.01),
    "ELS": random.uniform(-0.01, 0.01),
    "MST": random.uniform(-0.01, 0.01),
    "CUM": random.uniform(-0.01, 0.01),
    "BTEC": random.uniform(-0.01, 0.01),
}

async def update_crypto_prices():
    while True:
        await asyncio.sleep(300)  # Attendre 5 minutes
        try:
            db = sqlite3.connect("eco.sqlite")
            cursor = db.cursor()
            cursor.execute("SELECT * FROM crypto_prices")
            cryptos = cursor.fetchall()
            for crypto in cryptos:
                crypto_name = crypto[0]
                old_price = crypto[1]

                # Facteur de volatilité quotidien
                daily_volatility = random.uniform(-0.02, 0.02)

                # Facteur de tendance à long terme
                long_term_trend = crypto_trends[crypto_name]

                # Facteur d'événement aléatoire majeur
                if random.random() > 0.95:  # 5% de chances qu'un événement majeur se produise
                    major_event = random.uniform(-0.5, 0.5)
                else:
                    major_event = 0

                # Calcul du nouveau prix
                new_price = old_price * (1 + daily_volatility + long_term_trend + major_event)
                new_price = max(0, new_price)  # S'assurer que le prix ne soit pas négatif

                # Mettre à jour l'historique des prix
                crypto_prices_history[crypto_name] = old_price 

                # Mettre à jour le prix dans la base de données
                cursor.execute("UPDATE crypto_prices SET price = ? WHERE crypto_name = ?", (new_price, crypto_name))
            
            db.commit()
            cursor.close()
            db.close()
            
            await update_permanent_crypto_prices_message()
        except Exception as e:
            print(f"Erreur lors de la mise à jour des prix des cryptomonnaies : {e}")

async def update_permanent_crypto_prices_message():
    global permanent_message_id, permanent_message_channel_id
    if permanent_message_id and permanent_message_channel_id:
        try:
            channel = bot.get_channel(permanent_message_channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(permanent_message_id)
                    await message.delete()
                except discord.NotFound:
                    print("Le message permanent à supprimer n'a pas été trouvé.")
        except Exception as e:
            print(f"Erreur lors de la suppression du message permanent : {e}")

    try:
        db = sqlite3.connect("eco.sqlite")
        cursor = db.cursor()
        cursor.execute("SELECT * FROM crypto_prices")
        prices = cursor.fetchall()
        embed = discord.Embed(title="Cours des Cryptomonnaies", color=discord.Color.blue())
        for crypto, price in prices:
            old_price = crypto_prices_history.get(crypto, price)
            emoji = "📈" if price > old_price else "📉"
            embed.add_field(name=crypto, value=f"{price:.2f} dhs {emoji}", inline=False)
        new_message = await channel.send(embed=embed)
        permanent_message_id = new_message.id
        permanent_message_channel_id = new_message.channel.id
        cursor.close()
        db.close()
    except Exception as e:
        print(f"Erreur lors de l'envoi du message permanent : {e}")

class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.add_cog(Event(self))
        self.tree.copy_global_to(guild=discord.Object(id=558586798423670804))  # Remplacez YOUR_GUILD_ID par l'ID de votre serveur
        await self.tree.sync()
        self.loop.create_task(update_crypto_prices())

bot = MyBot()



@bot.tree.command(name="permanent_crypto_prices", description="Afficher le cours des cryptomonnaies de façon permanente")
async def permanent_crypto_prices(interaction: discord.Interaction):
    if interaction.user.id != 558586798423670804:
        await interaction.response.send_message("Vous n'avez pas la permission d'utiliser cette commande.", ephemeral=True)
        return

    global permanent_message_id, permanent_message_channel_id
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM crypto_prices")
    prices = cursor.fetchall()
    embed = discord.Embed(title="Cours des Cryptomonnaies", color=discord.Color.blue())
    for crypto, price in prices:
        old_price = crypto_prices_history.get(crypto, price)
        emoji = "📈" if price > old_price else "📉"
        embed.add_field(name=crypto, value=f"{price:.2f} dhs {emoji}", inline=False)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/10076/10076729.png")
    new_message = await interaction.response.send_message(embed=embed)
    permanent_message_id = (await interaction.original_response()).id
    permanent_message_channel_id = interaction.channel_id
    cursor.close()
    db.close()



@bot.tree.command(name="crypto_prices", description="Voir les cours actuels des cryptomonnaies")
async def crypto_prices(interaction: discord.Interaction):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute("SELECT * FROM crypto_prices")
    prices = cursor.fetchall()
    embed = discord.Embed(title="Cours des Cryptomonnaies", color=discord.Color.blue())
    for crypto, price in prices:
        old_price = crypto_prices_history.get(crypto, price)
        emoji = "📈" if price > old_price else "📉"
        embed.add_field(name=crypto, value=f"{price:.2f} dhs {emoji}", inline=False)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3378/3378138.png")
    await interaction.response.send_message(embed=embed)
    cursor.close()
    db.close()



@bot.tree.command(name="buy_crypto", description="Acheter une cryptomonnaie")
@app_commands.describe(crypto="La cryptomonnaie à acheter", amount="La quantité à acheter")
async def buy_crypto(interaction: discord.Interaction, crypto: str, amount: float):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute("SELECT price FROM crypto_prices WHERE crypto_name = ?", (crypto,))
    price = cursor.fetchone()
    if not price:
        await interaction.response.send_message("Cryptomonnaie invalide.", ephemeral=True)
        return

    cost = price[0] * amount
    cursor.execute("SELECT portemonnaie FROM eco WHERE user_id = ?", (interaction.user.id,))
    portemonnaie = cursor.fetchone()
    if not portemonnaie or portemonnaie[0] < cost:
        await interaction.response.send_message("Fonds insuffisants dans le portemonnaie.", ephemeral=True)
        return

    cursor.execute("SELECT portefeuille FROM eco WHERE user_id = ?", (interaction.user.id,))
    portefeuille = cursor.fetchone()
    portefeuille = eval(portefeuille[0]) if portefeuille else {}
    portefeuille[crypto] = portefeuille.get(crypto, 0) + amount

    cursor.execute("UPDATE eco SET portemonnaie = portemonnaie - ?, portefeuille = ? WHERE user_id = ?", (cost, str(portefeuille), interaction.user.id))
    cursor.execute("INSERT INTO crypto_transactions (user_id, crypto_name, amount, buy_price) VALUES (?, ?, ?, ?)", (interaction.user.id, crypto, amount, price[0]))
    db.commit()
    cursor.close()
    db.close()
    await interaction.response.send_message(f"Acheté {amount} {crypto} pour {cost} dhs.")


# ----- give ------
@bot.tree.command(name="give", description="Donner du dh à un membre")
@app_commands.describe(member="Le membre à qui donner", amount="Le montant à donner")
@app_commands.checks.has_role('taha')
async def give(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != 558586798423670804:
        return await interaction.response.send_message("Vous n'êtes pas autorisé à exécuter cette commande.", ephemeral=True)
    
    if amount < 0:
        return await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    
    cursor.execute("SELECT portemonnaie FROM eco WHERE user_id = ?", (member.id,))
    portemonnaie = cursor.fetchone()
    
    if portemonnaie is None:
        portemonnaie = 0
        cursor.execute("INSERT INTO eco (user_id, portemonnaie, banque) VALUES (?, ?, ?)", (member.id, amount, 0))
    else:
        portemonnaie = portemonnaie[0]
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie + amount, member.id))
    
    db.commit()
    cursor.close()
    db.close()

    await interaction.response.send_message(f"{amount} dh ont été ajoutés au portefeuille de {member.mention}.")
    


# ----- remove ------
@bot.tree.command(name="remove", description="Retirer du dh d'un membre")
@app_commands.describe(member="Le membre à qui retirer", amount="Le montant à retirer")
@app_commands.checks.has_role('taha')
async def remove(interaction: discord.Interaction, member: discord.Member, amount: int):
    if interaction.user.id != 558586798423670804:
        return await interaction.response.send_message("Vous n'êtes pas autorisé à exécuter cette commande.", ephemeral=True)
    
    if amount < 0:
        return await interaction.response.send_message("Le montant doit être positif.", ephemeral=True)

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    
    cursor.execute("SELECT portemonnaie FROM eco WHERE user_id = ?", (member.id,))
    portemonnaie = cursor.fetchone()
    
    if portemonnaie is None:
        return await interaction.response.send_message("L'utilisateur n'a pas de compte.", ephemeral=True)
    
    portemonnaie = portemonnaie[0]
    
    if portemonnaie < amount:
        return await interaction.response.send_message("L'utilisateur n'a pas assez d'argent.", ephemeral=True)

    cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie - amount, member.id))
    
    db.commit()
    cursor.close()
    db.close()

    await interaction.response.send_message(f"{amount} dh ont été retirés du portefeuille de {member.mention}.")



# ---- withdraw crypto ----
@bot.tree.command(name="withdraw_crypto", description="Retirer des fonds du portefeuille de cryptomonnaie vers le portemonnaie")
@app_commands.describe(crypto="La cryptomonnaie à retirer", amount="Le montant à retirer")
async def withdraw_crypto(interaction: discord.Interaction, crypto: str, amount: float):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute("SELECT price FROM crypto_prices WHERE crypto_name = ?", (crypto,))
    price = cursor.fetchone()
    if not price:
        await interaction.response.send_message("Cryptomonnaie invalide.", ephemeral=True)
        return

    cursor.execute("SELECT portefeuille FROM eco WHERE user_id = ?", (interaction.user.id,))
    portefeuille = cursor.fetchone()
    portefeuille = eval(portefeuille[0]) if portefeuille else {}
    if portefeuille.get(crypto, 0) < amount:
        await interaction.response.send_message("Quantité insuffisante dans le portefeuille.", ephemeral=True)
        return

    value = price[0] * amount
    portefeuille[crypto] -= amount
    if portefeuille[crypto] == 0:
        del portefeuille[crypto]

    cursor.execute("UPDATE eco SET portemonnaie = portemonnaie + ?, portefeuille = ? WHERE user_id = ?", (value, str(portefeuille), interaction.user.id))
    db.commit()
    cursor.close()
    db.close()
    await interaction.response.send_message(f"Retiré {amount} unités de {crypto} pour {value} dhs.")



@bot.tree.command(name="portefeuille", description="Voir votre portefeuille de cryptomonnaie")
async def portfolio(interaction: discord.Interaction):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute("SELECT portefeuille FROM eco WHERE user_id = ?", (interaction.user.id,))
    portefeuille = cursor.fetchone()
    portefeuille = eval(portefeuille[0]) if portefeuille else {}
    embed = discord.Embed(title="Votre Portefeuille", color=discord.Color.green())
    for crypto, amount in portefeuille.items():
        cursor.execute("SELECT price FROM crypto_prices WHERE crypto_name = ?", (crypto,))
        current_price = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(buy_price * amount) / SUM(amount) FROM crypto_transactions WHERE user_id = ? AND crypto_name = ?", (interaction.user.id, crypto))
        buy_price = cursor.fetchone()[0]

        value = current_price * amount
        embed.add_field(name=crypto, value=f"🪙 {amount} unités \n :moneybag: **Prix actuel**: {current_price:.2f} 💩 | Achat : {buy_price:.2f} 💩" , inline=False)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/6826/6826311.png")
    await interaction.response.send_message(embed=embed)
    cursor.close()
    db.close()


# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------




# --- balance ---
@bot.tree.command(name="balance", description="Affiche le solde du compte")
@app_commands.describe(member="Le membre dont vous souhaitez voir le solde")
async def balance(interaction: discord.Interaction, member: discord.Member = None):
    if member is None:
        member = interaction.user
    
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    cursor.execute(f'SELECT portemonnaie, banque FROM eco WHERE user_id = {member.id}')
    bal = cursor.fetchone()
    try:
        portemonnaie = bal[0]
        banque = bal[1]
    except:
        portemonnaie = 0
        banque = 0

    embed = discord.Embed(
        title=f"Compte Bancaire de {member.display_name}",
        color=discord.Color.green()
    )
    embed.add_field(name="Portemonnaie", value=f"**`{int(portemonnaie)}`💩**")
    embed.add_field(name="Banque", value=f"**`{int(banque)}`💩**")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2295/2295218.png")
    await interaction.response.send_message(embed=embed)



# --- deposit ---
@bot.tree.command(name="deposit", description="Dépose de l'argent dans la banque")
@app_commands.describe(amount="Le montant à déposer (peut être 'all' pour tout déposer)")
async def deposit(interaction: discord.Interaction, amount: str):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM eco WHERE user_id = {interaction.user.id}")
    data = cursor.fetchone()

    if data is None:
        await interaction.response.send_message("Utilisateur non trouvé dans la base de données.", ephemeral=True)
        db.close()
        return

    portemonnaie, banque = data[1], data[2]

    if amount.lower() == "all":
        amount = portemonnaie
    else:
        try:
            amount = int(amount)
        except ValueError:
            await interaction.response.send_message("Veuillez entrer un montant valide.", ephemeral=True)
            db.close()
            return

    if portemonnaie < amount:
        await interaction.response.send_message("Vous n'avez pas assez d'argent dans votre porte-monnaie.", ephemeral=True)
    else:
        cursor.execute("UPDATE eco SET banque = ? WHERE user_id = ?", (banque + amount, interaction.user.id))
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie - amount, interaction.user.id))
        await interaction.response.send_message(f"💩 Tu as déposé {int(amount)} dh dans la banque")

    db.commit()
    cursor.close()
    db.close()


# --- withdraw ---
@bot.tree.command(name="withdraw", description="Retire de l'argent de la banque")
@app_commands.describe(amount="Le montant à retirer (peut être 'all' pour tout retirer)")
async def withdraw(interaction: discord.Interaction, amount: str):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute(f"SELECT * FROM eco WHERE user_id = {interaction.user.id}")
    data = cursor.fetchone()

    if data is None:
        await interaction.response.send_message("Utilisateur non trouvé dans la base de données.", ephemeral=True)
        db.close()
        return

    portemonnaie, banque = data[1], data[2]

    if amount.lower() == "all":
        amount = banque
    else:
        try:
            amount = int(amount)
        except ValueError:
            await interaction.response.send_message("Veuillez entrer un montant valide.", ephemeral=True)
            db.close()
            return

    if banque < amount:
        await interaction.response.send_message("Vous n'avez pas assez d'argent dans votre banque.", ephemeral=True)
    else:
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie + amount, interaction.user.id))
        cursor.execute("UPDATE eco SET banque = ? WHERE user_id = ?", (banque - amount, interaction.user.id))
        await interaction.response.send_message(f"💩 Tu as retiré {int(amount)} dh de la banque")

    db.commit()
    cursor.close()
    db.close()



# ---- dh ----
@bot.tree.command(name="dh", description="Gagne du dh")
@app_commands.checks.cooldown(10, 86400, key=lambda i: (i.guild_id, i.user.id))
async def dh(interaction: discord.Interaction):
    member = interaction.user
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    earnings = random.randint(1, 20)

    cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {member.id}')
    portemonnaie = cursor.fetchone()
    portemonnaie = portemonnaie[0] if portemonnaie else 0

    cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie + earnings, member.id))
    await interaction.response.send_message(f"Tu as gagné {earnings} dh :coin:")
    
    db.commit()
    cursor.close()
    db.close()
@dh.error
async def dh_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.',
            ephemeral=True
        )



# ----- miner ------
@bot.tree.command(name="miner", description="Mine des toilettes pour gagner du dh")
@app_commands.checks.cooldown(2, 86400, key=lambda i: (i.guild_id, i.user.id))
async def miner(interaction: discord.Interaction):
    member = interaction.user
    mining_duration = 3

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    # Send initial mining message
    await interaction.response.send_message(f"🚽 En train de miner les toilettes... {mining_duration} secondes restantes.")
    mining_message = await interaction.original_response()

    # Simulate mining animation
    for remaining in range(mining_duration, 0, -1):
        await asyncio.sleep(1)
        await mining_message.edit(content=f"🚽 En train de miner les toilettes... {remaining} secondes restantes.")

    # Simulate mining Bitecoin
    mined_bitecoin = round(random.uniform(0.7, 3), 3)
    conversion_rate = 10 
    mined_dh = int(mined_bitecoin * conversion_rate * 10)  

    # Fetch current balance 
    cursor.execute('SELECT portemonnaie FROM eco WHERE user_id = ?', (member.id,))
    result = cursor.fetchone()
    portemonnaie = result[0] if result else 0

    # Update balance with mined dh
    new_balance = portemonnaie + mined_dh
    if result:
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_balance, member.id))
    else:
        cursor.execute("INSERT INTO eco (user_id, portemonnaie) VALUES (?, ?)", (member.id, new_balance))

    # Create an embed
    embed = discord.Embed(title="Minage réussi!", color=discord.Color.green())
    embed.add_field(name="Bitecoin miné", value=f"{int(mined_bitecoin)} Bitecoin(s)", inline=False)
    embed.add_field(name="dh reçu", value=f"{mined_dh} dh :coin:", inline=False)
    embed.add_field(name="Nouveau solde", value=f"{int(new_balance)} dh", inline=False)
    embed.set_footer(text="Continuez à miner pour gagner plus de dh!")

    # Edit the initial message with the mining results
    await mining_message.edit(content=None, embed=embed)

    db.commit()
    cursor.close()
    db.close()
@miner.error
async def miner_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.',
            ephemeral=True
        )



# ----- pari ------
@bot.tree.command(name="pari", description="Faites un pari pour gagner ou perdre du dh")
@app_commands.describe(amount="Le montant à parier")
@app_commands.checks.cooldown(4, 86400, key=lambda i: (i.guild_id, i.user.id))
async def pari(interaction: discord.Interaction, amount: int):
    user = interaction.user
    bot_user = bot.user

    # Vérification de la mise minimum
    if amount < 300:
        await interaction.response.send_message("La mise doit être au moins de 300 dhs.", ephemeral=True)
        return

    if amount <= 0:
        await interaction.response.send_message("La mise doit être un montant positif.", ephemeral=True)
        return

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {user.id}')
    user_balance = cursor.fetchone()
    user_balance = user_balance[0] if user_balance else 0

    if user_balance < amount:
        await interaction.response.send_message("Vous n'avez pas assez de dh pour faire ce pari.", ephemeral=True)
        cursor.close()
        db.close()
        return

    cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {bot_user.id}')
    bot_balance = cursor.fetchone()
    bot_balance = bot_balance[0] if bot_balance else 0

    # Logique du jeu
    user_strikes = int(random.randint(0, 10))
    bot_strikes = int(random.randint(0, 10))

    if user_strikes > bot_strikes:
        percentage = int(random.randint(30, 50))
        amount_won = int(amount * (percentage / 100))
        if user_balance + amount_won > 1000000:
            amount_won = 1000000 - user_balance
        new_user_balance = user_balance + amount_won
        new_bot_balance = bot_balance - amount_won

        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_bot_balance, bot_user.id))

        result_message = f"Vous avez gagné le pari et remporté {int(amount_won)} dh! 🎉"
    elif user_strikes == bot_strikes:
        embed = discord.Embed(title="Résultat du Pari")
        embed.add_field(name="Vous n'avez rien gagné ni rien perdu")
    else:
        amount_lost = int(amount * (int(random.randint(50, 70)) / 100))
        new_user_balance = user_balance - amount_lost
        new_bot_balance = bot_balance + amount_lost

        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_bot_balance, bot_user.id))

        result_message = f"Vous avez perdu le pari et perdu {int(amount_lost)} dh... 😢"

    embed = discord.Embed(title="Résultat du Pari", color=discord.Color.gold())
    embed.add_field(name="Vos Strikes", value=user_strikes, inline=True)
    embed.add_field(name="Strikes du Bot", value=bot_strikes, inline=True)
    embed.add_field(name="Résultat", value=result_message, inline=False)
    embed.add_field(name="Votre Nouveau Solde", value=f"{int(new_user_balance)} dh", inline=False)
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3425/3425925.png")

    await interaction.response.send_message(embed=embed)

    db.commit()
    cursor.close()
    db.close()
@pari.error
async def pari_error(interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.',
            ephemeral=True
        )



# ----- vol ------
@bot.tree.command(name="vol", description="Vole un autre membre")
@app_commands.describe(member="Le membre à voler")
@app_commands.checks.cooldown(2, 86400, key=lambda i: (i.guild_id, i.user.id))
async def vol(interaction: discord.Interaction, member: discord.Member):
    if member == interaction.user:
        await interaction.response.send_message("Tu ne peux pas te voler toi-même.", ephemeral=True)
        return

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    cursor.execute(f"SELECT portemonnaie FROM eco WHERE user_id = {member.id}")
    portemonnaie_victime = cursor.fetchone()
    cursor.execute(f"SELECT portemonnaie FROM eco WHERE user_id = {interaction.user.id}")
    portemonnaie_voleur = cursor.fetchone()

    portemonnaie_victime = portemonnaie_victime[0] if portemonnaie_victime else 0
    portemonnaie_voleur = portemonnaie_voleur[0] if portemonnaie_voleur else 0

    if portemonnaie_victime == 0:
        await interaction.response.send_message(f"{member.display_name} n'a pas d'argent dans son portemonnaie.", ephemeral=True)
        return

    chance = random.uniform(0, 1)
    if chance < 0.4:
        montant_vole = int(portemonnaie_victime * 0.1)
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie_victime - montant_vole, member.id))
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie_voleur + montant_vole, interaction.user.id))
        await interaction.response.send_message(f"🟢 Vol réussi ! Tu as volé {montant_vole} dh de {member.display_name}.")
    else:
        perte = int(portemonnaie_voleur * 0.05)
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie_voleur - perte, interaction.user.id))
        await interaction.response.send_message(f"🔴 Vol échoué ! Tu as perdu {perte} dhs.")

    db.commit()
    cursor.close()
    db.close()
@vol.error
async def vol_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.', ephemeral=True)



# ----- pileouface ------
@bot.tree.command(name="pileouface", description="Pariez sur pile ou face")
@app_commands.describe(mise="Le montant à parier", choix="Votre choix: 'pile' ou 'face'")
@app_commands.checks.cooldown(4, 86400, key=lambda i: (i.guild_id, i.user.id))
async def pileouface(interaction: discord.Interaction, mise: int, choix: str):

    if choix not in ["pile", "face"]:
        await interaction.response.send_message("Choix invalide. Choisis soit 'pile' soit 'face'.", ephemeral=True)
        return

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute(f"SELECT portemonnaie FROM eco WHERE user_id = {interaction.user.id}")
    portemonnaie = cursor.fetchone()
    portemonnaie = portemonnaie[0] if portemonnaie else 0

    if portemonnaie < mise:
        await interaction.response.send_message("Tu n'as pas assez d'argent pour parier cette somme.", ephemeral=True)
        return
    
    if mise < 300:
        await interaction.response.send_message("Il faut avoir au moins 300 dhs pour lancer un pileouface", ephemeral=True)
        return

    resultat = random.choice(["pile", "face"])
    if resultat == choix:
        gain = mise * 2
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie + gain, interaction.user.id))
        await interaction.response.send_message(f"Félicitations ! C'est {resultat}. Tu gagnes {gain} dh.")
    else:
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (portemonnaie - mise, interaction.user.id))
        await interaction.response.send_message(f"Dommage ! C'est {resultat}. Tu perds {mise} dh.")
    
    db.commit()
    cursor.close()
    db.close()
@pileouface.error
async def pileouface(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.', ephemeral=True)


# ---- roulette ----
@bot.tree.command(name="roulette", description="Joue à la roulette des couleurs pour parier du dh")
@app_commands.describe(amount="Montant à parier", opponent="Adversaire (optionnel)")
@app_commands.checks.cooldown(4, 86400, key=lambda i: (i.guild_id, i.user.id))
async def roulette(interaction: discord.Interaction, amount: int, opponent: discord.Member = None):
    user = interaction.user

    if amount <= 0:
        await interaction.response.send_message("La mise doit être un montant positif.", ephemeral=True)
        return

    if amount < 500:
        await interaction.response.send_message("La mise doit être au moins égale à 500",ephemeral=True)
        return

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {user.id}')
    user_balance = cursor.fetchone()
    try:
        user_balance = user_balance[0]
    except:
        user_balance = 0

    if user_balance < amount:
        await interaction.response.send_message("Vous n'avez pas assez de dh pour faire ce pari.", ephemeral=True)
        cursor.close()
        db.close()
        return

    if opponent is None:
        # Single-player mode
        colors = ["🔴", "🟢", "🔵", "🟡", "⚫"]
        winning_color = random.choice(colors)

        embed = discord.Embed(title="Roulette des Couleurs", description="Choisissez une couleur!", color=discord.Color.gold())
        for color in colors:
            embed.add_field(name=f"Couleur {color}", value="", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1055/1055813.png")
        message = await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        for color in colors:
            try:
                await message.add_reaction(color)
            except Exception as e:
                await interaction.followup.send(f"Erreur lors de l'ajout de la réaction {color} : {str(e)}", ephemeral=True)
                cursor.close()
                db.close()
                return

        def check(reaction, user):
            return user == interaction.user and str(reaction.emoji) in colors and reaction.message.id == message.id

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé. Veuillez réessayer.", ephemeral=True)
            cursor.close()
            db.close()
            return

        chosen_color = str(reaction.emoji)

        if chosen_color == winning_color:
            amount_won = amount * 4  # Win 4 times the bet
            new_user_balance = user_balance + amount_won
            result_message = f"Félicitations {user.mention}, vous avez choisi la bonne couleur et gagné {amount_won} dh! 🎉"
        else:
            amount_lost = int((80/100)*amount)
            new_user_balance = user_balance - amount_lost
            result_message = f"Dommage {user.mention}, vous avez perdu {amount_lost} dh... 😢 La couleur gagnante était {winning_color}."

        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))

        embed = discord.Embed(title="Résultat de la Roulette des Couleurs", color=discord.Color.gold())
        embed.add_field(name="Votre Choix", value=chosen_color, inline=True)
        embed.add_field(name="Couleur Gagnante", value=winning_color, inline=True)
        embed.add_field(name="Résultat", value=result_message, inline=False)
        embed.add_field(name="Votre Nouveau Solde", value=f"{int(new_user_balance)} dh", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/1055/1055813.png")

        await interaction.followup.send(embed=embed)
    else:
        # Two-player mode
        cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {opponent.id}')
        opponent_balance = cursor.fetchone()
        try:
            opponent_balance = opponent_balance[0]
        except:
            opponent_balance = 0

        if opponent_balance < amount:
            await interaction.response.send_message(f"{opponent.mention} n'a pas assez de dh pour faire ce pari.", ephemeral=True)
            cursor.close()
            db.close()
            return

        await interaction.response.send_message(f"{opponent.mention}, {interaction.user.mention} vous a défié à une roulette des couleurs pour {amount} dh! Réagissez avec ✅ pour accepter.")
        message = await interaction.original_response()

        try:
            await message.add_reaction("✅")
        except Exception as e:
            await interaction.followup.send(f"Erreur lors de l'ajout de la réaction : {str(e)}", ephemeral=True)
            cursor.close()
            db.close()
            return

        def accept_check(reaction, user):
            return user == opponent and str(reaction.emoji) == "✅" and reaction.message.id == message.id

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=accept_check)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"{opponent.mention} n'a pas accepté le pari à temps.", ephemeral=True)
            cursor.close()
            db.close()
            return

        colors = ["🔴", "🟢", "🔵", "🟡", "⚫"]
        winning_color = random.choice(colors)

        embed = discord.Embed(title="Roulette des Couleurs", description="Choisissez chacun une couleur!", color=discord.Color.gold())

        message = await interaction.followup.send(embed=embed)

        for color in colors:
            try:
                await message.add_reaction(color)
            except Exception as e:
                await interaction.followup.send(f"Erreur lors de l'ajout de la réaction {color} : {str(e)}", ephemeral=True)
                cursor.close()
                db.close()
                return

        def user_check(reaction, user):
            return user == interaction.user and str(reaction.emoji) in colors and reaction.message.id == message.id

        def opponent_check(reaction, user):
            return user == opponent and str(reaction.emoji) in colors and reaction.message.id == message.id

        try:
            user_reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=user_check)
            opponent_reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=opponent_check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé. Veuillez réessayer.", ephemeral=True)
            cursor.close()
            db.close()
            return

        user_chosen_color = str(user_reaction.emoji)
        opponent_chosen_color = str(opponent_reaction.emoji)

        if user_chosen_color == winning_color and opponent_chosen_color != winning_color:
            amount_won = amount * 2
            new_user_balance = user_balance + amount_won
            new_opponent_balance = opponent_balance - amount
            result_message = f"Félicitations {user.mention}, vous avez choisi la bonne couleur et gagné {amount_won} dh! 🎉"
        elif opponent_chosen_color == winning_color and user_chosen_color != winning_color:
            amount_won = amount * 2
            new_user_balance = user_balance - amount
            new_opponent_balance = opponent_balance + amount_won
            result_message = f"Félicitations {opponent.mention}, vous avez choisi la bonne couleur et gagné {amount_won} dh! 🎉"
        else:
            result_message = f"Aucun gagnant. La couleur gagnante était {winning_color}. Réessayez!"

            new_user_balance = user_balance
            new_opponent_balance = opponent_balance

        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_opponent_balance, opponent.id))

        embed = discord.Embed(title="Résultat de la Roulette des Couleurs", color=discord.Color.gold())
        embed.add_field(name=f"Choix de {user.display_name}", value=user_chosen_color, inline=True)
        embed.add_field(name=f"Choix de {opponent.display_name}", value=opponent_chosen_color, inline=True)
        embed.add_field(name="Couleur Gagnante", value=winning_color, inline=True)
        embed.add_field(name="Résultat", value=result_message, inline=False)
        embed.add_field(name=f"Nouveau Solde de {user.display_name}", value=f"{int(new_user_balance)} dh", inline=False)
        embed.add_field(name=f"Nouveau Solde de {opponent.display_name}", value=f"{int(new_opponent_balance)} dh", inline=False)

        await interaction.followup.send(embed=embed)

    db.commit()
    cursor.close()
    db.close()
@roulette.error
async def roulette_erro(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.', ephemeral=True)



# ---- tresor ----
@bot.tree.command(name="tresor", description="Joue à la chasse au trésor pour parier du dh")
@app_commands.describe(amount="Montant à parier", opponent="Adversaire (optionnel)")
@app_commands.checks.cooldown(3, 86400, key=lambda i: (i.guild_id, i.user.id))
async def tresor(interaction: discord.Interaction, amount: int, opponent: discord.Member = None):
    user = interaction.user

    if amount <= 0:
        await interaction.response.send_message("La mise doit être un montant positif.", ephemeral=True)
        return

    if amount < 1000:
        await interaction.response.send_message("La miste doit être au moins égale à 1000")
        return
    
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    # Vérifier le solde de l'utilisateur
    cursor.execute('SELECT portemonnaie FROM eco WHERE user_id = ?', (user.id,))
    user_balance = cursor.fetchone()
    user_balance = user_balance[0] if user_balance else 0

    if user_balance < amount:
        await interaction.response.send_message("Vous n'avez pas assez de dh pour faire ce pari.", ephemeral=True)
        cursor.close()
        db.close()
        return

    if opponent is None:
        # Mode solo
        chest_values = ["grand prix", "petit prix", "rien", "rien"]
        random.shuffle(chest_values)

        embed = discord.Embed(title="Chasse au Trésor", description="Choisissez un coffre au trésor (1-4)!", color=discord.Color.blue())
        embed.add_field(name="Coffre 1", value="❓", inline=True)
        embed.add_field(name="Coffre 2", value="❓", inline=True)
        embed.add_field(name="Coffre 3", value="❓", inline=True)
        embed.add_field(name="Coffre 4", value="❓", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/128/1355/1355900.png")

        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

        for emoji in emojis:
            await message.add_reaction(emoji)

        def check(reaction, user):
            return user == interaction.user and str(reaction.emoji) in emojis and reaction.message.id == message.id

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé. Veuillez réessayer.", ephemeral=True)
            cursor.close()
            db.close()
            return

        chosen_chest = emojis.index(str(reaction.emoji))
        prize = chest_values[chosen_chest]

        if prize == "grand prix":
            amount_won = amount * 2  # Grand prix vaut 5 fois la mise
            new_user_balance = user_balance + amount_won
            result_message = f"{user.mention} a trouvé le grand prix et gagné {amount_won} dh! 🎉"
        elif prize == "petit prix":
            amount_won = amount * 1.25  # Petit prix vaut 2 fois la mise
            new_user_balance = user_balance + amount_won
            result_message = f"{user.mention} a trouvé un petit prix et gagné {amount_won} dh! 🎉"
        else:
            amount_won = 0
            new_user_balance = user_balance - amount
            result_message = f"{user.mention} n'a rien trouvé et perdu {amount} dh... 😢"

        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))

        embed = discord.Embed(title="Chasse au Trésor", color=discord.Color.blue())
        embed.add_field(name=f"Votre Choix: Coffre {chosen_chest + 1}", value=prize, inline=True)
        embed.add_field(name="Résultat", value=result_message, inline=False)
        embed.add_field(name="Votre Nouveau Solde", value=f"{int(new_user_balance)} dh", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/128/1355/1355900.png")

        await interaction.followup.send(embed=embed)
    else:
        # Mode duo
        cursor.execute('SELECT portemonnaie FROM eco WHERE user_id = ?', (opponent.id,))
        opponent_balance = cursor.fetchone()
        opponent_balance = opponent_balance[0] if opponent_balance else 0

        if opponent_balance < amount:
            await interaction.response.send_message(f"{opponent.mention} n'a pas assez de dh pour accepter le pari.", ephemeral=True)
            cursor.close()
            db.close()
            return

        await interaction.response.send_message(f"{opponent.mention}, {user.mention} vous a défié à une chasse au trésor pour {amount} dh! Réagissez avec ✅ pour accepter.")
        challenge_message = await interaction.original_response()
        await challenge_message.add_reaction("✅")

        def check(reaction, user):
            return str(reaction.emoji) == "✅" and user == opponent and reaction.message.id == challenge_message.id

        try:
            reaction, _ = await bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"{opponent.mention} n'a pas accepté le défi à temps.", ephemeral=True)
            cursor.close()
            db.close()
            return

        chest_values = ["grand prix", "petit prix", "rien", "rien"]
        random.shuffle(chest_values)

        embed = discord.Embed(title="Chasse au Trésor", description="Choisissez chacun un coffre au trésor (1-4)!", color=discord.Color.blue())
        embed.add_field(name="Coffre 1", value="❓", inline=True)
        embed.add_field(name="Coffre 2", value="❓", inline=True)
        embed.add_field(name="Coffre 3", value="❓", inline=True)
        embed.add_field(name="Coffre 4", value="❓", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/128/1355/1355900.png")

        await interaction.followup.send(embed=embed)
        message = await interaction.original_response()

        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣"]

        for emoji in emojis:
            await message.add_reaction(emoji)

        def check(reaction, user):
            return user in [interaction.user, opponent] and str(reaction.emoji) in emojis and reaction.message.id == message.id

        choices = {}
        try:
            while len(choices) < 2:
                reaction, reacting_user = await bot.wait_for("reaction_add", timeout=60.0, check=check)
                if reacting_user not in choices:
                    choices[reacting_user] = emojis.index(str(reaction.emoji))
        except asyncio.TimeoutError:
            await interaction.followup.send("Temps écoulé. Veuillez réessayer.", ephemeral=True)
            cursor.close()
            db.close()
            return

        user_choice = choices[user]
        opponent_choice = choices[opponent]

        user_prize = chest_values[user_choice]
        opponent_prize = chest_values[opponent_choice]

        user_amount_won, opponent_amount_won = 0, 0
        user_new_balance, opponent_new_balance = user_balance, opponent_balance

        if user_prize == "grand prix":
            user_amount_won = amount * 2
            user_new_balance += user_amount_won
        elif user_prize == "petit prix":
            user_amount_won = amount * 1.5
            user_new_balance += user_amount_won
        else:
            user_new_balance -= amount

        if opponent_prize == "grand prix":
            opponent_amount_won = amount * 2
            opponent_new_balance += opponent_amount_won
        elif opponent_prize == "petit prix":
            opponent_amount_won = amount * 1.5
            opponent_new_balance += opponent_amount_won
        else:
            opponent_new_balance -= amount

        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (user_new_balance, user.id))
        cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (opponent_new_balance, opponent.id))

        result_message = (f"{user.mention} a choisi le Coffre {user_choice + 1} et a trouvé {user_prize}.\n"
                          f"{opponent.mention} a choisi le Coffre {opponent_choice + 1} et a trouvé {opponent_prize}.\n")

        embed = discord.Embed(title="Chasse au Trésor", color=discord.Color.blue())
        embed.add_field(name=f"Choix de {user.display_name}: Coffre {user_choice + 1}", value=user_prize, inline=True)
        embed.add_field(name=f"Choix de {opponent.display_name}: Coffre {opponent_choice + 1}", value=opponent_prize, inline=True)
        embed.add_field(name="Résultat", value=result_message, inline=False)
        embed.add_field(name=f"Nouveau solde de {user.display_name}", value=f"{int(user_new_balance)} dh", inline=False)
        embed.add_field(name=f"Nouveau solde de {opponent.display_name}", value=f"{int(opponent_new_balance)} dh", inline=False)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/128/1355/1355900.png")

        await interaction.followup.send(embed=embed)

    db.commit()
    cursor.close()
    db.close()
@tresor.error
async def tresor_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.', ephemeral=True)



# ---- duelrpg ----
@bot.tree.command(name="duelrpg", description="Défiez un autre joueur dans un duel RPG avec une mise")
@app_commands.describe(opponent="Adversaire", bet="Mise à parier")
@app_commands.checks.cooldown(2, 86400, key=lambda i: (i.guild_id, i.user.id))
async def duelrpg(interaction: discord.Interaction, opponent: discord.Member, bet: int):
    if opponent == interaction.user:
        await interaction.response.send_message("Vous ne pouvez pas vous battre contre vous-même !", ephemeral=True)
        return

    # Envoyer une demande d'acceptation
    embed = discord.Embed(title="Duel RPG", description=f"{interaction.user.mention} vous a défié dans un duel RPG avec une mise de {bet} ! Acceptez-vous ?", color=0x00FF00)
    embed.add_field(name="Instructions", value="Réagissez avec ✅ pour accepter ou ❌ pour refuser.")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/934/934478.png")
    await interaction.response.send_message(content=opponent.mention, embed=embed)
    message = await interaction.original_response()

    await message.add_reaction('✅')
    await message.add_reaction('❌')

    def check_reaction(reaction, user):
        return user == opponent and str(reaction.emoji) in ['✅', '❌']

    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check_reaction)
        if str(reaction.emoji) == '❌':
            await interaction.followup.send(f"{opponent.mention} a refusé le duel.")
            return
    except asyncio.TimeoutError:
        await interaction.followup.send(f"{opponent.mention} n'a pas répondu à temps. Le duel est annulé.")
        return

    # Vérifier les fonds des joueurs
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    cursor.execute("SELECT portemonnaie FROM eco WHERE user_id = ?", (interaction.user.id,))
    author_money = cursor.fetchone()
    cursor.execute("SELECT portemonnaie FROM eco WHERE user_id = ?", (opponent.id,))
    opponent_money = cursor.fetchone()

    if author_money is None or opponent_money is None:
        await interaction.followup.send("L'un des joueurs n'est pas enregistré dans la base de données.")
        db.close()
        return

    if author_money[0] < bet or opponent_money[0] < bet:
        await interaction.followup.send("L'un des joueurs n'a pas assez d'argent pour cette mise.")
        db.close()
        return

    # Déduire la mise initiale
    cursor.execute("UPDATE eco SET portemonnaie = portemonnaie - ? WHERE user_id = ?", (bet, interaction.user.id))
    cursor.execute("UPDATE eco SET portemonnaie = portemonnaie - ? WHERE user_id = ?", (bet, opponent.id))
    db.commit()

    # Magasin de potions
    potions = {
        "heal": {"name": "🍷 - Potion de Soin", "effect": 30, "cost": 200, "emoji": "🍷"},
        "damage": {"name": "💥 - Potion de Dégâts", "effect": 20, "cost": 200, "emoji": "💥"},
        "poison": {"name": "☠️ - Potion de Poison", "effect": 10, "cost": 150, "emoji": "☠️"}
    }

    embed = discord.Embed(title="Magasin de Potions", description="Achetez des potions avant de commencer le duel.")
    for key, potion in potions.items():
        embed.add_field(name=potion["name"], value=f"Effet: {potion['effect']} - 💩 {potion['cost']} dhs")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/15972/15972238.png")

    await interaction.followup.send(embed=embed)

    def check_purchase(m):
        return m.author in [interaction.user, opponent] and (m.content.lower() in potions or m.content.lower() == 'done')

    player_potions = {interaction.user: [], opponent: []}
    max_potions = 3
    for player in [interaction.user, opponent]:
        await interaction.followup.send(f"{player.mention}, tapez le nom de la potion que vous voulez acheter (heal/damage/poison) ou 'done' pour terminer.")
        while True:
            if len(player_potions[player]) >= max_potions:
                await interaction.followup.send(f"{player.mention}, vous avez atteint la limite de {max_potions} potions.")
                break
            try:
                message = await bot.wait_for('message', timeout=60.0, check=check_purchase)
                if message.content.lower() == 'done':
                    break
                potion = potions[message.content.lower()]
                cursor.execute("SELECT portemonnaie FROM eco WHERE user_id = ?", (player.id,))
                money = cursor.fetchone()[0]
                if money >= potion['cost']:
                    player_potions[player].append(potion)
                    cursor.execute("UPDATE eco SET portemonnaie = portemonnaie - ? WHERE user_id = ?", (potion['cost'], player.id))
                    db.commit()
                    await interaction.followup.send(f"{player.mention} a acheté {potion['name']}.")
                else:
                    await interaction.followup.send(f"{player.mention}, vous n'avez pas assez d'argent pour acheter {potion['name']}.")
            except asyncio.TimeoutError:
                await interaction.followup.send(f"{player.mention} n'a pas répondu à temps.")
                break

    players = {
        interaction.user: {"HP": 100, "Attack": (10, 20), "Special": (25, 40), "Defense": 0, "Defense_Uses": 3, "Special_Uses": 3, "Potions": player_potions[interaction.user], "Banner_Color": 0x0000FF},
        opponent: {"HP": 100, "Attack": (10, 20), "Special": (25, 40), "Defense": 0, "Defense_Uses": 3, "Special_Uses": 3, "Potions": player_potions[opponent], "Banner_Color": 0xFF0000}
    }

    embed = discord.Embed(title="Duel RPG", description=f"{interaction.user.mention} a défié {opponent.mention} dans un duel RPG avec une mise de {bet} !", color=0x00FF00)
    embed.add_field(name="Instructions", value="Utilisez les réactions ci-dessous pour choisir votre action :\n⚔️ pour Attaquer\n✨ pour Attaque Spéciale (max 3 fois)\n🛡️ pour Défendre (max 3 fois)\n🍷 pour Utiliser une Potion")
    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7445/7445281.png")
    duel_message = await interaction.followup.send(embed=embed)

    current_turn = interaction.user
    other_player = opponent

    def check(reaction, user):
        return user == current_turn and str(reaction.emoji) in ['⚔️', '✨', '🛡️'] + [p["emoji"] for p in players[current_turn]["Potions"]]

    while players[interaction.user]["HP"] > 0 and players[opponent]["HP"] > 0:
        embed = discord.Embed(title="Tour de combat", description=f"{current_turn.mention}, c'est votre tour ! Choisissez une action :", color=players[current_turn]["Banner_Color"])
        embed.add_field(name="Stats", value=f"**{current_turn.mention}**: {players[current_turn]['HP']} HP, {players[current_turn]['Special_Uses']} Attaques Spéciales restantes, {len(players[current_turn]['Potions'])} Potion(s)\n**{other_player.mention}**: {players[other_player]['HP']} HP, {players[other_player]['Special_Uses']} Attaques Spéciales restantes, {len(players[other_player]['Potions'])} Potion(s)")
        action_message = await interaction.followup.send(embed=embed)

        await action_message.add_reaction('⚔️')
        await action_message.add_reaction('✨')
        await action_message.add_reaction('🛡️')
        for potion in players[current_turn]["Potions"]:
            await action_message.add_reaction(potion["emoji"])

        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=60.0, check=check)
            if str(reaction.emoji) == '⚔️':
                damage = random.randint(*players[current_turn]["Attack"])
                players[other_player]["HP"] -= damage
                result = f"{current_turn.mention} attaque {other_player.mention} et inflige {damage} dégâts."
            elif str(reaction.emoji) == '✨':
                if players[current_turn]["Special_Uses"] > 0:
                    damage = random.randint(*players[current_turn]["Special"])
                    players[other_player]["HP"] -= damage
                    players[current_turn]["Special_Uses"] -= 1
                    result = f"{current_turn.mention} utilise une attaque spéciale sur {other_player.mention} et inflige {damage} dégâts."
                else:
                    result = f"{current_turn.mention} n'a plus d'attaques spéciales restantes !"
            elif str(reaction.emoji) == '🛡️':
                if players[current_turn]["Defense_Uses"] > 0:
                    players[current_turn]["Defense"] += 10
                    players[current_turn]["Defense_Uses"] -= 1
                    result = f"{current_turn.mention} se défend et augmente sa défense."
                else:
                    result = f"{current_turn.mention} n'a plus de défenses restantes !"
            else:
                potion = next(p for p in players[current_turn]["Potions"] if p["emoji"] == str(reaction.emoji))
                if potion["name"] == "🍷 - Potion de Soin":
                    players[current_turn]["HP"] += potion["effect"]
                    result = f"{current_turn.mention} a utilisé une potion de soin et a soigné {potion['effect']} HP."
                else:
                    damage = potion["effect"]
                    players[other_player]["HP"] -= damage
                    result = f"{current_turn.mention} a utilisé {potion['name']} et inflige {damage} dégâts à {other_player.mention}."
                players[current_turn]["Potions"].remove(potion)

            await interaction.followup.send(result)

            if players[other_player]["HP"] <= 0:
                break

            current_turn, other_player = other_player, current_turn

        except asyncio.TimeoutError:
            await interaction.followup.send(f"{current_turn.mention} n'a pas répondu à temps. {other_player.mention} gagne le duel par forfait.")
            players[current_turn]["HP"] = 0
            break

    winner = interaction.user if players[interaction.user]["HP"] > 0 else opponent
    loser = opponent if winner == interaction.user else interaction.user
    cursor.execute("UPDATE eco SET portemonnaie = portemonnaie + ? WHERE user_id = ?", (2 * bet, winner.id))
    db.commit()
    db.close()

    await interaction.followup.send(f"Le duel est terminé ! {winner.mention} a gagné et remporte {2 * bet} dhs !")



# ----- duel -----
@bot.tree.command(name="duel", description="Jouez à Dice Duel avec une mise")
@app_commands.describe(amount="Montant à parier", opponent="Adversaire (optionnel)")
@app_commands.checks.cooldown(5, 86400, key=lambda i: (i.guild_id, i.user.id))
async def des(interaction: discord.Interaction, amount: int, opponent: discord.Member = None):
    user = interaction.user

    if amount <= 0:
        await interaction.response.send_message("La mise doit être un montant positif.", ephemeral=True)
        return
    
    if amount < 300:
        await interaction.response.send_message("La mise doit être au moins égale à 300 dhs",ephemeral=True)

    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()

    # Check user balance
    cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {user.id}')
    user_balance = cursor.fetchone()
    user_balance = user_balance[0] if user_balance else 0

    if user_balance < amount:
        await interaction.response.send_message("Vous n'avez pas assez de dh pour faire ce pari.", ephemeral=True)
        cursor.close()
        db.close()
        return

    if opponent is None:
        # Single-player mode
        user_roll = random.randint(1, 6)
        bot_roll = random.randint(1, 6)

        embed = discord.Embed(title="Dice Duel", color=discord.Color.blue())
        embed.add_field(name=f"{user.display_name}'s Roll", value=f"{user_roll} 🎲", inline=True)
        embed.add_field(name="Bot's Roll", value=f"{bot_roll} 🎲", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12907/12907890.png ")

        if user_roll > bot_roll:
            amount_won = amount
            new_user_balance = user_balance + amount_won
            cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
            result_message = f"{user.mention} a gagné {amount_won} dh! 🎉"
        elif user_roll < bot_roll:
            amount_lost = amount
            new_user_balance = user_balance - amount_lost
            cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
            result_message = f"{user.mention} a perdu {amount_lost} dh... 😢"
        else:
            result_message = "C'est une égalité! Vous récupérez votre mise."
            new_user_balance = user_balance

        embed.add_field(name="Résultat", value=result_message, inline=False)
        embed.add_field(name="Votre Nouveau Solde", value=f"{int(new_user_balance)} dh", inline=False)

        await interaction.response.send_message(embed=embed)
    else:
        # Two-player mode
        cursor.execute(f'SELECT portemonnaie FROM eco WHERE user_id = {opponent.id}')
        opponent_balance = cursor.fetchone()
        opponent_balance = opponent_balance[0] if opponent_balance else 0

        if opponent_balance < amount:
            await interaction.response.send_message(f"{opponent.mention} n'a pas assez de dh pour accepter le pari.", ephemeral=True)
            cursor.close()
            db.close()
            return

        challenge_message = await interaction.response.send_message(
            f"{opponent.mention}, {user.mention} vous a défié de jouer à Dice Duel pour {amount} dh! Réagissez avec ✅ pour accepter.")
        message = await interaction.original_response()

        await message.add_reaction("✅")

        def check(reaction, user_check):
            return str(reaction.emoji) == "✅" and user_check == opponent and reaction.message.id == message.id

        try:
            await bot.wait_for("reaction_add", timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await interaction.followup.send(f"{opponent.mention} n'a pas accepté le défi à temps.")
            cursor.close()
            db.close()
            return

        user_roll = random.randint(1, 6)
        opponent_roll = random.randint(1, 6)

        embed = discord.Embed(title="Dice Duel", color=discord.Color.blue())
        embed.add_field(name=f"{user.display_name}'s Roll", value=f"{user_roll} 🎲", inline=True)
        embed.add_field(name=f"{opponent.display_name}'s Roll", value=f"{opponent_roll} 🎲", inline=True)
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/12907/12907890.png ")

        if user_roll > opponent_roll:
            amount_won = amount
            new_user_balance = user_balance + amount_won
            new_opponent_balance = opponent_balance - amount_won
            cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
            cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_opponent_balance, opponent.id))
            result_message = f"{user.mention} a gagné {amount_won} dh! 🎉"
        elif user_roll < opponent_roll:
            amount_lost = amount
            new_user_balance = user_balance - amount_lost
            new_opponent_balance = opponent_balance + amount_lost
            cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_user_balance, user.id))
            cursor.execute("UPDATE eco SET portemonnaie = ? WHERE user_id = ?", (new_opponent_balance, opponent.id))
            result_message = f"{opponent.mention} a gagné {amount_lost} dh! 🎉"
        else:
            result_message = "C'est une égalité! Vous récupérez votre mise."
            new_user_balance = user_balance
            new_opponent_balance = opponent_balance

        embed.add_field(name="Résultat", value=result_message, inline=False)
        embed.add_field(name=f"Nouveau solde de {user.display_name}", value=f"{int(new_user_balance)} dh", inline=False)
        embed.add_field(name=f"Nouveau solde de {opponent.display_name}", value=f"{int(new_opponent_balance)} dh", inline=False)

        await interaction.followup.send(embed=embed)

    db.commit()
    cursor.close()
    db.close()
@des.error
async def vol_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f'⏳ Tu dois attendre {int(error.retry_after)} secondes avant de pouvoir utiliser cette commande à nouveau.', ephemeral=True)



@bot.tree.command(name="leaderboard", description="Voir le classement du serveur")
async def leaderboard(interaction: discord.Interaction):
    try:
        db = sqlite3.connect("eco.sqlite")
        cursor = db.cursor()
        cursor.execute("SELECT user_id, portemonnaie, banque, portefeuille FROM eco")
        results = cursor.fetchall()

        # Récupérer les prix actuels des cryptomonnaies
        cursor.execute("SELECT crypto_name, price FROM crypto_prices")
        crypto_prices = {crypto_name: price for crypto_name, price in cursor.fetchall()}
        
        user_net_worths = []
        for user_id, portemonnaie, banque, portefeuille in results:
            portefeuille = eval(portefeuille) if portefeuille else {}
            crypto_value = sum(amount * crypto_prices[crypto] for crypto, amount in portefeuille.items())
            net_worth = portemonnaie + banque + crypto_value
            user_net_worths.append((user_id, net_worth))

        # Trier les utilisateurs par valeur nette décroissante
        user_net_worths.sort(key=lambda x: x[1], reverse=True)

        embed = discord.Embed(title="Leaderboard", color=discord.Color.gold())
        embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/3593/3593584.png")
        if not user_net_worths:
            embed.description = "Aucun résultat trouvé."
        else:
            for i, (user_id, net_worth) in enumerate(user_net_worths[:10], start=1):
                try:
                    user = await bot.fetch_user(user_id)
                    embed.add_field(name=f"{i}. {user.display_name}", value=f"{int(net_worth)} dhs", inline=False)
                except discord.NotFound:
                    embed.add_field(name=f"{i}. Utilisateur inconnu", value=f"{int(net_worth)} dhs", inline=False)
        
        await interaction.response.send_message(embed=embed)
    except sqlite3.Error as e:
        await interaction.response.send_message("Une erreur de base de données s'est produite lors de l'exécution de la commande leaderboard.", ephemeral=True)
        print(f"SQLite error: {e}")
    except discord.DiscordException as e:
        await interaction.response.send_message("Une erreur Discord s'est produite lors de l'exécution de la commande leaderboard.", ephemeral=True)
        print(f"Discord error: {e}")
    except Exception as e:
        await interaction.response.send_message("Une erreur inconnue s'est produite lors de l'exécution de la commande leaderboard.", ephemeral=True)
        print(f"Unknown error: {e}")


# ----- daily ------
@bot.tree.command(name="daily", description="Recevoir votre récompense quotidienne")
async def daily(interaction: discord.Interaction):
    db = sqlite3.connect("eco.sqlite")
    cursor = db.cursor()
    user_id = interaction.user.id
    
    cursor.execute("SELECT portemonnaie, last_daily FROM eco WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result is None:
        await interaction.response.send_message("Tu n'es pas encore inscrit dans l'économie. Utilise une commande pour t'inscrire.", ephemeral=True)
        return
    
    portemonnaie, last_daily = result
    
    now = datetime.now()
    if last_daily:
        last_daily = datetime.strptime(last_daily, "%Y-%m-%d %H:%M:%S.%f")
        delta = now - last_daily
        
        if delta < timedelta(days=1):
            next_daily = last_daily + timedelta(days=1)
            time_left = next_daily - now
            hours, remainder = divmod(time_left.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            await interaction.response.send_message(f"Tu as déjà réclamé tes dhs quotidiens. Réessaie dans {hours}h {minutes}m {seconds}s.", ephemeral=True)
            return
    
    new_portemonnaie = portemonnaie + 150
    cursor.execute("UPDATE eco SET portemonnaie = ?, last_daily = ? WHERE user_id = ?", 
                (new_portemonnaie, now.strftime("%Y-%m-%d %H:%M:%S.%f"), user_id))
    db.commit()
    
    await interaction.response.send_message(f"💩 Tu as reçu 150 dhs! Nouvelle balance: {int(new_portemonnaie)} dhs.")
    
    cursor.close()
    db.close() 



# ----- help ------
@bot.tree.command(name="help", description="Afficher le menu d'aide")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Aide économie", description="Menu d'aide")
    embed.add_field(name=":record_button: `balance`", value="Vérifier votre solde")
    embed.add_field(name=":record_button: `withdraw`", value="Déposer du dh dans la banque")
    embed.add_field(name=":record_button: `deposit`", value="Déposer du dh dans le portemonnaie")
    embed.add_field(name=":record_button: `dh`", value="Jouez pour gagner du dh - **`10× par jour`**")
    embed.add_field(name=":record_button: `daily`", value="Recevez votre récompense quotidienne - **`1× par jour`**")
    embed.add_field(name=":record_button: `miner`", value="Miner du BITEcoin pour gagner du dh - **`2× par jour`**")
    embed.add_field(name=":record_button: `vol`", value="Voler quelqu'un sur son portemonnaie (attention à ne pas vous faire choper) - **`2× par jour`**")
    embed.add_field(name=":record_button: `leaderboard`", value="Voir le classement du serveur") 
    embed.add_field(name=":record_button: `pari`", value="Pariez une certaine somme de d'argent, /pari [somme] - **`4× par jour`**")
    embed.add_field(name=":record_button: `pileouface`", value="Pariez sur pile ou face, /pileouface [mise] [pile/face] - **`4× par jour`**")
    embed.add_field(name=":wireless:/:record_button: `roulette`", value="Lancez une roulette ou jouer à la roulette avec un deuxieme joueur - **`4× par jour`**")
    embed.add_field(name=":wireless:/:record_button: `duel`", value="Lancez un duel de des contre quelqu'un pour gagner / perdre de l'argent, /duel @[cible] [montant] ou bien lancez un duel contre le bot /duel [montant] - **`5× par jour`**")
    embed.add_field(name=":wireless:/:record_button: `trésor`", value="Lancez une chasse au tresor seul ou avec quelqu'un d'autre - **`3× par jour`**")
    embed.add_field(name=":wireless: `duelrpg`", value="Lancez un duel rpg contre quelqu'un du serveur avec une mise - **`2× par jour`**")

    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2295/2295218.png")
    
    await interaction.response.send_message(embed=embed,ephemeral=True)

    embed_crypto = discord.Embed(title="Aide crypto", description="Menu d'aide crypto")
    embed_crypto.add_field(name=":record_button: `crypto_prices`", value="Vérifier les prix de cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `portefeuille`", value="Voir votre portefeuille de cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `buy_crypto`", value="Acheter de la cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `sell_crypto`", value="Vendre de la cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `withdraw_crypto`", value="Retirer des fonds du portefeuille de cryptomonnaie vers le portemonnaie")
    embed_crypto.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7280/7280222.png ")
    await interaction.followup.send(embed=embed_crypto, ephemeral=True)


# ----- help_economy ------
@bot.tree.command(name="help_economy", description="Afficher le menu d'aide")
async def help(interaction: discord.Interaction):
    embed = discord.Embed(title="Aide économie", description="Menu d'aide")
    embed.add_field(name=":record_button: `balance`", value="Vérifier votre solde")
    embed.add_field(name=":record_button: `withdraw`", value="Déposer du dh dans la banque")
    embed.add_field(name=":record_button: `deposit`", value="Déposer du dh dans le portemonnaie")
    embed.add_field(name=":record_button: `dh`", value="Jouez pour gagner du dh - **`10× par jour`**")
    embed.add_field(name=":record_button: `daily`", value="Recevez votre récompense quotidienne - **`1× par jour`**")
    embed.add_field(name=":record_button: `miner`", value="Miner du BITEcoin pour gagner du dh - **`2× par jour`**")
    embed.add_field(name=":record_button: `vol`", value="Voler quelqu'un sur son portemonnaie (attention à ne pas vous faire choper) - **`2× par jour`**")
    embed.add_field(name=":record_button: `leaderboard`", value="Voir le classement du serveur") 
    embed.add_field(name=":record_button: `pari`", value="Pariez une certaine somme de d'argent, /pari [somme] - **`4× par jour`**")
    embed.add_field(name=":record_button: `pileouface`", value="Pariez sur pile ou face, /pileouface [mise] [pile/face] - **`4× par jour`**")
    embed.add_field(name=":wireless:/:record_button: `roulette`", value="Lancez une roulette ou jouer à la roulette avec un deuxieme joueur - **`4× par jour`**")
    embed.add_field(name=":wireless:/:record_button: `duel`", value="Lancez un duel de des contre quelqu'un pour gagner / perdre de l'argent, /duel @[cible] [montant] ou bien lancez un duel contre le bot /duel [montant] - **`5× par jour`**")
    embed.add_field(name=":wireless:/:record_button: `trésor`", value="Lancez une chasse au tresor seul ou avec quelqu'un d'autre - **`3× par jour`**")
    embed.add_field(name=":wireless: `duelrpg`", value="Lancez un duel rpg contre quelqu'un du serveur avec une mise - **`2× par jour`**")

    embed.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/2295/2295218.png")
    
    await interaction.response.send_message(embed=embed)



# ----- help_crypto ------
@bot.tree.command(name="help_crypto", description="Afficher le menu d'aide")
async def help(interaction: discord.Interaction):
    embed_crypto = discord.Embed(title="Aide crypto", description="Menu d'aide crypto")
    embed_crypto.add_field(name=":record_button: `crypto_prices`", value="Vérifier les prix de cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `portefeuille`", value="Voir votre portefeuille de cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `buy_crypto`", value="Acheter de la cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `sell_crypto`", value="Vendre de la cryptomonnaie")
    embed_crypto.add_field(name=":record_button: `withdraw_crypto`", value="Retirer des fonds du portefeuille de cryptomonnaie vers le portemonnaie")
    embed_crypto.set_thumbnail(url="https://cdn-icons-png.flaticon.com/512/7280/7280222.png")
    await interaction.response.send_message(embed=embed_crypto)


async def main():
    await bot.start('')

asyncio.run(main())

