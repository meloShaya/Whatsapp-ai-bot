import os
import sys # Added for path modification
import logging
import google.generativeai as genai
from dotenv import load_dotenv
import shelve

# Handle relative imports when running directly
try:
    from app.utils.file_parser import load_knowledge_from_directory, load_and_extract_text # Added load_and_extract_text for prompt file
except ModuleNotFoundError:
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
    from app.utils.file_parser import load_knowledge_from_directory, load_and_extract_text # Added load_and_extract_text

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_ASSISTANT_INSTRUCTIONS_BASE = os.getenv("GEMINI_ASSISTANT_INSTRUCTIONS") # Fallback string instructions
GEMINI_SYSTEM_PROMPT_FILE_PATH = os.getenv("GEMINI_SYSTEM_PROMPT_FILE_PATH") # Path to prompt file
GEMINI_KNOWLEDGE_BASE_DIR_PATH = os.getenv("GEMINI_KNOWLEDGE_BASE_PATH") # Renamed for clarity
GEMINI_THREADS_DB = "gemini_threads_db"

# --- Load System Instructions from File or Fallback ---
system_instructions_from_file = ""
if GEMINI_SYSTEM_PROMPT_FILE_PATH:
    logging.info(f"Attempting to load system prompt from file: {GEMINI_SYSTEM_PROMPT_FILE_PATH}")
    # Use load_and_extract_text as it handles path resolution and basic text extraction
    system_instructions_from_file = load_and_extract_text(GEMINI_SYSTEM_PROMPT_FILE_PATH)
    if system_instructions_from_file:
        logging.info(f"Successfully loaded system prompt from file ({len(system_instructions_from_file)} chars).")
    else:
        logging.warning(f"Failed to load system prompt from file: {GEMINI_SYSTEM_PROMPT_FILE_PATH}. Will use GEMINI_ASSISTANT_INSTRUCTIONS_BASE if set.")

# Determine active system instructions
active_system_instructions = system_instructions_from_file if system_instructions_from_file else GEMINI_ASSISTANT_INSTRUCTIONS_BASE
if not active_system_instructions:
    logging.info("No system instructions provided (neither file nor direct string).")
# --- End Load System Instructions ---

# Load knowledge base content
KNOWLEDGE_BASE_CONTENT = load_knowledge_from_directory(GEMINI_KNOWLEDGE_BASE_DIR_PATH)

# Combine active system instructions with knowledge base preamble
final_system_instructions = active_system_instructions
if KNOWLEDGE_BASE_CONTENT:
    knowledge_preamble = "\n\nUse the following information from the knowledge base to answer user questions. Prioritize this information above all other knowledge:\n---\n" + KNOWLEDGE_BASE_CONTENT + "\n---"
    if final_system_instructions:
        final_system_instructions += knowledge_preamble
    else:
        # If there were no system instructions at all, the knowledge base becomes the primary instruction
        final_system_instructions = knowledge_preamble.strip() 

if not GEMINI_API_KEY:
    logging.warning("GEMINI_API_KEY not found in environment variables.")
else:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
    except Exception as e:
        logging.error(f"Failed to configure Gemini API: {e}")

# For simplicity, using a global model instance. Consider implications for concurrent requests.
# You might want to initialize the model inside the function if that's more appropriate for your setup.
model = None
if GEMINI_API_KEY:
    try:
        model = genai.GenerativeModel(
            model_name='models/gemini-2.0-flash-lite',
            system_instruction=final_system_instructions if final_system_instructions else None
            )
        if final_system_instructions:
            logging.info(f"Gemini model initialized with effective system instructions (len: {len(final_system_instructions)}). Preview: {final_system_instructions[:200]}...")
        else:
            logging.info("Gemini model initialized without specific system instructions.")
            
    except Exception as e:
        logging.error(f"Failed to initialize Gemini model: {e}")

# --- Thread Management Functions ---
def check_if_gemini_thread_exists(wa_id: str):
    """Retrieves conversation history for a given wa_id from shelve."""
    with shelve.open(GEMINI_THREADS_DB) as S_DB:
        return S_DB.get(wa_id, None)

