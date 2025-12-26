import discord
from discord.ext import commands
from datetime import datetime, timedelta
import pytz
import json
import os
import asyncio

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

TEST_MODE = True  # <<< MUDE PARA FALSE EM PRODUÇÃO

# ================= BOT =================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True
intents.message_content = True

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

def janela_ativa():
    if TEST_MODE:
        return True

    agora = agora_br()
    for h in TRATAMENTO_JANELAS:
        inicio = agora.replace(hour=h, minute=55, second=0, microsecond=0)
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

    canal = guild.get_channel(CANAL_QUARENTENA)
    if not canal:
        return

    if not janela_ativa():
        print("⏳ Fora da janela de tratamento")
        return

    dados = carregar_dados()

    for member in guild.members:
        if member.bot:
            continue

        if guild.get_role(ROLE_SAV) not in member.roles:
            continue

        if guild.get_role(ROLE_CRONICA) in member.roles:
            continue

        user_id = str(member.id)

        if user_id in dados and dados[user_id].get("tratamento_iniciado"):
            continue

        msg = await canal.send(
            f"{member.mention} 💊 **Tratamento disponível!**\n"
            f"Reaja com 💊 para iniciar.\n"
            f"⏳ A mensagem dura 10 minutos."
        )
        await msg.add_reaction("💊")

        dados[user_id] = {
            "mensagem_id": msg.id,
            "tratamento_iniciado": False,
            "infectado_em": agora_br().isoformat()
        }

        salvar_dados(dados)

        bot.loop.create_task(remover_mensagem(msg))

# ================= REAÇÃO =================

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.emoji != "💊":
        return

    guild = reaction.message.guild
    member = guild.get_member(user.id)
    dados = carregar_dados()

    user_id = str(user.id)
    if user_id not in dados:
        return

    if dados[user_id]["tratamento_iniciado"]:
        return

    dados[user_id]["tratamento_iniciado"] = True
    salvar_dados(dados)

    await reaction.message.channel.send(
        f"🧪 {user.mention} iniciou o tratamento.\n"
        f"⏳ Cura em **40 minutos**."
    )

    await asyncio.sleep(40 * 60)

    await curar(member, guild)
    dados.pop(user_id, None)
    salvar_dados(dados)

# ================= AÇÕES =================

async def curar(member, guild):
    await member.remove_roles(
        guild.get_role(ROLE_SAV),
        guild.get_role(ROLE_QUARENTENA),
        reason="Tratamento concluído"
    )

# ================= LIMPEZA =================

async def remover_mensagem(msg):
    await asyncio.sleep(10 * 60)
    try:
        await msg.delete()
    except:
        pass

# ================= RUN =================

bot.run(TOKEN)
