import disnake, asyncio, json, random, sqlite3, os, httpx, sys, string, aiohttp
from disnake.ext import commands
from disnake.ui import View, Button, Modal, TextInput
from disnake.enums import TextInputStyle
from datetime import datetime, timedelta, timezone

intents = disnake.Intents.default()
intents.message_content = True

# config.json 불러오기
try:
    with open("jsons/config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    print("⚠️ config.json 파일을 찾을 수 없습니다.")
    sys.exit(1)

adminid = int(config["AdminRole"])
logch = config["logch"]

VOICE_MAP = {
    "혜련": "4-3-13",
    "유미": "1-3-13",
    "줄리": "3-3-1",
    "서연": "Seoyeon",
    "효수": "ko-KR-Standard-A",
}

def setup(bot):
    @bot.slash_command(name="tts생성", description="tts를 생성합니다.")
    async def tts생성(
        interaction: disnake.ApplicationCommandInteraction,
        voice: str = commands.Param(
            name="voice",
            description="TTS 음성을 선택하세요",
            choices=list(VOICE_MAP.keys())
        ),
        text: str = commands.Param(
            name="text",
            description="읽을 문장(텍스트)을 입력하세요"
        )
    ):
        await interaction.response.defer()

        user: disnake.Member = interaction.author
        role = interaction.guild.get_role(adminid)

        # 관리자 역할 확인
        if role is None:
            await interaction.followup.send(
                embed=disnake.Embed(
                    title="**⚠️ 오류 발생**",
                    description="config.json에 설정된 관리자 역할 ID를 서버에서 찾을 수 없습니다.",
                    color=0xff4040
                ),
                ephemeral=True
            )
            return

        if role not in user.roles:
            await interaction.followup.send(
                embed=disnake.Embed(
                    title="**<:banned_1162727777523478548:1400072243525976146> | 권한 부족**",
                    description="이 명령어를 사용할 권한이 없습니다. 관리자 역할이 필요합니다.",
                    color=0xff4040
                ),
                ephemeral=True
            )
            return

        if not text:
            return await interaction.followup.send(
                embed=disnake.Embed(
                    title="**<:banned_1162727777523478548:1400072243525976146> | 오류 발생**",
                    description="읽을 문장을 입력해주세요.",
                    color=0xff4040
                )
            )
            # return await interaction.followup.send("🗣️ 읽을 문장을 입력해주세요!\n예시: `!tts 안녕하세요`")

        # 선택된 보이스 ID 결정
        voice_id = VOICE_MAP.get(voice)
        if not voice_id:
            await interaction.followup.send("❌ 지원하지 않는 보이스입니다.", ephemeral=True)
            return

        # Lazypy TTS 요청
        
        async with aiohttp.ClientSession() as session:
                
                payload = {
                    "service": "Oddcast" if voice in ("혜련", "유미", "줄리") else "StreamElements",   # TTS 엔진
                    "voice": voice_id,      # 선택한 보이스
                    "text": text
                }
                async with session.post("https://lazypy.ro/tts/request_tts.php", data=payload) as resp:
                    # API가 JSON 응답을 보장하지 않는 경우 대비
                    try:
                        data = await resp.json()
                    except Exception:
                        raw = await resp.text()
                        #return await interaction.followup.send(f"❌ TTS 생성 실패 (응답 파싱 오류)\n```{raw[:400]}```")
                        return await interaction.followup.send(
                            embed=disnake.Embed(
                                title="**<:banned_1162727777523478548:1400072243525976146> | 오류 발생**",
                                description=(
                                    f"TTS를 생성하지 못했습니다. ( 응답 파싱 오류 )\n\n"
                                    f"오류 상세 설명:\n{data.get(raw[:400])}"
                                ),
                                color=0xff4040
                            )
                        )

        # 응답 검사
        if not data.get("success"):
                return await interaction.followup.send(
                    embed=disnake.Embed(
                        title="**<:banned_1162727777523478548:1400072243525976146> | 오류 발생**",
                        description=(
                            f"TTS를 생성하지 못했습니다.\n\n"
                            f"오류 상세 설명:\n{data.get('error_msg')}"
                        ),
                        color=0xff4040
                    )
                )
            # return await interaction.followup.send(f"❌ TTS 생성 실패: {data.get('error_msg', 'Unknown error')}")

        audio_url = data["audio_url"]
        filename = "tts_output.mp3"

        # MP3 다운로드
        async with aiohttp.ClientSession() as session:
            async with session.get(audio_url) as resp:
                if resp.status == 200:
                    with open(filename, "wb") as f:
                        f.write(await resp.read())
                else:
                    return await interaction.followup.send("❌ MP3 파일 다운로드 실패")

        # 채팅에 mp3 파일 업로드
        """await interaction.followup.send(
            f"✅ **TTS 변환 완료!**\n🗨️ `{text}`",
            file=disnake.File(filename)
        )"""

        await interaction.followup.send(
            embed=disnake.Embed(
                title="**<:CHECK_1141002471297253538:1400072262765514854> | TTS 생성 완료**",
                description=(
                    f"TTS 생성이 완료되었습니다.\n"
                    f"TTS 상세정보:\n\n"
                    f"보이스 엔진 : `{voice}`\n"
                    f"텍스트 : `{text}`\n"
                ),
                color=0x59ff85
            ),
            file=disnake.File(filename)
        )

        # 임시파일 삭제
        os.remove(filename)
