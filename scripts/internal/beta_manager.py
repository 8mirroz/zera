#!/usr/bin/env python3
import os
import sys
import shutil
import logging
from datetime import datetime

MAIN_PROFILE_DIR = os.path.expanduser("~/.hermes/profiles/zera")
BETA_PROFILE_DIR = os.path.expanduser("~/.hermes/profiles/zera_beta")
LOG_FILE = os.path.expanduser("~/.hermes/profiles/zera/logs/beta_manager.log")

# Ensure logs dir exists
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def setup_beta():
    """Создает параллельную теневую конфигурацию на основе main."""
    if os.path.exists(BETA_PROFILE_DIR):
        logging.info("Очистка старой бета-среды перед клонированием.")
        shutil.rmtree(BETA_PROFILE_DIR)
        
    logging.info(f"Создание Shadow Instance: клонирование из {MAIN_PROFILE_DIR} в {BETA_PROFILE_DIR}")
    try:
        shutil.copytree(MAIN_PROFILE_DIR, BETA_PROFILE_DIR)
        print(f"✅ Успешно: Параллельная бета-система инициализирована в {BETA_PROFILE_DIR}.")
        # Перезаписываем имя профиля в конфиге беты, чтобы не путаться
        config_path = os.path.join(BETA_PROFILE_DIR, "config.yaml")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                content = f.read()
            content = content.replace("profile_name: zera", "profile_name: zera_beta")
            with open(config_path, "w") as f:
                f.write(content)
                
    except Exception as e:
        print(f"❌ Ошибка клонирования профиля: {e}")
        logging.error(f"Ошибка клонирования профиля: {e}")

def promote_beta():
    """Мигрирует конфигурацию беты обратно в production после успешных тестов метрик."""
    if not os.path.exists(BETA_PROFILE_DIR):
        print("❌ Ошибка: Бета-среда не найдена, нечего мигрировать.")
        return
        
    logging.info("Принято решение о Promote. Миграция конфигов из Beta в Main.")
    
    # Резервная копия Main на всякий случай
    backup_dir = f"{MAIN_PROFILE_DIR}_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    shutil.copytree(MAIN_PROFILE_DIR, backup_dir)
    logging.info(f"Сделан бекап main-среды в {backup_dir}")

    try:
        # Для простоты заменяем основные конфигурационные файлы
        for filename in ["config.yaml", "cli_tools.json", ".env"]:
            beta_file = os.path.join(BETA_PROFILE_DIR, filename)
            main_file = os.path.join(MAIN_PROFILE_DIR, filename)
            if os.path.exists(beta_file):
                shutil.copy2(beta_file, main_file)
                # Возвращаем правильное имя профиля
                if filename == "config.yaml":
                    with open(main_file, "r") as f:
                        content = f.read()
                    content = content.replace("profile_name: zera_beta", "profile_name: zera")
                    with open(main_file, "w") as f:
                        f.write(content)
                        
        print(f"✅ Успешно: Инновации из беты интегрированы в main ядро. Сделан бекап в {backup_dir}.")
        
    except Exception as e:
        print(f"❌ Ошибка промоута: {e}")
        logging.error(f"Ошибка промоута: {e}")
        
    # Очищаем бету
    shutil.rmtree(BETA_PROFILE_DIR)
    logging.info("Shadow Beta среда удалена после успешного Promote.")

def rollback_beta():
    """Отменяет бета-эксперимент, удаляя теневую среду."""
    if os.path.exists(BETA_PROFILE_DIR):
        shutil.rmtree(BETA_PROFILE_DIR)
        print("✅ Успешно: Теневой профиль удален, откат (Rollback) выполнен.")
        logging.info("Откат бета среды. Профили удалены.")
    else:
        print("ℹ️ Бета среда и так не существовала.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python beta_manager.py [setup|promote|rollback]")
        sys.exit(1)
        
    command = sys.argv[1]
    if command == "setup":
        setup_beta()
    elif command == "promote":
        promote_beta()
    elif command == "rollback":
        rollback_beta()
    else:
        print(f"Неизвестная команда: {command}")
