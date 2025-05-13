import discord
import json
import os
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ui import View, Button
from dotenv import load_dotenv
from discord import FFmpegPCMAudio
from discord import OptionChoice
from pytz import timezone, all_timezones
from datetime import datetime

bot = discord.Bot(intents=discord.Intents.default())
scheduler = AsyncIOScheduler()
alert_jobs = []  # 리스트 형태로 알림 저장 (딕셔너리)
allowed_role_map = {}  # 서버별 역할 제한 정보
CURRENT_TIMEZONE = "Asia/Seoul"

ALERTS_FILE = "alerts.json"
ROLES_FILE = "roles.json"

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡdefㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

def save_alerts():
    with open(ALERTS_FILE, "w", encoding="utf-8") as f:
        json.dump(alert_jobs, f, indent=2, ensure_ascii=False)

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_roles():
    with open(ROLES_FILE, "w") as f:
        json.dump(allowed_role_map, f)

def load_roles():
    global allowed_role_map
    if os.path.exists(ROLES_FILE):
        with open(ROLES_FILE, "r") as f:
            allowed_role_map = json.load(f)

def is_authorized(ctx: discord.ApplicationContext):
    role_id = allowed_role_map.get(str(ctx.guild.id))
    return role_id and any(role.id == int(role_id) for role in ctx.author.roles)
    
def get_mp3_choices():
    folder = "audio"
    return [
        (f.replace(".mp3", ""), f.replace(".mp3", ""))
        for f in os.listdir(folder)
        if f.endswith(".mp3")
    ]

def get_mp3_choices():
    folder = "audio"
    return [
        OptionChoice(name=f.replace(".mp3", ""), value=f.replace(".mp3", ""))
        for f in os.listdir(folder)
        if f.endswith(".mp3")
    ]

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡdefㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡclassㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

class 삭제버튼(Button):
    def __init__(self, label, index, ctx):
        super().__init__(label=label, style=discord.ButtonStyle.red, custom_id=str(index))
        self.index = index
        self.ctx = ctx

    async def callback(self, interaction: discord.Interaction):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("❌ 이 버튼은 당신이 사용할 수 없습니다.", ephemeral=True)
            return

        if 0 <= self.index < len(alert_jobs):
            deleted = alert_jobs.pop(self.index)
            save_alerts()
            await interaction.response.send_message(
                f"🗑️ `{deleted['trigger']} {deleted['message']}` 알림이 삭제되었습니다.",
                ephemeral=True
            )
            await interaction.message.delete()
        else:
            await interaction.response.send_message("❌ 유효하지 않은 알림입니다.", ephemeral=True)
            
class 알림삭제뷰(View):
    def __init__(self, ctx, jobs):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.jobs = jobs

        for i, job in enumerate(self.jobs):
            # 주기와 시간 분리 안전하게
            trigger_str = job["trigger"]
            시간 = trigger_str.split(" ")[-1]
            주기 = trigger_str.replace(시간, "").strip()

            label = f"{i+1}. {주기} {시간}"
            self.add_item(삭제버튼(label, i, ctx))

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡclassㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡstartㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

@bot.event
async def on_ready():
    await bot.sync_commands(force=True)

    if not scheduler.running:
        scheduler.start()

    load_roles()

    for alert in load_alerts():
        try:
            guild = bot.get_guild(alert["guild_id"])
            channel = guild.get_channel(alert["channel_id"])
            trigger_str = alert["trigger"]
            시간 = trigger_str.split(" ")[-1]
            주기 = trigger_str.replace(시간, "").strip()
            hour, minute = map(int, 시간.split(":"))

            if 주기 == "매일":
                trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone(CURRENT_TIMEZONE))
            elif 주기.startswith("매주"):
                day_map = {
                    "월요일": "mon", "화요일": "tue", "수요일": "wed",
                    "목요일": "thu", "금요일": "fri", "토요일": "sat", "일요일": "sun"
                }
                요일 = 주기.replace("매주 ", "")
                trigger = CronTrigger(day_of_week=day_map[요일], hour=hour, minute=minute, timezone=timezone(CURRENT_TIMEZONE))
            else:
                continue

            async def 작업(채널=channel, mention=alert["mention"], message=alert["message"]):
                mention_text = f"{mention} " if mention else ""
                await 채널.send(f"{mention_text}{message}")

            scheduler.add_job(작업, trigger)
            alert_jobs.append(alert)
        except Exception as e:
            print("❌ 알림 복원 실패:", e)
    print(f"{bot.user} 온라인, 동기화 & 알림/권한 복원 완료 ✅")

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡstartㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡcommandㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

@bot.slash_command(name="권한지정", description="알림 명령어를 사용할 역할을 지정합니다. (관리자 전용)")
async def 권한지정(ctx: discord.ApplicationContext, 역할: discord.Role):
    if not ctx.author.guild_permissions.administrator:
        await ctx.respond("❌ 이 명령어는 관리자만 사용할 수 있습니다.", ephemeral=True)
        return
    allowed_role_map[str(ctx.guild.id)] = 역할.id
    save_roles()
    await ctx.respond(f"✅ `{역할.name}` 역할에게 알림 명령어 사용 권한을 부여했습니다.")

