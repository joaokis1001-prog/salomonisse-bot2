import discord
import json
import os
import asyncio
from datetime import datetime, timedelta
import pytz

# ================= CONFIGURAÇÕES =================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 1453468097569886361
CANAL_QUARENTENA_ID = 1453640324097376391

EMOJI_TRATAMENTO = "💊"

TRATAMENTO_MINUTOS = 40
DURACAO_MENSAGEM_MINUTOS = 10

# Janelas a cada 2 horas
TRATAMENTO_JANELAS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]

MODO_TESTE = True  # <<< MUDE PARA False EM PRODUÇÃO

DADOS_ARQ = "dados.json"
TZ = pytz.timezone("America/Sao_Paulo")

# ================= FUNÇÕES AUXILIARES =================

def agora_br():
    return datetime.now(TZ)

def carregar_dados():
    if not os.path.exists(DADOS_ARQ):
        return {}
    with open(DADOS_ARQ, "r") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DADOS_ARQ, "w") as f:
        json.dump(dados, f, indent=4)

def tratamento_aberto():
    if MODO_TESTE:
        return True

    agora = agora_br()
    for h in TRATAMENTO_JANELAS:
        inicio = agora.replace(hour=h, minute=0, second=0, microsecond=0)
        fim = inicio + timedelta(minutes=DURACAO_MENSAGEM_MINUTOS)
        if inicio <= agora <= fim:
            return True
    return False

# ================= DISCORD =================

intents = discord.Intents.default()
intents.reactions = True
intents.guilds = True
intents.members = True
intents.messages = True

client = discord.Client(intents=intents)

mensagem_tratamento = None

# ================= EVENTOS =================

@client.event
async def on_ready():
    print(f"🤖 Conectado como {client.user}")

    guild = client.get_guild(GUILD_ID)
    if not guild:
        print("❌ Guild não encontrada")
        return

    canal = guild.get_channel(CANAL_QUARENTENA_ID)
    if not canal:
        print("❌ Canal não encontrado")
        return

    dados = carregar_dados()

    if not tratamento_aberto():
        print("⏰ Fora da janela de tratamento")
        return

    # ENVIA MENSAGEM DE TRATAMENTO
    msg = await canal.send(
        "🦠 **Tratamento contra Salomonisse disponível!**\n\n"
        "Clique no emoji 💊 para iniciar o tratamento.\n"
        f"⏳ Duração: {TRATAMENTO_MINUTOS} minutos"
    )

    await msg.add_reaction(EMOJI_TRATAMENTO)

    global mensagem_tratamento
    mensagem_tratamento = msg

    print("📨 Mensagem enviada")

    # Remove mensagem após 10 minutos
    await asyncio.sleep(DURACAO_MENSAGEM_MINUTOS * 60)
    try:
        await msg.delete()
        print("🗑 Mensagem removida")
    except:
        pass

    await client.close()  # encerra para não virar 24/7

@client.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    if not mensagem_tratamento:
        return

    if reaction.message.id != mensagem_tratamento.id:
        return

    if str(reaction.emoji) != EMOJI_TRATAMENTO:
        return

    dados = carregar_dados()
    user_id = str(user.id)

    inicio = agora_br()
    fim = inicio + timedelta(minutes=TRATAMENTO_MINUTOS)

    dados[user_id] = {
        "tratamento_inicio": inicio.isoformat(),
        "tratamento_fim": fim.isoformat()
    }

    salvar_dados(dados)

    await reaction.message.channel.send(
        f"💊 {user.mention} iniciou o tratamento!\n"
        f"🕒 Termina às **{fim.strftime('%H:%M')}**"
    )

    print(f"✅ Tratamento iniciado para {user}")

# ================= START =================

client.run(TOKEN)
