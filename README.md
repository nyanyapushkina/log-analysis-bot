
# Telegram Log Analysis Bot

Telegram bot that analyzes your logs and makes them readable — so you can focus on fixing bugs instead of decoding them. Developed as a project for the [VK Education](https://education.vk.company/education_projects) course.


 -  Upload log files directly in chat
 -  Configure filters with interactive buttons:
	- Errors (ERROR/CRITICAL/FAILED)
	- Warnings (WARNING)
	- Authentication messages (AUTH/LOGIN)
 - Get easy-to-read results grouped by message type

##  Technologies

- Python 3.9+
- aiogram 3.x (async Telegram Bot API)


## Installation
1. Clone the repository:
```bash
git clone https://github.com/nyanyapushkina/log-analysis-bot.git
cd log-analysis-bot 
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3.  Create  `.env`  file with bot token:
```bash
ini
BOT_TOKEN=your_bot_token_here
``` 

4.  Run the bot:
 ```bash
python main.py
```    


## Usage

Main commands:
-   `/start`  or  `/help`  – show help
-   `/logs`  – analyze uploaded logs (you have to send the file prior to this step)
-   `/filters`  – configure filters
-   `/contact`  – contact developer (don't send hate pls)
    

## Contacts

Developer:  [@nyanyapushkina](https://t.me/nyanyapushkina)  
Source code:  [GitHub](https://github.com/nyanyapushkina/log-analysis-bot)
