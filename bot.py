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

# Janelas a cada 2 horas a partir da meia-noite
TRATAMENTO_JANELAS = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22]

MODO_TESTE = False  # <<< True ignora horário

DADOS_ARQ = "dados.json"
TZ = pytz.timezone("America/Sao_Paulo")

# ================= FUNÇÕES AUXILIARES =================

def agora_br():
    return datetime.now(TZ)

def carregar_dados():
    if not os.path.exists(DADOS_ARQ):
        return {}
    with open(DADOS_ARQ, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DADOS_ARQ, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def tratamento_aberto():
    """
    Verifica se agora está dentro de alguma janela válida
    Ex: 00:00–00:10, 02:00–02:10, etc
    """
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
    global mensagem_tratamento

    print(f"🤖 Conectado como {client.user}")
    print(f"🕒 Horário BR: {agora_br().strftime('%Y-%m-%d %H:%M:%S')}")

    guild = client.get_guild(GUILD_ID)
    if not guild:
        print("❌ Guild não encontrada")
        await client.close()
        return

    canal = guild.get_channel(CANAL_QUARENTENA_ID)
    if not canal:
        print("❌ Canal não encontrado")
        await client.close()
        return

    if not tratamento_aberto():
        print("⏰ Fora da janela de tratamento")
        await client.close()
        return

    # ================= ENVIA MENSAGEM =================

    mensagem_tratamento = await canal.send(
        "🦠 **Tratamento contra Salomonisse disponível!**\n\n"
        "Clique no emoji 💊 para iniciar o tratamento.\n"
        f"⏳ Duração do tratamento: **{TRATAMENTO_MINUTOS} minutos**\n"
        f"⌛ Mensagem ativa por **{DURACAO_MENSAGEM_MINUTOS} minutos**"
    )

    await mensagem_tratamento.add_reaction(EMOJI_TRATAMENTO)

    print("📨 Mensagem de tratamento enviada")

    # ================= REMOVE MENSAGEM =================

    await asyncio.sleep(DURACAO_MENSAGEM_MINUTOS * 60)

    try:
        await mensagem_tratamento.delete()
        print("🗑 Mensagem removida")
    except:
        pass

    print("🔌 Encerrando bot")
    await client.close()

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

    agora = agora_br()
    fim = agora + timedelta(minutes=TRATAMENTO_MINUTOS)

    # Evita reiniciar tratamento se já estiver ativo
    if user_id in dados:
        fim_antigo = datetime.fromisoformat(dados[user_id]["tratamento_fim"])
        if fim_antigo > agora:
            await reaction.message.channel.send(
                f"⚠️ {user.mention}, você já está em tratamento até "
                f"**{fim_antigo.strftime('%H:%M')}**."
            )
            return

    dados[user_id] = {
        "tratamento_inicio": agora.isoformat(),
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