@bot.slash_command(name="권한확인", description="누가 알림 명령어를 사용할 수 있는지 확인합니다.")
async def 권한확인(ctx: discord.ApplicationContext):
    role_id = allowed_role_map.get(str(ctx.guild.id))
    if role_id:
        역할 = ctx.guild.get_role(int(role_id))
        await ctx.respond(f"🔐 현재 알림 명령어 사용 가능 역할: `{역할.name}`")
    else:
        await ctx.respond("⚠️ 아직 사용 권한이 설정되지 않았습니다.")
        
@bot.slash_command(name="알림추가", description="테스트용 음성 알림 추가")
async def 알림추가(
    ctx: discord.ApplicationContext,

    시간: discord.Option(str, description="예: 23:59"),

    선택주기: discord.Option(str, description="주기를 선택하세요",
        choices=["매일"] + [f"매주 {d}" for d in ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]]
    ),

    채널: discord.Option(
        discord.VoiceChannel,
        description="알림을 재생할 음성 채널 선택",
        channel_types=[discord.ChannelType.voice]
    ),

    음성파일: discord.Option(
        str,
        description="재생할 mp3 파일 선택",
        choices=get_mp3_choices()
    ),

    주기: discord.Option(str, default="", description="직접 입력할 주기 (선택 안 했을 때만 사용)"),

    멘션: discord.Option(str, default="", description="멘션 대상 (@everyone 등)"),

    메시지: discord.Option(str, default="🔔 알림입니다!", description="알림 메시지")
):
    try:
        await ctx.defer(ephemeral=True)

        hour, minute = map(int, 시간.split(":"))
        최종주기 = 선택주기 or 주기

        if not 최종주기:
            await ctx.followup.send("❌ 주기를 입력하거나 선택해야 합니다.")
            return

        if 최종주기 == "매일":
            trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone(CURRENT_TIMEZONE))
        elif 최종주기.startswith("매주"):
            day_map = {
                "월요일": "mon", "화요일": "tue", "수요일": "wed",
                "목요일": "thu", "금요일": "fri", "토요일": "sat", "일요일": "sun"
            }
            요일 = 최종주기.replace("매주", "").strip()
            if 요일 not in day_map:
                await ctx.followup.send("형식이 잘못됐어요. '매일' 또는 '매주 요일'만 가능해요.")
                return
            trigger = CronTrigger(day_of_week=day_map[요일], hour=hour, minute=minute, timezone=timezone(CURRENT_TIMEZONE))
        else:
            await ctx.followup.send("형식이 잘못됐어요. '매일' 또는 '매주 요일'만 가능해요.")
            return

        # 예약 정보 저장
        guild_id = ctx.guild.id
        channel_id = 채널.id
        text_channel_id = ctx.channel.id

        # 알림 데이터 저장
        alert = {
            "guild_id": guild_id,
            "channel_id": channel_id,
            "trigger": f"{최종주기} {시간}",
            "mention": 멘션,
            "message": 메시지
        }
        alert_jobs.append(alert)
        save_alerts()

        # 작업 등록
        async def 작업():
            try:
                guild = bot.get_guild(guild_id)
                vc_channel = guild.get_channel(channel_id)
                text_channel = guild.get_channel(text_channel_id)

                mention_text = f"{멘션} " if 멘션 else ""
                await text_channel.send(f"{mention_text}{메시지}")

                if guild.voice_client and guild.voice_client.is_connected():
                    await guild.voice_client.disconnect()

                vc = await vc_channel.connect()

                audio_path = f"audio/{음성파일}.mp3"
                if os.path.exists(audio_path):
                    vc.play(discord.FFmpegPCMAudio(audio_path))
                    while vc.is_playing():
                        await asyncio.sleep(1)
                await vc.disconnect()

            except Exception as e:
                print(f"❌ 작업 중 오류: {e}")

        scheduler.add_job(작업, trigger)

        await ctx.followup.send(f"✅ 알림이 추가되었습니다: `{최종주기} {시간}` → {채널.name}\n🎵 음성파일: `{음성파일}.mp3`")

    except Exception as e:
        await ctx.followup.send(f"❌ 알림 추가 중 오류 발생: {e}")

@bot.slash_command(name="채널테스트", description="음성 채널 드롭다운 테스트")
async def 채널테스트(
    ctx: discord.ApplicationContext,
    채널: discord.Option(discord.VoiceChannel,
        description="음성 채널만 드롭다운에 표시됨",
        channel_types=[discord.ChannelType.voice],
        input_type=discord.VoiceChannel  # ✅ 이걸 추가하면 객체로 받아짐
    )
):
    await ctx.respond(f"✅ 선택한 채널: {채널.name} / ID: {채널.id}")
    
