# Build AI WhatsApp Bots with Pure Python

This guide will walk you through the process of creating a WhatsApp bot using the Meta (formerly Facebook) Cloud API with pure Python, and Flask particular. We'll also integrate webhook events to receive messages in real-time and use OpenAI to generate AI responses. For more information on the structure of the Flask application, you can refer to [this documentation](https://github.com/daveebbelaar/python-whatsapp-bot/tree/main/app).

## Prerequisites

1. A Meta developer account — If you don't have one, you can [create a Meta developer account here](https://developers.facebook.com/).
2. A business app — If you don't have one, you can [learn to create a business app here](https://developers.facebook.com/docs/development/create-an-app/). If you don't see an option to create a business app, select **Other** > **Next** > **Business**.
3. Familiarity with Python to follow the tutorial.

## Table of Contents

-   [Build AI WhatsApp Bots with Pure Python](#build-ai-whatsapp-bots-with-pure-python)
    -   [Prerequisites](#prerequisites)
    -   [Table of Contents](#table-of-contents)
    -   [Get Started](#get-started)
    -   [Step 1: Select Phone Numbers](#step-1-select-phone-numbers)
    -   [Step 2: Send Messages with the API](#step-2-send-messages-with-the-api)
    -   [Step 3: Configure Webhooks to Receive Messages](#step-3-configure-webhooks-to-receive-messages)
        -   [Start your app](#start-your-app)
        -   [Launch ngrok](#launch-ngrok)
        -   [Integrate WhatsApp](#integrate-whatsapp)
        -   [Testing the Integration](#testing-the-integration)
    -   [Step 4: Understanding Webhook Security](#step-4-understanding-webhook-security)
        -   [Verification Requests](#verification-requests)
        -   [Validating Verification Requests](#validating-verification-requests)
        -   [Validating Payloads](#validating-payloads)
    -   [Step 5: Learn about the API and Build Your App](#step-5-learn-about-the-api-and-build-your-app)
    -   [Step 6: Integrate AI into the Application](#step-6-integrate-ai-into-the-application)
    -   [Step 7: Add a Phone Number](#step-7-add-a-phone-number)
    -   [Datalumina](#datalumina)
    -   [Tutorials](#tutorials)

## Get Started

1. **Overview & Setup**: Begin your journey [here](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started).
2. **Locate Your Bots**: Your bots can be found [here](https://developers.facebook.com/apps/).
3. **WhatsApp API Documentation**: Familiarize yourself with the [official documentation](https://developers.facebook.com/docs/whatsapp).
4. **Helpful Guide**: Here's a [Python-based guide](https://developers.facebook.com/blog/post/2022/10/24/sending-messages-with-whatsapp-in-your-python-applications/) for sending messages.
5. **API Docs for Sending Messages**: Check out [this documentation](https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-messages).

## Step 1: Select Phone Numbers

-   Make sure WhatsApp is added to your App.
-   You begin with a test number that you can use to send messages to up to 5 numbers.
-   Go to API Setup and locate the test number from which you will be sending messages.
-   Here, you can also add numbers to send messages to. Enter your **own WhatsApp number**.
-   You will receive a code on your phone via WhatsApp to verify your number.

## Step 2: Send Messages with the API

1. Obtain a 24-hour access token from the API access section.
2. It will show an example of how to send messages using a `curl` command which can be send from the terminal or with a tool like Postman.
3. Let's convert that into a [Python function with the request library](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/start/whatsapp_quickstart.py).
4. Create a `.env` files based on `example.env` and update the required variables. [Video example here](https://www.youtube.com/watch?v=sOwG0bw0RNU).
5. You will receive a "Hello World" message (Expect a 60-120 second delay for the message).

Creating an access that works longer then 24 hours

1. Create a [system user at the Meta Business account level](https://business.facebook.com/settings/system-users).
2. On the System Users page, configure the assets for your System User, assigning your WhatsApp app with full control. Don't forget to click the Save Changes button.
    - [See step 1 here](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/img/meta-business-system-user-token.png)
    - [See step 2 here](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/img/adding-assets-to-system-user.png)
3. Now click `Generate new token` and select the app, and then choose how long the access token will be valid. You can choose 60 days or never expire.
4. Select all the permissions, as I was running into errors when I only selected the WhatsApp ones.
5. Confirm and copy the access token.

Now we have to find the following information on the **App Dashboard**:

-   **APP_ID**: "<YOUR-WHATSAPP-BUSINESS-APP_ID>" (Found at App Dashboard)
-   **APP_SECRET**: "<YOUR-WHATSAPP-BUSINESS-APP_SECRET>" (Found at App Dashboard)
-   **RECIPIENT_WAID**: "<YOUR-RECIPIENT-TEST-PHONE-NUMBER>" (This is your WhatsApp ID, i.e., phone number. Make sure it is added to the account as shown in the example test message.)
-   **VERSION**: "v18.0" (The latest version of the Meta Graph API)
-   **ACCESS_TOKEN**: "<YOUR-SYSTEM-USER-ACCESS-TOKEN>" (Created in the previous step)

Add these to your `.env` file:

-   **AI_PROVIDER**: "openai" (The AI provider to use. Options: "openai", "gemini", "deepseek". Defaults to "openai" if not set.)
-   **GEMINI_API_KEY**: "<YOUR-GEMINI-API-KEY>" (Your API key for Google Gemini, required if AI_PROVIDER is "gemini")
-   **DEEPSEEK_API_KEY**: "<YOUR-DEEPSEEK-API-KEY>" (Your API key for DeepSeek, required if AI_PROVIDER is "deepseek")
-   **GEMINI_ASSISTANT_INSTRUCTIONS**: "You are a helpful assistant." (Optional: System instructions for the Gemini model, used if AI_PROVIDER is "gemini")
-   **GEMINI_SYSTEM_PROMPT_FILE_PATH**: "data/gemini_system_prompt.txt" (Optional: Path to a .txt file containing detailed system instructions for Gemini. If set, this overrides `GEMINI_ASSISTANT_INSTRUCTIONS`.)
-   **GEMINI_KNOWLEDGE_BASE_PATH**: "data/gemini_knowledge_dir/" (Optional: Path to a DIRECTORY containing knowledge base files (e.g., .txt, .pdf, .docx, .xlsx) for Gemini. Relative to the project root.)
-   **DEEPSEEK_KNOWLEDGE_BASE_PATH**: "data/deepseek_knowledge_dir/" (Optional: Path to a DIRECTORY containing knowledge base files (e.g., .txt, .pdf, .docx, .xlsx) for DeepSeek. Relative to the project root.)

> You can only send a template type message as your first message to a user. That's why you have to send a reply first before we continue. Took me 2 hours to figure this out.

## Step 3: Configure Webhooks to Receive Messages

> Please note, this is the hardest part of this tutorial.

#### Start your app

-   Make you have a python installation or environment and install the requirements: `pip install -r requirements.txt`
-   Run your Flask app locally by executing [run.py](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/run.py)

#### Launch ngrok

The steps below are taken from the [ngrok documentation](https://ngrok.com/docs/integrations/whatsapp/webhooks/).

> You need a static ngrok domain because Meta validates your ngrok domain and certificate!

Once your app is running successfully on localhost, let's get it on the internet securely using ngrok!

1. If you're not an ngrok user yet, just sign up for ngrok for free.
2. Download the ngrok agent.
3. Go to the ngrok dashboard, click Your [Authtoken](https://dashboard.ngrok.com/get-started/your-authtoken), and copy your Authtoken.
4. Follow the instructions to authenticate your ngrok agent. You only have to do this once.
5. On the left menu, expand Cloud Edge and then click Domains.
6. On the Domains page, click + Create Domain or + New Domain. (here everyone can start with [one free domain](https://ngrok.com/blog-post/free-static-domains-ngrok-users))
7. Start ngrok by running the following command in a terminal on your local desktop:

```
ngrok http 8000 --domain your-domain.ngrok-free.app

```

8. ngrok will display a URL where your localhost application is exposed to the internet (copy this URL for use with Meta).

#### Integrate WhatsApp

In the Meta App Dashboard, go to WhatsApp > Configuration, then click the Edit button.

1. In the Edit webhook's callback URL popup, enter the URL provided by the ngrok agent to expose your application to the internet in the Callback URL field, with /webhook at the end (i.e. https://myexample.ngrok-free.app/webhook).
2. Enter a verification token. This string is set up by you when you create your webhook endpoint. You can pick any string you like. Make sure to update this in your `VERIFY_TOKEN` environment variable.
3. After you add a webhook to WhatsApp, WhatsApp will submit a validation post request to your application through ngrok. Confirm your localhost app receives the validation get request and logs `WEBHOOK_VERIFIED` in the terminal.
4. Back to the Configuration page, click Manage.
5. On the Webhook fields popup, click Subscribe to the **messages** field. Tip: You can subscribe to multiple fields.
6. If your Flask app and ngrok are running, you can click on "Test" next to messages to test the subscription. You recieve a test message in upper case. If that is the case, your webhook is set up correctly.

#### Testing the Integration

Use the phone number associated to your WhatsApp product or use the test number you copied before.

1. Add this number to your WhatsApp app contacts and then send a message to this number.
2. Confirm your localhost app receives a message and logs both headers and body in the terminal.
3. Test if the bot replies back to you in upper case.
4. You have now succesfully integrated the bot! 🎉
5. Now it's time to acutally build cool things with this.

## Step 4: Understanding Webhook Security

Below is some information from the Meta Webhooks API docs about verification and security. It is already implemented in the code, but you can reference it to get a better understanding of what's going on in [security.py](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/app/decorators/security.py)

#### Verification Requests

[Source](https://developers.facebook.com/docs/graph-api/webhooks/getting-started#:~:text=process%20these%20requests.-,Verification%20Requests,-Anytime%20you%20configure)

Anytime you configure the Webhooks product in your App Dashboard, we'll send a GET request to your endpoint URL. Verification requests include the following query string parameters, appended to the end of your endpoint URL. They will look something like this:

```
GET https://www.your-clever-domain-name.com/webhook?
  hub.mode=subscribe&
  hub.challenge=1158201444&
  hub.verify_token=meatyhamhock
```

The verify_token, `meatyhamhock` in the case of this example, is a string that you can pick. It doesn't matter what it is as long as you store in the `VERIFY_TOKEN` environment variable.

#### Validating Verification Requests

[Source](https://developers.facebook.com/docs/graph-api/webhooks/getting-started#:~:text=Validating%20Verification%20Requests)

Whenever your endpoint receives a verification request, it must:

-   Verify that the hub.verify_token value matches the string you set in the Verify Token field when you configure the Webhooks product in your App Dashboard (you haven't set up this token string yet).
-   Respond with the hub.challenge value.

#### Validating Payloads

[Source](https://developers.facebook.com/docs/graph-api/webhooks/getting-started#:~:text=int-,Validating%20Payloads,-We%20sign%20all)

WhatsApp signs all Event Notification payloads with a SHA256 signature and include the signature in the request's X-Hub-Signature-256 header, preceded with sha256=. You don't have to validate the payload, but you should.

To validate the payload:

-   Generate a SHA256 signature using the payload and your app's App Secret.
-   Compare your signature to the signature in the X-Hub-Signature-256 header (everything after sha256=). If the signatures match, the payload is genuine.

## Step 5: Learn about the API and Build Your App

Review the developer documentation to learn how to build your app and start sending messages. [See documentation](https://developers.facebook.com/docs/whatsapp/cloud-api).

## Step 6: Integrate AI into the Application

Now that we have an end-to-end connection, we can make the bot more intelligent. The core logic for choosing an AI provider and generating a response is in `app/utils/whatsapp_utils.py` within the `generate_response()` function. This function uses the `AI_PROVIDER` environment variable to delegate to the appropriate service in `app/services/`.

**General Steps for AI Integration:**

1.  **Choose your AI Provider:** Set the `AI_PROVIDER` environment variable in your `.env` file to "openai", "gemini", or "deepseek".
2.  **Configure API Keys:** Ensure the relevant API key (`OPENAI_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`) is correctly set in your `.env` file.
3.  **Provide Instructions/Persona (if applicable):**
    -   **OpenAI:**
        -   Create an Assistant in the OpenAI platform and get its ID.
        -   Set `OPENAI_ASSISTANT_ID` in your `.env` file.
        -   You can provide instructions and enable tools like Retrieval directly in the OpenAI Assistant configuration.
        -   The `app/services/openai_service.py` uses this Assistant ID to interact with your pre-configured assistant.
    -   **Gemini:**
        -   Set the `GEMINI_ASSISTANT_INSTRUCTIONS` environment variable in your `.env` file (e.g., "You are a helpful geography expert."). This serves as a fallback if `GEMINI_SYSTEM_PROMPT_FILE_PATH` is not set or the file is not found.
        -   Alternatively, for longer or more complex system prompts, set `GEMINI_SYSTEM_PROMPT_FILE_PATH` in your `.env` file to point to a text file (e.g., `data/gemini_system_prompt.txt`). The content of this file will be used as the primary system instruction.
        -   These instructions (from file or string) are passed as `system_instruction` when initializing the Gemini model in `app/services/gemini_service.py`, guiding its behavior for all conversations. The knowledge base from `GEMINI_KNOWLEDGE_BASE_PATH` is then appended to these system instructions.
    -   **DeepSeek:**
        -   Currently, `deepseek_service.py` does not have explicit system-level instruction support like Gemini or OpenAI Assistants. Persona and instructions would need to be prepended to the conversation history manually within the service if desired (this is not yet implemented).
        -   However, you can provide a knowledge base file via `DEEPSEEK_KNOWLEDGE_BASE_PATH`. Its content will be added to the start of the conversation with DeepSeek.
        *   This path should now point to a directory. All supported files within this directory will be loaded and concatenated.
4.  **Customize AI Service Logic (Optional):**
    -   You can modify the respective service files (`openai_service.py`, `gemini_service.py`, `deepseek_service.py`) if you need to change model parameters (e.g., temperature, max tokens), how conversation history is handled, or integrate other specific features of the AI provider's API.
5.  **Test:** Send messages to your WhatsApp bot and observe the responses and logs.

**Original OpenAI Assistant Example (for reference):**

The previous instructions for a cookie-cutter OpenAI Assistants API example were:

1. Watch this video: [OpenAI Assistants Tutorial](https://www.youtube.com/watch?v=0h1ry-SqINc)
2. Create your own assistant with OpenAI and update your `OPENAI_API_KEY` and `OPENAI_ASSISTANT_ID` in the environment variables.
3. Provide your assistant with data and instructions
4. Update [openai_service.py](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/app/services/openai_service.py) to your use case.
5. Import `generate_response` into [whatsapp_utils.py](https://github.com/daveebbelaar/python-whatsapp-bot/blob/main/app/utils/)
6. Update `process_whatsapp_message()` with the new `generate_response()` function.

These general principles are now handled by the multi-provider setup, with provider-specific configurations as noted above.

## Step 7: Add a Phone Number

When you're ready to use your app for a production use case, you need to use your own phone number to send messages to your users.

To start sending messages to any WhatsApp number, add a phone number. To manage your account information and phone number, [see the Overview page.](https://business.facebook.com/wa/manage/home/) and the [WhatsApp docs](https://developers.facebook.com/docs/whatsapp/phone-numbers/).

If you want to use a number that is already being used in the WhatsApp customer or business app, you will have to fully migrate that number to the business platform. Once the number is migrated, you will lose access to the WhatsApp customer or business app. [See Migrate Existing WhatsApp Number to a Business Account for information](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started/migrate-existing-whatsapp-number-to-a-business-account).

Once you have chosen your phone number, you have to add it to your WhatsApp Business Account. [See Add a Phone Number](https://developers.facebook.com/docs/whatsapp/cloud-api/get-started/add-a-phone-number).

When dealing with WhatsApp Business API and wanting to experiment without affecting your personal number, you have a few options:

1. Buy a New SIM Card
2. Virtual Phone Numbers
3. Dual SIM Phones
4. Use a Different Device
5. Temporary Number Services
6. Dedicated Devices for Development

**Recommendation**: If this is for a more prolonged or professional purpose, using a virtual phone number service or purchasing a new SIM card for a dedicated device is advisable. For quick tests, a temporary number might suffice, but always be cautious about security and privacy. Remember that once a number is associated with WhatsApp Business API, it cannot be used with regular WhatsApp on a device unless you deactivate it from the Business API and reverify it on the device.


## Tutorials

For video tutorials, visit the YouTube channel: [youtube.com/@daveebbelaar](youtube.com/@daveebbelaar)
