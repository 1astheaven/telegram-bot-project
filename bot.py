from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, ContextTypes
from database import session, User, Building, Room, Asset
from sqlalchemy.sql import text
import logging

# Настройка логирования для отладки
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния разговора
REGISTER_NAME, REGISTER_EMAIL, MAIN_MENU, VIEW_BUILDING, VIEW_ASSET, SEARCH_ASSET, VIEW_PROFILE = range(7)

# Токен бота
TOKEN = '8016146950:AAG2U1xHRcUt3jyzwaHbLJD4rzWkPSx5Mv0'

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    logger.info(f"Start command triggered by user {user.username} (ID: {user.id})")
    existing_user = session.query(User).filter_by(telegram_id=user.id).first()
    if not existing_user:
        await update.message.reply_text("Добро пожаловать! Пожалуйста, введите ваше имя для регистрации.")
        return REGISTER_NAME
    await update.message.reply_text(
        f"Добро пожаловать, {existing_user.username}! Ваш email: {existing_user.email or 'Не указан'}\nИспользуйте /menu для доступа к функциям.",
        reply_markup=ReplyKeyboardMarkup([['/menu']], one_time_keyboard=True)
    )
    return ConversationHandler.END

# Регистрация: ввод имени
async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.message.from_user
    username = update.message.text
    context.user_data['username'] = username
    logger.info(f"Registering name: {username} for user {user.id}")
    await update.message.reply_text(f"Регистрация, {username}! Пожалуйста, введите ваш email.")
    return REGISTER_EMAIL

# Регистрация: ввод email
async def register_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text
    username = context.user_data['username']
    user = User(telegram_id=update.message.from_user.id, username=username, email=email)
    session.add(user)
    session.commit()
    logger.info(f"Registration complete for {username} with email {email}")
    await update.message.reply_text(
        f"Регистрация успешна, {username}! Ваш email: {email}\nИспользуйте /menu для доступа к функциям.",
        reply_markup=ReplyKeyboardMarkup([['/menu']], one_time_keyboard=True)
    )
    return MAIN_MENU

# Главное меню через /menu
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info(f"Menu command triggered by user {update.message.from_user.username}")
    user = session.query(User).filter_by(telegram_id=update.message.from_user.id).first()
    if not user:
        await update.message.reply_text("Пользователь не найден. Пожалуйста, зарегистрируйтесь заново с /start.")
        return ConversationHandler.END
    await update.message.reply_text(
        f"Добро пожаловать, {user.username}! Ваш email: {user.email or 'Не указан'}\nВыберите действие:",
        reply_markup=ReplyKeyboardMarkup([['1. Просмотр корпусов', '2. Поиск инвентарной единицы', '3. Мой профиль']], one_time_keyboard=True)
    )
    return MAIN_MENU

# Просмотр корпусов с помещениями и имуществом
async def view_building(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "Просмотр корпусов" in update.message.text:
        logger.info("Viewing buildings")
        try:
            buildings = session.query(Building).all()
            if buildings:
                response = "Список корпусов и помещений с имуществом:\n"
                for building in buildings:
                    response += f"\nКорпус {building.id}. {building.name}\n"
                    rooms = session.query(Room).filter_by(building_id=building.id).all()
                    if rooms:
                        for room in rooms:
                            response += f"  Помещение №{room.number}\n"
                            assets = session.query(Asset).filter_by(room_id=room.id).all()
                            if assets:
                                response += "    Имущество:\n" + "\n".join([f"    - {a.name} (№ {a.inventory_number})" for a in assets])
                            else:
                                response += "    Имущество отсутствует.\n"
                    else:
                        response += "  Помещения не найдены.\n"
            else:
                response = "Корпуса не найдены."
            await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"Error in view_building: {e}")
            await update.message.reply_text("Произошла ошибка при загрузке корпусов.")
        return MAIN_MENU
    return VIEW_ASSET

# Инициация поиска инвентарной единицы
async def search_asset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "Поиск инвентарной единицы" in update.message.text:
        logger.info("Initiating search for asset")
        await update.message.reply_text("Введите инвентарный номер для поиска:")
        return SEARCH_ASSET
    return VIEW_PROFILE

# Обработка поиска инвентарной единицы
async def process_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    inventory_number = update.message.text.strip()
    logger.info(f"Processing search for inventory number: {inventory_number}")
    try:
        # Проверка подключения к базе данных
        session.execute(text("SELECT 1")).scalar()
        # Проверка всех записей для отладки
        all_assets = session.query(Asset).all()
        logger.info(f"All assets in DB: {[a.inventory_number for a in all_assets]}")
        asset = session.query(Asset).filter_by(inventory_number=inventory_number).first()
        if asset:
            room = session.query(Room).filter_by(id=asset.room_id).first()
            if room:
                response = f"Найдена инвентарная единица:\n{asset.id}. {asset.name} (№ {asset.inventory_number})\nПомещение: №{room.number}, Корпус: {room.building_id}"
            else:
                response = f"Помещение для {asset.name} (№ {asset.inventory_number}) не найдено."
        else:
            response = f"Инвентарная единица с номером {inventory_number} не найдена. Проверьте номер или добавьте данные."
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f"Error in process_search: {e}")
        await update.message.reply_text("Произошла ошибка при поиске. Проверьте подключение или данные.")
    return MAIN_MENU

# Просмотр профиля
async def view_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if "Мой профиль" in update.message.text:
        logger.info("Viewing profile")
        try:
            user = session.query(User).filter_by(telegram_id=update.message.from_user.id).first()
            await update.message.reply_text(f"Ваш профиль:\nИмя: {user.username}\nEmail: {user.email or 'Не указан'}")
        except Exception as e:
            logger.error(f"Error in view_profile: {e}")
            await update.message.reply_text("Произошла ошибка при загрузке профиля.")
        return MAIN_MENU
    return MAIN_MENU

# Обработчик отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    logger.info("Cancel command triggered")
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END

def main() -> None:
    # Проверка данных при старте
    logger.info("Checking database connection...")
    try:
        session.execute(text("SELECT 1")).scalar()
        logger.info("Database connection successful")
        all_assets = session.query(Asset).all()
        logger.info(f"Assets in DB: {[a.inventory_number for a in all_assets]}")
    except Exception as e:
        logger.error(f"Database connection failed: {e}")

    # Создание приложения
    application = Application.builder().token(TOKEN).build()

    # Глобальные обработчики для функций меню
    application.add_handler(CommandHandler('menu', menu))
    application.add_handler(MessageHandler(filters.Regex('^1. Просмотр корпусов$'), view_building))
    application.add_handler(MessageHandler(filters.Regex('^2. Поиск инвентарной единицы$'), search_asset))
    application.add_handler(MessageHandler(filters.Regex('^3. Мой профиль$'), view_profile))

    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_email)],
            MAIN_MENU: [],  # Пустое состояние, так как функции обрабатываются глобально
            VIEW_BUILDING: [],
            SEARCH_ASSET: [MessageHandler(filters.ALL & ~filters.COMMAND, process_search)],  # Используем filters.ALL для обработки любого текста
            VIEW_PROFILE: []
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(conv_handler)

    # Запуск бота
    logger.info("Bot starting...")
    application.run_polling()

if __name__ == '__main__':
    main()