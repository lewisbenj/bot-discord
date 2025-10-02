import discord
import requests
import json
import asyncio

# --- CẤU HÌNH ---
# THAY THẾ bằng Token Bot Discord của bạn
DISCORD_TOKEN = "YOUR_DISCORD_BOT_TOKEN_HERE" 
# THAY THẾ bằng API Key Gemini của bạn. (LƯU Ý: Nếu chạy trong môi trường Canvas, hãy để trống)
GEMINI_API_KEY = "" 

# Model API Endpoint
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={GEMINI_API_KEY}"
BOT_PREFIX = "!ai"

# Cấu hình Discord Intents (cần thiết cho các phiên bản discord.py mới)
intents = discord.Intents.default()
intents.message_content = True # BẬT để bot có thể đọc nội dung tin nhắn

# Khởi tạo client Discord
client = discord.Client(intents=intents)

# --- CHỨC NĂNG GỌI API GEMINI ---
async def generate_response_from_gemini(prompt: str) -> str:
    """
    Gửi prompt đến Gemini API và nhận lại câu trả lời.
    Sử dụng systemInstruction để hướng dẫn hành vi của bot.
    """
    
    # Định nghĩa persona và hướng dẫn cho AI
    system_prompt = (
        "Bạn là một Trợ lý AI đa năng và thân thiện. Hãy phân tích tin nhắn của người dùng "
        "(kể cả những câu hỏi phức tạp hoặc yêu cầu viết lách sáng tạo) và đưa ra câu trả lời "
        "chi tiết, hữu ích bằng tiếng Việt. Giữ giọng điệu chuyên nghiệp và hỗ trợ."
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
    }

    try:
        # Sử dụng requests để gọi API (cần chạy trong thread khác nếu không phải async framework)
        # Đối với một bot Discord, chúng ta cần chạy yêu cầu này một cách không đồng bộ
        
        # Hàm wrapper cho requests.post
        def fetch_api():
            headers = {'Content-Type': 'application/json'}
            # Thử nghiệm với Exponential Backoff (1s, 2s, 4s)
            for i in range(3):
                try:
                    response = requests.post(API_URL, headers=headers, data=json.dumps(payload), timeout=15)
                    response.raise_for_status() # Kiểm tra lỗi HTTP
                    return response.json()
                except requests.exceptions.HTTPError as e:
                    if response.status_code in [429, 500, 503] and i < 2:
                        delay = 2 ** i
                        print(f"Lỗi API ({response.status_code}). Thử lại sau {delay} giây...")
                        asyncio.sleep(delay)
                    else:
                        raise e
                except requests.exceptions.RequestException as e:
                    raise e
            return None

        # Chạy yêu cầu đồng bộ trong executor của asyncio
        response_json = await client.loop.run_in_executor(None, fetch_api)

        # Xử lý phản hồi JSON
        if response_json and 'candidates' in response_json:
            text = response_json['candidates'][0]['content']['parts'][0]['text']
            return text
        else:
            return "Xin lỗi, tôi không thể tạo ra câu trả lời. Phản hồi API không hợp lệ."

    except Exception as e:
        print(f"LỖI KHI GỌI GEMINI API: {e}")
        return f"Rất tiếc, đã xảy ra lỗi trong quá trình xử lý: {e}"

# --- XỬ LÝ SỰ KIỆN DISCORD ---

@client.event
async def on_ready():
    """Xử lý khi Bot đã sẵn sàng và kết nối thành công."""
    print('-------------------------------------------')
    print(f'Bot {client.user} đã đăng nhập và sẵn sàng!')
    print('-------------------------------------------')
    # Thiết lập trạng thái bot
    await client.change_presence(activity=discord.Game(name=f"Sử dụng {BOT_PREFIX} [câu hỏi]"))

@client.event
async def on_message(message):
    """Xử lý khi có tin nhắn mới."""
    
    # 1. Bỏ qua tin nhắn của chính bot
    if message.author == client.user:
        return

    # 2. Kiểm tra prefix để kích hoạt bot
    if message.content.startswith(BOT_PREFIX):
        # Trích xuất câu hỏi sau prefix
        user_prompt = message.content[len(BOT_PREFIX):].strip()
        
        if not user_prompt:
            await message.channel.send(f"Bạn cần cung cấp câu hỏi sau lệnh `{BOT_PREFIX}`.")
            return

        # Gửi thông báo đang xử lý
        async with message.channel.typing():
            # 3. Gọi API Gemini để xử lý câu hỏi phức tạp
            print(f"Đang xử lý câu hỏi từ {message.author}: {user_prompt}")
            ai_response = await generate_response_from_gemini(user_prompt)
            
            # 4. Gửi kết quả trở lại kênh
            # Sử dụng Embed để trình bày đẹp hơn
            embed = discord.Embed(
                title=f"Phản hồi AI cho {message.author.display_name}",
                description=ai_response,
                color=discord.Color.blue()
            )
            embed.set_footer(text="Được cung cấp bởi Gemini AI")
            
            await message.channel.send(embed=embed)
    
    # Có thể thêm logic phản hồi tin nhắn phức tạp khác, ví dụ: nếu bot được tag (@bot)

# --- KHỞI CHẠY BOT ---
try:
    client.run(DISCORD_TOKEN)
except discord.LoginFailure:
    print("LỖI: Token Discord không hợp lệ hoặc thiếu. Vui lòng kiểm tra lại DISCORD_TOKEN.")
except Exception as e:
    print(f"Đã xảy ra lỗi khi chạy bot: {e}")
