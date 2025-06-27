from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import yaml
import os

# 读取MySQL配置
def get_mysql_url():
    config_path = os.path.join(os.path.dirname(__file__), '../..', 'config.yaml')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    mysql = config['mysql']
    return f"mysql+pymysql://{mysql['user']}:{mysql['password']}@{mysql['host']}:{mysql['port']}/{mysql['database']}"

SQLALCHEMY_DATABASE_URL = get_mysql_url()
engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 