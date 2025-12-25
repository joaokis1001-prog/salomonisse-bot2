import discord
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import json
import os

# ================= CONFIG =================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 123456789012345678

ROLE_SAV = 1453502439167623289
ROLE_QUARENTENA = 1453505974282485956
ROLE_CRONICA = 1453808748387766334

CANAL_QUARENTENA = 1453640324097376391

TIMEZONE = pytz.timezone("America/Sao_Paulo")

DATA_FILE = "dados.json"

TRATAMENTO_JANELAS = [0,2,4,6,8,10,12,14,16,18,20,22]

# ================= BOT =================

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
    for h in TRATAMENTO_JANELAS:
        inicio = agora.replace(hour=h, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(minutes=10)
        if inicio <= agora <= fim:
            return True
    return False

# ================= EVENT =================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    await executar_logica()
    await bot.close()

# ================= LÓGICA =================

async def executar_logica():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    dados = carregar_dados()
    agora = agora_br()

    for member in guild.members:
        if member.bot:
            continue

        user_id = str(member.id)

        # ===== IGNORA CRÔNICOS =====
        if guild.get_role(ROLE_CRONICA) in member.roles:
            continue

        # ===== NOVA INFECÇÃO =====
        if guild.get_role(ROLE_SAV) in member.roles:
            if user_id not in dados:
                dados[user_id] = {
                    "infectado_em": agora.isoformat(),
                    "avisado_tratamento": False,
                    "quarentena_aplicada": False
                }

            infectado_em = datetime.fromisoformat(dados[user_id]["infectado_em"])

            # ===== 48h → CRÔNICA =====
            if agora - infectado_em >= timedelta(hours=48):
                await aplicar_cronica(member, guild)
                dados.pop(user_id, None)
                continue

            # ===== 40 MIN → QUARENTENA =====
            if agora - infectado_em >= timedelta(minutes=40):
                if not dados[user_id]["quarentena_aplicada"]:
                    await member.add_roles(
                        guild.get_role(ROLE_QUARENTENA),
                        reason="Quarentena iniciada"
                    )
                    dados[user_id]["quarentena_aplicada"] = True

                # ===== AVISO DE TRATAMENTO =====
                if tratamento_aberto() and not dados[user_id]["avisado_tratamento"]:
                    canal = guild.get_channel(CANAL_QUARENTENA)
                    if canal:
                        await canal.send(
                            f"{member.mention} 💊 **Tratamento disponível agora!**\n"
                            f"⏳ Você tem **10 minutos**."
                        )
                    dados[user_id]["avisado_tratamento"] = True

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
