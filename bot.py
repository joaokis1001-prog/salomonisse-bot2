import discord
from discord.ext import commands
from datetime import datetime, timedelta, time
import pytz
import json
import os

# ================= CONFIGURAÇÕES =================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 123456789012345678  # ID do servidor

ROLE_SAV = 1453502439167623289
ROLE_QUARENTENA = 1453505974282485956
ROLE_CRONICA = 1453808748387766334

CANAL_QUARENTENA = 1453640324097376391

TIMEZONE = pytz.timezone("America/Sao_Paulo")

DATA_FILE = "dados.json"

TRATAMENTO_JANELAS = [
    (0, 10), (2, 10), (4, 10), (6, 10),
    (8, 10), (10, 10), (12, 10), (14, 10),
    (16, 10), (18, 10), (20, 10), (22, 10),
]

# =================================================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================= DADOS =================

def carregar_dados():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DATA_FILE, "w") as f:
        json.dump(dados, f, indent=2)

# ================= HORÁRIOS =================

def agora_br():
    return datetime.now(TIMEZONE)

def tratamento_aberto():
    agora = agora_br()
    for hora, duracao in TRATAMENTO_JANELAS:
        inicio = agora.replace(hour=hora, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(minutes=duracao)
        if inicio <= agora <= fim:
            return True
    return False

# ================= BOT =================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    await executar_logica()
    await bot.close()

# ================= LÓGICA PRINCIPAL =================

async def executar_logica():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    dados = carregar_dados()
    agora = agora_br()

    for member in guild.members:
        if member.bot:
            continue

        # ===== SE TEM SALOMONISSE =====
        if guild.get_role(ROLE_SAV) in member.roles:
            user_id = str(member.id)

            if user_id not in dados:
                dados[user_id] = {
                    "infectado_em": agora.isoformat(),
                    "tratou": False
                }

            infectado_em = datetime.fromisoformat(dados[user_id]["infectado_em"])

            # ===== 48h SEM TRATAR → CRÔNICA =====
            if agora - infectado_em >= timedelta(hours=48):
                await aplicar_cronica(member, guild)
                dados.pop(user_id, None)
                continue

            # ===== 40 MIN DE QUARENTENA =====
            if agora - infectado_em >= timedelta(minutes=40):
                if tratamento_aberto():
                    canal = guild.get_channel(CANAL_QUARENTENA)
                    if canal:
                        await canal.send(
                            f"{member.mention}, 💊 **tratamento disponível agora!** "
                            f"Você tem **10 minutos**."
                        )

    salvar_dados(dados)

# ================= AÇÕES =================

async def aplicar_cronica(member, guild):
    await member.remove_roles(
        guild.get_role(ROLE_SAV),
        guild.get_role(ROLE_QUARENTENA),
        reason="Salomonisse Crônica"
    )
    await member.add_roles(
        guild.get_role(ROLE_CRONICA),
        reason="Salomonisse Crônica"
    )

# ================= RUN =================

bot.run(TOKEN)
