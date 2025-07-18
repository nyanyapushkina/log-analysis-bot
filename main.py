import os
import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv
import logging
import yaml

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Загрузка конфигурации
load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')

# Создаём папки если их нет
os.makedirs('logs', exist_ok=True)
os.makedirs('config', exist_ok=True)

# Загрузка конфигурации фильтров
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
    """Загружает или создает конфигурационный файл"""
    if not os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(DEFAULT_CONFIG, f, allow_unicode=True)
        return DEFAULT_CONFIG
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)

config = load_config()

class LogAnalyzer:
    def __init__(self):
        self.filters = [f for f in config['filters'] if f['enabled']]
        self.log_file = config['log_file']
        self.max_lines = config['max_lines']

    def analyze_logs(self):
        """Анализирует логи и возвращает отфильтрованные результаты"""
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
        """Форматирует результаты для отправки"""
        if not results:
            return "Не удалось проанализировать логи"
            
        message = []
        for filter_name, lines in results.items():
            if lines:
                message.append(f"📍 {filter_name} ({len(lines)}):")
                message.extend(lines[-20:])  # Последние 10 записей каждого типа 
                message.append("") 
        
        return "\n".join(message) if message else "Нет записей, соответствующих фильтрам"

# Инициализация бота
bot = Bot(token=TOKEN)
dp = Dispatcher()
analyzer = LogAnalyzer()

async def send_welcome(message: Message):
    """Приветственное сообщение с инструкциями"""
    active_filters = "\n".join(
        f"• {f['name']} ({f['pattern']})" 
        for f in config['filters'] 
        if f['enabled']
    )
    
    await message.reply(
        f"📋 Бот для анализа логов\n\n"
        f"Активные фильтры:\n{active_filters}\n\n"
        f"Отправьте команду /logs для получения последних логов"
    )

async def send_logs(message: Message):
    """Обработка команды для получения логов"""
    await message.reply("Анализирую логи...")
    
    try:
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
    """Обработка загруженного файла логов"""
    if not message.document.file_name.endswith('.log'):
        await message.reply("Пожалуйста, отправьте файл с расширением .log")
        return
    
    try:
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        
        # Формируем путь для сохранения
        file_path = f"logs/{file_id}.log"
        
        # Скачиваем файл
        await bot.download_file(file.file_path, file_path)
        
        # Обновляем путь к логам в анализаторе
        analyzer.log_file = file_path
        
        await message.reply("Файл логов успешно загружен. Используйте /logs для анализа.")
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        await message.reply(f"Произошла ошибка при загрузке файла: {e}")

# Регистрация обработчиков
dp.message.register(send_welcome, Command(commands=['start', 'help']))
dp.message.register(send_logs, Command(commands='logs'))
dp.message.register(handle_document, F.document)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    logger.info("Запуск бота...")
    asyncio.run(main())
