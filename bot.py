import discord
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import json
import os
import asyncio

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1453XXXXXXXXXXXXXX  # <-- ID REAL DO SERVIDOR
ROLE_SAV = 1453502439167623289
ROLE_CRONICA = 1453808748387766334

CANAL_QUARENTENA = 1453640324097376391

TIMEZONE = pytz.timezone("America/Sao_Paulo")

DATA_FILE = "dados.json"

# Janelas a cada 2 horas
JANELAS_TRATAMENTO = [0,2,4,6,8,10,12,14,16,18,20,22]

DURACAO_MENSAGEM = 10       # minutos
DURACAO_TRATAMENTO = 40    # minutos

# ================= BOT =================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= UTIL =================

def agora_br():
    return datetime.now(TIMEZONE)

def carregar_dados():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DATA_FILE, "w") as f:
        json.dump(dados, f, indent=2)

def janela_aberta():
    agora = agora_br()
    for h in JANELAS_TRATAMENTO:
        inicio = agora.replace(hour=h, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(minutes=DURACAO_MENSAGEM)
        if inicio <= agora <= fim:
            return True
    return False

# ================= EVENT =================

@bot.event
async def on_ready():
    print(f"🤖 Conectado como {bot.user}")

    try:
        guild = await bot.fetch_guild(GUILD_ID)
    except discord.NotFound:
        print("❌ Guild não encontrada")
        await bot.close()
        return

    await executar_logica(guild)
    await bot.close()

# ================= LÓGICA PRINCIPAL =================

async def executar_logica(guild):
    dados = carregar_dados()
    agora = agora_br()

    canal = guild.get_channel(CANAL_QUARENTENA)
    role_sav = guild.get_role(ROLE_SAV)
    role_cronica = guild.get_role(ROLE_CRONICA)

    for member in guild.members:
        if member.bot:
            continue

        if role_cronica in member.roles:
            continue

        if role_sav not in member.roles:
            continue

        uid = str(member.id)

        # ===== REGISTRO DE INFECÇÃO =====
        if uid not in dados:
            dados[uid] = {
                "infectado_em": agora.isoformat()
            }

        infectado_em = datetime.fromisoformat(dados[uid]["infectado_em"])

        # ===== CRÔNICA (48h SEM TRATAMENTO) =====
        if "tratamento_iniciado_em" not in dados[uid]:
            if agora - infectado_em >= timedelta(hours=48):
                await aplicar_cronica(member, role_sav, role_cronica)
                dados.pop(uid, None)
                continue

        # ===== FINALIZAR TRATAMENTO =====
        if "tratamento_iniciado_em" in dados[uid]:
            inicio = datetime.fromisoformat(dados[uid]["tratamento_iniciado_em"])
            if agora - inicio >= timedelta(minutes=DURACAO_TRATAMENTO):
                await member.remove_roles(role_sav, reason="Tratamento concluído")
                dados.pop(uid, None)
                print(f"✅ {member} curado")
            continue

        # ===== ENVIAR MENSAGEM DE TRATAMENTO =====
        if janela_aberta() and "mensagem_enviada_em" not in dados[uid]:
            msg = await canal.send(
                f"{member.mention} 💊 **Tratamento disponível agora!**\n"
                f"⏳ Você tem **{DURACAO_MENSAGEM} minutos** para aceitar."
            )
            await msg.add_reaction("💊")

            dados[uid]["mensagem_id"] = msg.id
            dados[uid]["mensagem_enviada_em"] = agora.isoformat()

            # agenda remoção da mensagem
            bot.loop.create_task(remover_mensagem(msg, uid))

    salvar_dados(dados)

# ================= REAÇÃO =================

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if str(reaction.emoji) != "💊":
        return

    dados = carregar_dados()
    uid = str(user.id)

    if uid not in dados:
        return

    if "tratamento_iniciado_em" in dados[uid]:
        return

    dados[uid]["tratamento_iniciado_em"] = agora_br().isoformat()
    salvar_dados(dados)

    try:
        await reaction.message.delete()
    except:
        pass

    print(f"💊 Tratamento iniciado por {user}")

# ================= AUX =================

async def remover_mensagem(msg, uid):
    await asyncio.sleep(DURACAO_MENSAGEM * 60)
    try:
        await msg.delete()
    except:
        pass

    dados = carregar_dados()
    if uid in dados:
        dados[uid].pop("mensagem_enviada_em", None)
        dados[uid].pop("mensagem_id", None)
        salvar_dados(dados)

async def aplicar_cronica(member, role_sav, role_cronica):
    await member.remove_roles(role_sav, reason="Salomonisse Crônica")
    await member.add_roles(role_cronica, reason="Salomonisse Crônica")
    print(f"☠️ {member} virou crônico")

# ================= RUN =================

bot.run(TOKEN)