def store_gemini_thread(wa_id: str, history):
    """Stores conversation history for a given wa_id into shelve."""
    with shelve.open(GEMINI_THREADS_DB, writeback=True) as S_DB:
        S_DB[wa_id] = history
# --- End Thread Management Functions ---

def generate_ai_response(prompt: str, wa_id: str, name: str) -> str:
    """
    Generates a response from the Google Gemini API, maintaining conversation history.
    """
    if not GEMINI_API_KEY:
        logging.error("Gemini API key not configured.")
        return "Error: Gemini API key not configured."
    if not model:
        logging.error("Gemini model not initialized.")
        return "Error: Gemini model not initialized."

    logging.info(f"Received message from {name} ({wa_id}): {prompt}")

    try:
        # Retrieve existing conversation history
        existing_history = check_if_gemini_thread_exists(wa_id)
        
        # Start a chat session. If history exists, it's loaded. Otherwise, a new chat starts.
        # Gemini's chat.history will automatically be a list of genai.types.Content objects
        chat = model.start_chat(history=existing_history or [])
        
        response = chat.send_message(prompt)

        # Store the updated history (which now includes the user's prompt and AI's response)
        store_gemini_thread(wa_id, chat.history)

        if response.candidates and response.candidates[0].content.parts:
            response_text = response.candidates[0].content.parts[0].text
            logging.info(f"Gemini response for {name} ({wa_id}): {response_text}")
            return response_text
        else:
            logging.warning(f"Unexpected Gemini API response structure for {name} ({wa_id}): {response}")
            return "Sorry, I couldn't process that response from Gemini."
    except Exception as e:
        logging.error(f"Error generating response from Gemini for {name} ({wa_id}): {e}")
        # It might be good to clear the history for this user if it's corrupted,
        # or handle specific errors like quota issues differently.
        # For now, just return a generic error.
        # store_gemini_thread(wa_id, []) # Optionally clear history on error
        return f"Error communicating with Gemini: {e}"

if __name__ == '__main__':
    # Example usage (for testing purposes)
    # Ensure GEMINI_API_KEY is set in your .env file
    if not (GEMINI_API_KEY and model):
        print("Gemini API key not set or model not initialized. Skipping example usage.")
    else:
        test_wa_id = "test_user_123"
        test_name = "Test User"

        print(f"--- Test 1: First message for {test_name} ---")
        prompt1 = "Hello Gemini, what's the capital of France?"
        response1 = generate_ai_response(prompt1, test_wa_id, test_name)
        print(f"Prompt: {prompt1}")
        print(f"Response: {response1}")

        print(f"\n--- Test 2: Follow-up message for {test_name} (should have context) ---")
        prompt2 = "And what is its population?"
        response2 = generate_ai_response(prompt2, test_wa_id, test_name)
        print(f"Prompt: {prompt2}")
        print(f"Response: {response2}")
        
        print(f"\n--- Test 3: Clearing history for {test_name} (simulating new session) ---")
        store_gemini_thread(test_wa_id, []) # Clear history
        prompt3 = "What is its population?" # Same as prompt2, but context should be lost
        response3 = generate_ai_response(prompt3, test_wa_id, test_name)
        print(f"Prompt: {prompt3}")
        print(f"Response: {response3}")

        # Clean up the test database entry
        with shelve.open(GEMINI_THREADS_DB) as S_DB:
            if test_wa_id in S_DB:
                del S_DB[test_wa_id]
        print(f"\nCleaned up test data for {test_wa_id}.")

    if GEMINI_API_KEY:
        print("Listing available Gemini models...")
        try:
            for m in genai.list_models():
                # Check if 'generateContent' is a supported method for the model
                if 'generateContent' in m.supported_generation_methods:
                    print(f"Model name: {m.name} - Display name: {m.display_name}")
        except Exception as e:
            print(f"Could not list models: {e}")

    if GEMINI_API_KEY and model:
        test_prompt = "Hello, Gemini! How are you today?"
        print(f"Sending prompt to Gemini: {test_prompt}")
        response = generate_ai_response(test_prompt, "test_user_123", "Test User")
        print(f"Gemini response: {response}")
    else:
        print("Gemini API key not set or model not initialized. Skipping example usage.") 