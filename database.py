from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Настройка базы данных
engine = create_engine('sqlite:///university_assets.db', echo=True)
Base = declarative_base()

# Модель пользователя
class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    username = Column(String)
    email = Column(String)  # Добавлено поле email

# Модель корпуса
class Building(Base):
    __tablename__ = 'buildings'
    id = Column(Integer, primary_key=True)
    name = Column(String)

# Модель помещения
class Room(Base):
    __tablename__ = 'rooms'
    id = Column(Integer, primary_key=True)
    building_id = Column(Integer)
    number = Column(String)

# Модель инвентарной единицы
class Asset(Base):
    __tablename__ = 'assets'
    id = Column(Integer, primary_key=True)
    room_id = Column(Integer)
    name = Column(String)
    inventory_number = Column(String)

# Создание таблиц
Base.metadata.create_all(engine)

# Создание сессии
Session = sessionmaker(bind=engine)
session = Session()