import asyncio
from spoon_ai.chat import ChatBot

async def main():
    bot = ChatBot(llm_provider="anthropic", model_name="claude-haiku-4-5-20251001")
    resp = await bot.ask(
        [{"role": "user", "content": "Say hello from DeepSeek."}]
    )
    print(resp)


if __name__ == "__main__":
    asyncio.run(main())
