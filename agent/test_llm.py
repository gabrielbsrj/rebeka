import asyncio
import litellm
import traceback

async def main():
    print("Testing LiteLLM Ollama Connection...")
    litellm.set_verbose = True
    try:
        response = litellm.completion(
            model="ollama/qwen3.5:9b",
            messages=[{"role": "user", "content": "Ping"}],
            api_base="http://localhost:11434"
        )
        print("Response:", response.choices[0].message.content)
    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
