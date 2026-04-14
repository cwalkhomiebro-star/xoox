# 🚀 Telegram Sales Bot - Setup Guide

This guide will help you get your production-ready Telegram sales bot up and running.

## Prerequisites

1.  **Python 3.10+**: Ensure Python is installed.
2.  **Bot Token**: Get one from [@BotFather](https://t.me/BotFather).
3.  **Telegram User ID**: Get your ID from [@userinfobot](https://t.me/userinfobot) for the `ADMIN_ID`.
4.  **Channel ID**: Create a private channel and add your bot as an **Administrator**.
    - To find your Channel ID, forward a message from the channel to [@userinfobot] or use a bot like [@MissRose_bot] (command `/id`). Private channel IDs usually start with `-100`.

## Installation Steps

1.  **Extract/Clone** the files into a new directory.
2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure Environment**:
    - Rename `.env.example` to `.env`.
    - Fill in your `TELEGRAM_BOT_TOKEN`, `ADMIN_ID`, `CHANNEL_ID`, and `USDT_TRC20_WALLET`.
4.  **Run the Bot**:
    ```bash
    python main.py
    ```

## Bot Commands

### User Commands
-   `/start`: Opens the welcome menu with pricing and links.

### Admin Commands (Admin Only)
-   `/pending`: Lists all users who have clicked "I Have Paid" and are waiting for verification.
-   `/approve USER_ID`: Approves a specific user and automatically sends them a single-use invite link to your private channel.

## Customization

-   **Pricing**: Edit `config.py` - `PRICING_PLANS` dictionary.
-   **Welcome Text**: Modify the `welcome_text` variable in `main.py`.
-   **Demo/Channel Links**: Search for "https://t.me/your_channel" in `main.py` and replace them with your actual links.

## Security & Reliability
-   **Manual Verification**: This bot uses manual verification for USDT payments. You should verify the transaction on a block explorer (e.g., [TronScan](https://tronscan.org/)) before using the `/approve` command.
-   **Database**: The bot uses a local SQLite database (`bot_database.db`). Back this file up regularly.
