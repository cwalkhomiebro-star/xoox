# 🚀 9-17 Bot — Setup Guide

This guide covers everything you need to get the bot running locally or on Render.

---

## Prerequisites

1. **Python 3.10+** installed
2. **Bot Token** — get one from [@BotFather](https://t.me/BotFather)
3. **Admin Telegram ID** — get yours from [@userinfobot](https://t.me/userinfobot)
4. **Private Channel** — create one and add your bot as **Administrator** with invite-link permission
   - Get the Channel ID by forwarding any message from the channel to [@userinfobot](https://t.me/userinfobot). It starts with `-100`.
5. **USDT TRC20 wallet** — your receiving address for crypto payments

---

## Installation

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Copy the environment template and fill in your values
copy .env.example .env
# (then edit .env with your real token, IDs, wallet, etc.)

# 3. Run the bot
python main.py
```

---

## Environment Variables (`.env`)

| Variable | Description |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `ADMIN_ID` | Your numeric Telegram user ID |
| `CHANNEL_ID` | Private channel ID (e.g. `-1001234567890`) |
| `USDT_TRC20_WALLET` | Your TRC20 wallet address for USDT payments |
| `SUPPORT_USERNAME` | Telegram username for support (no `@`) |
| `BOT_USERNAME` | Your bot's username (no `@`) — needed for referral links |

---

## Bot Commands Reference

### User Commands
| Command | Description |
|---|---|
| `/start` | Opens the main menu |
| `/start ref_<ID>` | Joins via a referral link |
| `/start plan_<id>` | Deep-links directly to a plan (e.g. `/start plan_pro`) |

### Admin Commands (Admin Only — restricted to `ADMIN_ID`)
| Command | Description |
|---|---|
| `/admin` | Opens admin panel with user count overview |
| `/pending` | Lists users waiting for manual payment approval |
| `/approve USER_ID` | Approves a user and sends them a single-use invite link |
| `/cancel USER_ID` | Marks a user as cancelled |
| `/stats` | Full analytics dashboard (funnel, revenue, referrers) |
| `/users [page]` | Paginated list of all registered users |
| `/demos` | Demo click analytics with bar chart |
| `/lookup @username or ID` | Quick user search by username or numeric ID |
| `/ban USER_ID [reason]` | Bans a user from using the bot |
| `/unban USER_ID` | Removes a ban |
| `/broadcast MESSAGE` | Sends a message to all registered users |
| `/refund USER_ID CHARGE_ID` | Issues a Telegram Stars refund |

---

## Payment Flows

### Stars (Automatic)
1. User clicks a plan → chooses Stars → invoice is sent
2. User pays in-app
3. Bot automatically generates a single-use invite link and delivers it
4. Admin is notified (no action required)

### USDT Crypto (Manual)
1. User clicks a plan → chooses Crypto → wallet address shown
2. User sends USDT (TRC20) and clicks "I've Sent the Payment"
3. Admin is notified via Telegram
4. **You verify the transaction** on [TronScan](https://tronscan.org/)
5. Run `/approve USER_ID` to deliver the invite link

---

## Customisation

| What to change | Where |
|---|---|
| Pricing plans | `config.py` → `PRICING_PLANS` dict |
| Welcome message | `config.py` → `WELCOME_TEXT` |
| Demo menu text | `config.py` → `DEMO_MENU_TEXT` |
| Demo links | `config.py` → `DEMO_LINK_1` … `DEMO_LINK_4` |
| FAQ entries | `config.py` → `FAQ_ITEMS` list |
| Brand footer | `config.py` → `BRAND_FOOTER` |

---

## Deployment (Render Free Tier)

The `render.yaml` is pre-configured. Push to GitHub and connect the repo in Render.
Set all environment variables in the Render dashboard (not in `render.yaml`).

> **Important:** Only run **one instance** at a time. Running locally while Render is also polling
> will cause `409 Conflict` errors. Pause the Render service before running locally, or use
> a separate dev bot token in your local `.env`.

---

## Security Notes

- **Never commit `.env`** — it is already listed in `.gitignore`
- **Rotate your bot token** via @BotFather if it is ever exposed in a repository
- **Back up `bot_database.db`** regularly — it holds all user records
- The database uses **WAL journal mode** for crash resilience