@bot.slash_command(name="보이스테스트", description="지정된 음성 채널에 봇이 접속합니다.")
async def 보이스테스트(
    ctx: discord.ApplicationContext,
    채널: discord.Option(
        discord.VoiceChannel,
        description="접속할 음성 채널",
        channel_types=[discord.ChannelType.voice]
    )
):
    try:
        await ctx.respond(f"🔄 `{채널.name}` 채널에 접속 시도 중...", ephemeral=True)

        if ctx.guild.voice_client and ctx.guild.voice_client.is_connected():
            await ctx.guild.voice_client.disconnect()

        print(f"🔊 채널 접속 시도: {채널.name}")
        vc = await 채널.connect()
        print("✅ 채널 연결 완료")
        await ctx.send(f"✅ 봇이 `{채널.name}` 음성 채널에 접속했습니다!")

    except Exception as e:
        print(f"❌ 음성 채널 연결 실패: {e}")
        await ctx.send(f"❌ 연결 실패: {e}")

# 알림목록 명령어
@bot.slash_command(name="알림목록", description="등록된 모든 알림을 확인합니다.")
async def 알림목록(ctx: discord.ApplicationContext):
    if not alert_jobs:
        await ctx.respond("⚠️ 현재 등록된 알림이 없습니다.")
        return

    embed = discord.Embed(title="📋 현재 알림 목록", color=discord.Color.blue())

    for i, job in enumerate(alert_jobs):
        trigger_str = job["trigger"]
        시간 = trigger_str.split(" ")[-1]
        주기 = trigger_str.replace(시간, "").strip()
        멘션 = job["mention"] if job["mention"] else "-"
        메시지 = job["message"]
        embed.add_field(
            name=f"{i+1}. {주기} {시간}",
            value=f"멘션: `{멘션}`\n메시지: `{메시지}`",
            inline=False
        )

    await ctx.respond(embed=embed)

# 알림삭제 명령어
@bot.slash_command(name="알림삭제", description="삭제할 알림을 선택합니다.")
async def 알림삭제(ctx: discord.ApplicationContext):
    if not alert_jobs:
        await ctx.respond("⚠️ 현재 등록된 알림이 없습니다.")
        return

    embed = discord.Embed(title="📋 삭제할 알림을 선택하세요", color=discord.Color.red())
    for i, job in enumerate(alert_jobs):
        trigger_str = job["trigger"]
        시간 = trigger_str.split(" ")[-1]
        주기 = trigger_str.replace(시간, "").strip()

        embed.add_field(
            name=f"{i+1}. {주기} {시간}",
            value=f"멘션: `{job['mention'] or '-'}`\n메시지: `{job['message']}`",
            inline=False
        )

    view = 알림삭제뷰(ctx, alert_jobs)
    await ctx.respond(embed=embed, view=view)

@bot.slash_command(name="알림초기화", description="등록된 모든 알림을 제거합니다.")
async def 알림초기화(ctx: discord.ApplicationContext):
    alert_jobs.clear()
    save_alerts()
    await ctx.respond("🗑️ 모든 알림이 제거되었습니다.")
    
@bot.slash_command(name="현재시간", description="현재 봇이 인식하고 있는 시간을 확인합니다.")
async def 현재시간(ctx: discord.ApplicationContext):
    now = datetime.now(timezone(CURRENT_TIMEZONE))
    await ctx.respond(f"🕒 현재 시간 ({CURRENT_TIMEZONE}): `{now.strftime('%Y-%m-%d %H:%M:%S')}`")

# 시간설정 명령어 (중복 없는 대표 시차 25개)
@bot.slash_command(name="시간설정", description="알림 스케줄에 사용할 기준 시간대를 설정합니다.")
async def 시간설정(
    ctx: discord.ApplicationContext,
    시간대: discord.Option(str, description="시간대를 선택하세요", choices=[
        "Asia/Seoul", "Etc/UTC", "Africa/Lagos", "Europe/Berlin", "Asia/Dubai", "Asia/Karachi", "Asia/Kolkata",
        "Asia/Dhaka", "Asia/Yangon", "Asia/Bangkok", "Asia/Shanghai", "Australia/Brisbane",
        "Pacific/Noumea", "Pacific/Auckland", "America/St_Johns", "America/Halifax", "America/New_York",
        "America/Chicago", "America/Denver", "America/Los_Angeles", "America/Anchorage", "Pacific/Honolulu",
        "Pacific/Pago_Pago", "Pacific/Kiritimati"
    ])
):
    global CURRENT_TIMEZONE
    CURRENT_TIMEZONE = 시간대
    await ctx.respond(f"✅ 시간대가 `{CURRENT_TIMEZONE}`(으)로 설정되었습니다.")


#ㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡcommandㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡㅡ#

bot.run(TOKEN)
