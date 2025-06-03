import os
import sys # Added for path modification
import logging
from openai import OpenAI # Use OpenAI library as DeepSeek is compatible
from dotenv import load_dotenv
import shelve # Added

# Handle relative imports when running directly
try:
    from app.utils.file_parser import load_knowledge_from_directory # Updated import
except ModuleNotFoundError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from app.utils.file_parser import load_knowledge_from_directory # Updated import

load_dotenv()

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_KNOWLEDGE_BASE_DIR_PATH = os.getenv("DEEPSEEK_KNOWLEDGE_BASE_PATH") # Renamed for clarity
DEEPSEEK_API_BASE_URL = "https://api.deepseek.com/v1" # Standard DeepSeek API endpoint
DEEPSEEK_THREADS_DB = "deepseek_threads_db" # Added for shelve db name

# Load knowledge base content once at startup using the new directory function
KNOWLEDGE_BASE_CONTENT = load_knowledge_from_directory(DEEPSEEK_KNOWLEDGE_BASE_DIR_PATH)
if KNOWLEDGE_BASE_CONTENT:
    logging.info(f"DeepSeek knowledge base loaded ({len(KNOWLEDGE_BASE_CONTENT)} chars). It will be prepended to new conversations.") # Updated log

client = None
if DEEPSEEK_API_KEY:
    try:
        client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_API_BASE_URL)
    except Exception as e:
        logging.error(f"Failed to initialize DeepSeek client: {e}")
else:
    logging.warning("DEEPSEEK_API_KEY not found in environment variables.")

# --- Thread Management Functions ---
def check_if_deepseek_thread_exists(wa_id: str):
    """Retrieves message history for a given wa_id from shelve."""
    with shelve.open(DEEPSEEK_THREADS_DB) as S_DB:
        return S_DB.get(wa_id, []) # Return empty list if no history

def store_deepseek_thread(wa_id: str, history: list):
    """Stores message history for a given wa_id into shelve."""
    with shelve.open(DEEPSEEK_THREADS_DB, writeback=True) as S_DB:
        S_DB[wa_id] = history
# --- End Thread Management Functions ---

def generate_ai_response(prompt: str, wa_id: str, name: str, model_name: str = "deepseek-chat") -> str:
    """
    Generates a response from the DeepSeek API, maintaining conversation history
    and prepending a global knowledge base if available.
    """
    if not client:
        logging.error("DeepSeek client not initialized. Check API key.")
        return "Error: DeepSeek client not initialized."

    logging.info(f"Received message from {name} ({wa_id}) for DeepSeek: {prompt}")

    try:
        messages_history = check_if_deepseek_thread_exists(wa_id)

        # If it's a new conversation (no history) and we have knowledge base content, prepend it.
        # We prepend it as a system message for context.
        # Note: For ongoing chats, the KB is not re-added to avoid redundancy and save tokens,
        # assuming the initial context is sufficient for the session.
        # A more sophisticated approach might re-inject relevant KB parts if needed later.
        if not messages_history and KNOWLEDGE_BASE_CONTENT:
            messages_history.append({"role": "system", "content": "You are an AI assistant. Use the following knowledge base to answer questions. Prioritize this information.\n---BEGIN KNOWLEDGE BASE---\n" + KNOWLEDGE_BASE_CONTENT + "\n---END KNOWLEDGE BASE---"})
        
        messages_history.append({"role": "user", "content": prompt})
        
        chat_completion = client.chat.completions.create(
            messages=messages_history,
            model=model_name,
        )
        
        if chat_completion.choices and chat_completion.choices[0].message and chat_completion.choices[0].message.content:
            ai_response_content = chat_completion.choices[0].message.content
            messages_history.append({"role": "assistant", "content": ai_response_content})
            store_deepseek_thread(wa_id, messages_history)
            logging.info(f"DeepSeek response for {name} ({wa_id}): {ai_response_content}")
            return ai_response_content
        else:
            logging.warning(f"Unexpected DeepSeek API response structure for {name} ({wa_id}): {chat_completion}")
            messages_history.pop() # Remove the user message we just added
            # Don't store system message if it was the only one and failed.
            if len(messages_history) == 1 and messages_history[0]["role"] == "system":
                 store_deepseek_thread(wa_id, []) # Clear history if only system message led to error
            else:
                store_deepseek_thread(wa_id, messages_history)
            return "Sorry, I couldn't process that response from DeepSeek."
    except Exception as e:
        logging.error(f"Error generating response from DeepSeek for {name} ({wa_id}): {e}")
        return f"Error communicating with DeepSeek: {e}"

if __name__ == '__main__':
    if not (DEEPSEEK_API_KEY and client):
        print("DeepSeek API key not set or client not initialized. Skipping example usage.")
    else:
        test_wa_id = "test_user_ds_456"
        test_name = "DeepSeek TestUser"

        print(f"--- DeepSeek Test 1: First message for {test_name} ---")
        prompt1 = "Hi DeepSeek, can you explain what a language model is in simple terms?"
        response1 = generate_ai_response(prompt1, test_wa_id, test_name)
        print(f"Prompt: {prompt1}")
        print(f"Response: {response1}")

        print(f"\n--- DeepSeek Test 2: Follow-up for {test_name} (should have context) ---")
        prompt2 = "And how is it different from a traditional computer program?"
        response2 = generate_ai_response(prompt2, test_wa_id, test_name)
        print(f"Prompt: {prompt2}")
        print(f"Response: {response2}")

        print(f"\n--- DeepSeek Test 3: Clearing history for {test_name} ---")
        store_deepseek_thread(test_wa_id, []) # Clear history
        prompt3 = "How is it different from a traditional computer program?" # Same as prompt2
        response3 = generate_ai_response(prompt3, test_wa_id, test_name)
        print(f"Prompt: {prompt3}")
        print(f"Response: {response3}")

        # Clean up
        with shelve.open(DEEPSEEK_THREADS_DB) as S_DB:
            if test_wa_id in S_DB:
                del S_DB[test_wa_id]
        print(f"\nCleaned up DeepSeek test data for {test_wa_id}.") 