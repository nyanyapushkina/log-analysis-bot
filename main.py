import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.filters import Command
from dotenv import load_dotenv
import logging
import yaml

# Logging settings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Congif
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

os.makedirs('logs', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Filter errors and warnings
CONFIG_PATH = 'config/filters.yaml'
DEFAULT_CONFIG = {
    'filters': [
        {
            'name': 'Ошибки',
            'pattern': r'ERROR|CRITICAL|FAILED|EXCEPTION',
            'enabled': True
        },
        {
            'name': 'Предупреждения',
            'pattern': r'WARNING',
            'enabled': True
        },
        {
            'name': 'Авторизация',
            'pattern': r'AUTH|LOGIN|LOGOUT|SESSION',
            'enabled': False
        }
    ],
    'log_file': 'logs/logs.log',
    'max_lines': 1000
}

def load_config():
    """Load configuration from YAML file or create default if not exists"""
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True)
        return DEFAULT_CONFIG
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def save_config(config):
    """Save current configuration to YAML file"""
    with open(CONFIG_PATH, 'w') as f:
        yaml.dump(config, f, allow_unicode=True)

config = load_config()


class LogAnalyzer:
    def __init__(self):
        """Initialize log analyzer with current configuration"""
        self.update_filters()
        self.log_file = config['log_file']
        self.max_lines = config['max_lines']
    
    def update_filters(self):
        """Update active filters from configuration"""
        self.filters = [f for f in config['filters'] if f['enabled']]
    
    def analyze_logs(self):
        """Analyze logs using active filters and get a dict"""
        results = {f['name']: [] for f in self.filters}
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()[-self.max_lines:]
                
            for line in lines:
                for filter in self.filters:
                    if re.search(filter['pattern'], line, re.IGNORECASE):
                        results[filter['name']].append(line.strip())
                        break
            
            return results
        except Exception as e:
            logger.error(f"Ошибка анализа логов: {e}")
            return None

    
    def format_results(self, results):
        """Results formatter"""
        if not results:
            return "Не удалось проанализировать логи"
            
        message = []
        for filter_name, lines in results.items():
            if lines:
                message.append(f"📍 {filter_name} ({len(lines)}):")
                message.extend(lines[-20:])
                message.append("") 
        
        return "\n".join(message) if message else "Записи не найдены"

# Bot initialization
bot = Bot(token=TOKEN)
dp = Dispatcher()
analyzer = LogAnalyzer()


def get_main_keyboard():
    """Create a keyboard for main commands"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="/logs"), KeyboardButton(text="/filters")],
            [KeyboardButton(text="/contact"), KeyboardButton(text="/help")]
        ],
        resize_keyboard=True
    )


def get_filters_keyboard():
    """Create keyboard for filter selection"""
    buttons = []
    for filter in config['filters']:
        status = "✅" if filter['enabled'] else "❌"
        buttons.append([KeyboardButton(text=f"{status} {filter['name']}")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


async def send_welcome(message: Message):
    """Send welcome message with bot description and active filters"""
    active_filters = "\n".join(
        f"• {f['name']} ({f['pattern']})" 
        for f in config['filters'] 
        if f['enabled']
    )
    
    await message.reply(
        f"Бот для отслеживания ошибок, который освобождает разработчиков от ручного мониторинга логов\n\n"
        f"Активные фильтры:\n{active_filters}\n\n"
        f"Загрузите файл с раширением .log и затем отправьте команду /logs, чтобы получить отчет"
    )


async def send_logs(message: Message):
    await message.reply("⏳ Анализирую логи...", reply_markup=ReplyKeyboardRemove())
    
    try:
        analyzer.update_filters()
        results = await asyncio.to_thread(analyzer.analyze_logs)
        formatted = analyzer.format_results(results)
        
        if len(formatted) > 4000:
            for chunk in [formatted[i:i+4000] for i in range(0, len(formatted), 4000)]:
                await message.answer(chunk)
        else:
            await message.answer(formatted)
    except Exception as e:
        logger.error(f"Ошибка обработки команды: {e}")
        await message.answer(f"Произошла ошибка: {e}")


async def handle_document(message: Message):
    """Handle uploaded log files"""
    if not message.document.file_name.endswith('.log'):
        await message.reply("Пожалуйста, отправьте файл с расширением .log")
        return
    
    try:
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        
        file_path = f"logs/{file_id}.log"
        await bot.download_file(file.file_path, file_path)
        
        analyzer.log_file = file_path
        config['log_file'] = file_path
        save_config(config)
        
        await message.reply("Файл логов успешно загружен. Используйте команду /logs, чтобы получить анализ",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        await message.reply(f"Произошла ошибка при загрузке файла: {e}")


async def show_filters_menu(message: Message):
    """Show interactive filters menu with toggle buttons"""
    await message.reply(
        "Выберите, какие фильтры применить:",
        reply_markup=get_filters_keyboard()
    )


async def toggle_filter(message: Message):
    """Toggle filter status based on button press"""
    try:
        button_text = message.text
        filter_name = button_text[2:].strip()
        
        if filter_name == "⬅️ Назад":
            await message.reply("Вернуться в главное меню", reply_markup=get_main_keyboard())
            return
            
        for filter in config['filters']:
            if filter['name'] == filter_name:
                filter['enabled'] = not filter['enabled']
                save_config(config)
                await message.reply(
                    f"Filter '{filter_name}' {'enabled' if filter['enabled'] else 'disabled'}",
                    reply_markup=get_filters_keyboard()
                )
                return
                
        await message.reply("Фильтры не найдены", reply_markup=get_filters_keyboard())
    except Exception as e:
        logger.error(f"Ошибка переключения фильтров: {e}")
        await message.reply(f"Ошибка: {e}", reply_markup=get_main_keyboard())


async def contact_developer(message: Message):
    """Show developer contact information"""
    await message.reply(
        "Обратная связь: @nyanyapushkina\n\n"
        "Код на <a href='https://github.com/nyanyapushkina/log-analysis-bot'>GitHub</a>",
        parse_mode="HTML",
        reply_markup=get_main_keyboard()
    )


# Command handlers
dp.message.register(send_welcome, Command(commands=['start', 'help']))
dp.message.register(send_logs, Command(commands='logs'))
dp.message.register(show_filters_menu, Command(commands='filters'))
dp.message.register(contact_developer, Command(commands='contact'))
dp.message.register(handle_document, F.document)
dp.message.register(toggle_filter, F.text.startswith(('✅', '❌')))


async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    logger.info("Запуск бота...")
    asyncio.run(main())
