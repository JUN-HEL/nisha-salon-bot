# 🌸 Nisha Hair Salon — AI WhatsApp Assistant

A production-ready, AI-powered WhatsApp receptionist for Nisha Hair Salon. Powered by **Google Gemini 2.5 Flash** with full tool-calling support, **SQLite** for conversation memory, and **Google Sheets** as a live operational data store.

---

## Architecture

```
Customer
  ↓
WhatsApp
  ↓
WhatsApp Cloud API Webhook  (GET /webhook + POST /webhook)
  ↓
FastAPI Backend
  ├── Google Gemini 2.5 Flash (AI + Tool Calling)
  ├── SQLite  (Conversation memory + Customer profiles)
  └── Tool Manager
        ├── FAQ Tool         → Google Sheets (FAQ tab)
        ├── Service Tool     → Google Sheets (Services tab)
        ├── Booking Tool     → Google Sheets (Appointments tab)
        └── Customer Tool    → SQLite + Google Sheets (Customers tab)
  ↓
WhatsApp Cloud API → Customer
```

---

## Features

| Feature | Description |
|---|---|
| 🤖 AI Receptionist | Gemini 2.5 Flash with function calling — behaves like a real receptionist |
| 📅 Booking Management | Create, reschedule, cancel appointments |
| 💇 Service Lookup | Real-time pricing and duration from Google Sheets |
| ❓ FAQ Answering | Fuzzy-matched FAQ lookup |
| 🧠 Customer Memory | SQLite stores conversation history and preferences |
| 📊 Google Sheets | Live operational store for services, FAQs, bookings |
| 🔄 Webhook | Full Meta webhook verification + async message processing |
| 🛡️ Retry Logic | Exponential backoff on all external calls |
| 📝 Logging | Structured logs via Loguru |

---

## Quick Start (Local)

### 1. Clone & Install

```bash
cd artifacts/nisha-salon-bot
pip install -r requirements.txt
```

### 2. Environment Variables

```bash
cp .env.example .env
# Fill in your credentials
```

### 3. Run

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Expose Locally (for WhatsApp webhook)

```bash
ngrok http 8000
# Use the https URL as your webhook: https://xxxx.ngrok.io/webhook
```

---

## Docker

```bash
docker-compose up --build -d
```

---

## Google Sheets Setup

Create a spreadsheet with 4 tabs:

### FAQ
| Question | Answer |
|---|---|
| What are your opening hours? | Mon–Sat 9am–7pm |

### Services
| Service | Price | Duration | Availability |
|---|---|---|---|
| Haircut | ₹500 | 45 mins | All stylists |
| Balayage | ₹3000 | 3 hrs | Senior stylist only |

### Appointments
| Name | Phone | Service | Stylist | Date | Time | Status |
|---|---|---|---|---|---|---|

### Customers
| Phone | Name | PreferredStylist | FavoriteService | VisitCount | LastVisit | Notes |
|---|---|---|---|---|---|---|

Share the spreadsheet with your service account email (from the credentials JSON).

---

## WhatsApp Cloud API Setup

1. Go to [Meta for Developers](https://developers.facebook.com)
2. Create an App → WhatsApp → API Setup
3. Copy **Phone Number ID** and **Access Token**
4. Set webhook URL: `https://your-domain.com/webhook`
5. Set Verify Token to your `WHATSAPP_VERIFY_TOKEN`
6. Subscribe to the `messages` webhook field

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/` | Root info |
| GET | `/health` | Health check |
| GET | `/webhook` | Meta webhook verification |
| POST | `/webhook` | Inbound messages from WhatsApp |
| POST | `/send-message` | Manually send a message |
| GET | `/customers` | List all customers (admin) |
| GET | `/appointments` | List all appointments (admin) |
| GET | `/docs` | Interactive Swagger UI |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Environment Variables

| Variable | Description |
|---|---|
| `WHATSAPP_ACCESS_TOKEN` | Meta permanent or temporary access token |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp phone number ID |
| `WHATSAPP_VERIFY_TOKEN` | Custom verify token for webhook |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GEMINI_MODEL` | Model name (default: `gemini-2.5-flash`) |
| `GOOGLE_SHEET_ID` | Google Spreadsheet ID |
| `GOOGLE_SHEETS_CREDENTIALS_JSON` | Full service account JSON as a string |
| `DATABASE_URL` | SQLite URL (default: `sqlite+aiosqlite:///./nisha_salon.db`) |

---

## Extending the Bot

- **New tool**: Add declaration + async function in `app/tools/`, register in `TOOL_REGISTRY` in `app/ai/gemini_client.py`
- **New route**: Add to `main.py` or a new router
- **Multiple branches**: Add a `branch` field to the `Customer` model and route by phone prefix
- **Payment**: Integrate Razorpay/Stripe as a new tool
- **Voice messages**: Add an audio transcription step before the Gemini call
