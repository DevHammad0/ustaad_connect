# Ustaad Connect

**Slogan:** Har masla ka hal - Ustaad Connect

Ustaad Connect is an AI-powered home-services booking platform designed for Pakistan's informal economy. It bridges the gap between customers needing quick home services (like AC repair, plumbing, and electrical work) and skilled local providers. 

The solution offers an intuitive, low-friction booking experience where customers simply chat on WhatsApp with our AI Agent ("Ustaad"), while providers manage their jobs through a dedicated mobile app.

---

## 🌟 Overall Design of the Solution

Our solution is designed around accessibility and automation:
1. **Customer Side (WhatsApp):** Instead of downloading an app, customers interact with a highly professional, conversational AI agent on WhatsApp. The agent detects their language (English, Roman Urdu, or Urdu script), collects their issue, requests their location via WhatsApp's native location picker, and presents nearby providers via interactive media carousels.
2. **Provider Side (Mobile App):** Providers use a dedicated Flutter-based mobile application. Here, they receive job requests, accept/reject bookings, offer cost estimates, and update their live status (En route, Arrived, Completed), which automatically notifies the customer via the WhatsApp agent.
3. **Agentic Workflow:** The core intelligence is handled by the **Ustaad Agent**, built using `openai-agents` SDK. It autonomously decides when to check the database, when to dispatch a location request, when to create a booking, and when to reply with text or voice based on the customer's input modality.

---

## 🏗️ Architecture Overview

The system architecture is a unified modern stack ensuring real-time interactivity and scalability:

- **Backend Framework:** FastAPI (Python) serving as the core API gateway and webhook listener.
- **Database:** PostgreSQL (via Supabase and SQLModel/SQLAlchemy) handling customers, providers, and bookings.
- **Memory & Caching:** Upstash Redis used for maintaining persistent conversation memory across WhatsApp sessions for each unique customer phone number.
- **Provider Mobile App:** A cross-platform Flutter application for service providers.
- **Background Jobs / Queues:** **Google Cloud Tasks** is utilized for asynchronous task offloading, ensuring reliable, decoupled, and scalable execution of webhook events and notifications.
- **Hosting / Deployment:** Deployed on **Google Cloud Run**, providing a fully managed, serverless execution environment that automatically scales with incoming WhatsApp traffic.

---

## 🤖 Agents Developed

We developed the **Ustaad Agent**, an advanced conversational assistant leveraging the `openai-agents` SDK. 

### Capabilities & Features:
- **Multimodal Interactions:** Can process and reply to text and voice notes. If a user sends an audio message, the agent responds with a concise, spoken voice message.
- **Language Detection & Adaptation:** Automatically detects if the customer is typing/speaking in English, Roman Urdu, or Urdu script, and aligns its responses accordingly.
- **Tool Calling (8 Custom Tools):**
  - `check_customer_exists` / `register_customer`: Seamless onboarding.
  - `get_service_categories`: Intent classification mapping user issues to canonical service types (AC repair, plumber, electrician).
  - `request_location`: Triggers a native WhatsApp interactive location request.
  - `fetch_available_providers`: Queries the database for nearby providers using geospatial filtering (distance) and renders them as interactive WhatsApp carousels.
  - `initiate_provider_booking`: Secures the booking and connects the provider.
  - `check_booking_status`: Real-time tracking of provider status.
  - `cancel_booking` / `confirm_booking`: State management for active jobs.
  - `submit_rating`: Feedback loop post-completion.

---

## 🔌 Integrations & APIs Used

- **Meta Cloud API (WhatsApp Webhooks):** Real-time messaging, handling text, audio, interactive buttons, and location payloads. Used extensively for dispatching interactive carousels and location requests to customers.
- **Nominatim / Geopy (Real API):** Used for reverse geocoding customer coordinates (latitude/longitude) into canonical Pakistani city slugs to efficiently filter the provider database. Includes rate-limiting and a 7-day TTL caching mechanism.
- **OpenAI / Google GenAI SDK (Real API):** Powers the core LLM reasoning, intent detection, and tool-calling capabilities of the Ustaad Agent.
- **Supabase PostgreSQL (Real API):** For persistent relational storage of our service providers, users, and booking lifecycle.
- **Upstash Redis (Real API):** For managing the session state and conversational memory of the AI agent for individual phone numbers.

---

## 🚀 How to Run Locally

1. **Install dependencies** using `uv`:
   ```bash
   uv sync
   ```
2. **Environment Variables**: Setup `.env` file based on `.env.example` (Requires OpenAI/Gemini keys, Meta API tokens, Supabase, and Upstash Redis credentials).
3. **Start the backend server**:
   ```bash
   uv run fastapi dev src/api/main.py
   ```
4. **Mobile App**: Navigate to `provider_mobile_app/`, run `flutter pub get`, and launch via `flutter run`.

---
*Built for the Google AI Seeko Hackathon - Informal Economy Challenge.*

*Note: antigravity was used for the development of entire project from A to Z as google ai seeko requirement.*
