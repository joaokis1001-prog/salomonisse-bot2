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
ROLE_CRONICA = 1453808748387766334

CANAL_QUARENTENA = 1453640324097376391

TIMEZONE = pytz.timezone("America/Sao_Paulo")

DATA_FILE = "dados.json"

TRATAMENTO_JANELAS = [0,2,4,6,8,10,12,14,16,18,20,22]

EMOJI_TRATAMENTO = "💊"

TEMPO_TRATAMENTO = timedelta(minutes=40)
TEMPO_CRONICA = timedelta(hours=48)
DURACAO_MENSAGEM = timedelta(minutes=10)

# ================= BOT =================

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.reactions = True

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

# ================= TEMPO =================

def agora_br():
    return datetime.now(TIMEZONE)

def janela_ativa():
    agora = agora_br()
    for h in TRATAMENTO_JANELAS:
        inicio = agora.replace(hour=h, minute=0, second=0, microsecond=0)
        envio = inicio - timedelta(minutes=5)
        fim = envio + DURACAO_MENSAGEM
        if envio <= agora <= fim:
            return True
    return False

# ================= EVENT =================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    await executar_logica()
    await bot.close()

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot or reaction.emoji != EMOJI_TRATAMENTO:
        return

    dados = carregar_dados()
    user_id = str(user.id)

    if user_id not in dados:
        return

    agora = agora_br()

    if dados[user_id].get("cura_em"):
        return

    dados[user_id]["tratamento_aceito_em"] = agora.isoformat()
    dados[user_id]["cura_em"] = (agora + TEMPO_TRATAMENTO).isoformat()
    dados[user_id]["mensagem_id"] = None

    salvar_dados(dados)

# ================= LÓGICA =================

async def executar_logica():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return

    canal = guild.get_channel(CANAL_QUARENTENA)
    if not canal:
        return

    dados = carregar_dados()
    agora = agora_br()

    for member in guild.members:
        if member.bot:
            continue

        if guild.get_role(ROLE_SAV) not in member.roles:
            continue

        if guild.get_role(ROLE_CRONICA) in member.roles:
            continue

        user_id = str(member.id)

        if user_id not in dados:
            dados[user_id] = {
                "infectado_em": agora.isoformat(),
                "tratamento_aceito_em": None,
                "cura_em": None,
                "mensagem_id": None
            }

        infectado_em = datetime.fromisoformat(dados[user_id]["infectado_em"])

        # ===== CRÔNICA =====
        if agora - infectado_em >= TEMPO_CRONICA:
            await aplicar_cronica(member, guild)
            dados.pop(user_id, None)
            continue

        # ===== CURA =====
        if dados[user_id]["cura_em"]:
            cura_em = datetime.fromisoformat(dados[user_id]["cura_em"])
            if agora >= cura_em:
                await member.remove_roles(guild.get_role(ROLE_SAV), reason="Tratamento concluído")
                dados.pop(user_id, None)
            continue

        # ===== MENSAGEM DE TRATAMENTO =====
        if janela_ativa() and not dados[user_id]["mensagem_id"]:
            msg = await canal.send(
                f"{member.mention} 💊 **Tratamento disponível contra a Salomonisse**\n"
                f"Reaja com 💊 para iniciar o tratamento.\n"
                f"⏳ Cura em **40 minutos**."
            )
            await msg.add_reaction(EMOJI_TRATAMENTO)

            dados[user_id]["mensagem_id"] = msg.id
            salvar_dados(dados)

            # apagar mensagem após 10 minutos
            asyncio.create_task(apagar_mensagem(msg, user_id))

    salvar_dados(dados)

# ================= AÇÕES =================

async def apagar_mensagem(msg, user_id):
    await asyncio.sleep(DURACAO_MENSAGEM.total_seconds())
    try:
        await msg.delete()
    except:
        pass

    dados = carregar_dados()
    if user_id in dados:
        dados[user_id]["mensagem_id"] = None
        salvar_dados(dados)

async def aplicar_cronica(member, guild):
    await member.remove_roles(
        guild.get_role(ROLE_SAV),
        reason="Salomonisse Crônica"
    )
    await member.add_roles(
        guild.get_role(ROLE_CRONICA),
        reason="Salomonisse Crônica"
    )

# ================= RUN =================

bot.run(TOKEN)
