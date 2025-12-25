import os
import json
import random
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

# ================== CONFIGURAÇÕES ==================

TOKEN = os.getenv("DISCORD_TOKEN")

GUILD_ID = 145000000000000000  # opcional, pode deixar 0
SALOMONISSE_ROLE_ID = 1453502439167623289
QUARENTENA_ROLE_ID = 1453505974282485956
CRONICA_ROLE_ID = 1453808748387766334
QUARENTENA_CHANNEL_ID = 1453640324097376391

DATA_FILE = "data.json"

TIMEZONE = timezone(timedelta(hours=-3))  # Brasil UTC-3

# Janelas de tratamento (a cada 2h, 5 minutos)
TRATAMENTO_HORARIOS = [
    0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 20, 22
]

# ================== BOT ==================

intents = discord.Intents.default()
intents.members = True
intents.reactions = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ================== UTILIDADES ==================

def agora():
    return datetime.now(TIMEZONE)

def carregar_dados():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def salvar_dados(dados):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2)

def dentro_do_tratamento():
    a = agora()
    return a.hour in TRATAMENTO_HORARIOS and a.minute < 5

# ================== EVENTO PRINCIPAL ==================

@bot.event
async def on_ready():
    print(f"🤖 Bot conectado como {bot.user}")
    await executar_sistema()
    await bot.close()  # encerra após rodar

# ================== SISTEMA ==================

async def executar_sistema():
    dados = carregar_dados()
    agora_dt = agora()

    for guild in bot.guilds:
        canal_q = guild.get_channel(QUARENTENA_CHANNEL_ID)

        for member in guild.members:
            uid = str(member.id)
            if uid not in dados:
                continue

            info = dados[uid]

            # ====== CRÔNICA (48h) ======
            infectado_em = datetime.fromisoformat(info["infectado_em"])
            if agora_dt - infectado_em >= timedelta(hours=48):
                await remover_cargo(member, SALOMONISSE_ROLE_ID)
                await remover_cargo(member, QUARENTENA_ROLE_ID)
                await adicionar_cargo(member, CRONICA_ROLE_ID)

                if canal_q:
                    await canal_q.send(
                        f"☠️ {member.mention} desenvolveu **Salomonisse Crônica**."
                    )

                del dados[uid]
                continue

            # ====== QUARENTENA (40min) ======
            if "quarentena_inicio" in info:
                inicio = datetime.fromisoformat(info["quarentena_inicio"])
                if agora_dt - inicio >= timedelta(minutes=40):
                    await remover_cargo(member, SALOMONISSE_ROLE_ID)
                    await remover_cargo(member, QUARENTENA_ROLE_ID)

                    if canal_q:
                        msg = await canal_q.send(
                            f"✅ {member.mention} concluiu a quarentena."
                        )
                        await msg.delete(delay=5)

                    del dados[uid]

    # ====== INFECÇÃO DIÁRIA ======
    if agora_dt.hour == 0 and agora_dt.minute < 5:
        for guild in bot.guilds:
            role = guild.get_role(SALOMONISSE_ROLE_ID)
            if not role:
                continue

            candidatos = [
                m for m in guild.members
                if not m.bot
                and role not in m.roles
                and guild.get_role(CRONICA_ROLE_ID) not in m.roles
            ]

            if not candidatos:
                continue

            escolhido = random.choice(candidatos)
            await adicionar_cargo(escolhido, SALOMONISSE_ROLE_ID)

            dados[str(escolhido.id)] = {
                "infectado_em": agora_dt.isoformat()
            }

            canal_q = guild.get_channel(QUARENTENA_CHANNEL_ID)
            if canal_q:
                msg = await canal_q.send(
                    f"🦠 {escolhido.mention} foi infectado!\n"
                    f"Reaja com ☣️ para entrar em quarentena."
                )
                await msg.add_reaction("☣️")

    salvar_dados(dados)

# ================== REAÇÃO ==================

@bot.event
async def on_raw_reaction_add(payload):
    if str(payload.emoji) != "☣️":
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member or member.bot:
        return

    dados = carregar_dados()
    uid = str(member.id)

    if uid not in dados:
        return

    if "quarentena_inicio" in dados[uid]:
        return

    if not dentro_do_tratamento():
        return

    dados[uid]["quarentena_inicio"] = agora().isoformat()
    salvar_dados(dados)

    await adicionar_cargo(member, QUARENTENA_ROLE_ID)

    canal_q = guild.get_channel(QUARENTENA_CHANNEL_ID)
    if canal_q:
        await canal_q.send(
            f"☣️ {member.mention} entrou em quarentena.\n"
            f"⏱️ Duração: **40 minutos**."
        )

# ================== CARGOS ==================

async def adicionar_cargo(member, role_id):
    role = member.guild.get_role(role_id)
    if role and role not in member.roles:
        await member.add_roles(role)

async def remover_cargo(member, role_id):
    role = member.guild.get_role(role_id)
    if role and role in member.roles:
        await member.remove_roles(role)

# ================== INICIAR ==================

if not TOKEN:
    raise RuntimeError("DISCORD_TOKEN não definido")

bot.run(TOKEN)
