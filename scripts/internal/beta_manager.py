#!/usr/bin/env python3
from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

try:
    import fcntl  # macOS / Linux
except ImportError:  # pragma: no cover
    fcntl = None


MAIN_PROFILE_DIR = Path("~/.hermes/profiles/zera").expanduser()
BETA_PROFILE_DIR = Path("~/.hermes/profiles/zera_beta").expanduser()

STATE_ROOT = Path("~/.hermes/beta_manager").expanduser()
LOG_FILE = STATE_ROOT / "logs" / "beta_manager.log"
LOCK_FILE = STATE_ROOT / "beta_manager.lock"
LAST_PROMOTION_FILE = STATE_ROOT / "last_promotion.json"
BACKUP_ROOT = STATE_ROOT / "backups"

SYNC_FILES = ("config.yaml", "cli_tools.json", ".env")
REQUIRED_MAIN_FILES = ("config.yaml",)

IGNORE_PATTERNS = shutil.ignore_patterns(
    "__pycache__",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "logs",
    "tmp",
    ".cache",
)

PROFILE_NAME_PATTERN = re.compile(
    r"(?m)^(\s*profile_name\s*:\s*)(['\"]?)([^'\"]+)(\2\s*)$"
)


class BetaManagerError(RuntimeError):
    """Предсказуемая ошибка менеджера beta-профиля."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def ts() -> str:
    return utc_now().strftime("%Y%m%dT%H%M%SZ")


def ensure_state_dirs() -> None:
    (STATE_ROOT / "logs").mkdir(parents=True, exist_ok=True)
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)


def configure_logging(verbose: bool = False) -> None:
    ensure_state_dirs()
    handlers: list[logging.Handler] = [logging.FileHandler(LOG_FILE, encoding="utf-8")]
    if verbose:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=handlers,
        force=True,
    )


@contextlib.contextmanager
def process_lock():
    ensure_state_dirs()
    with open(LOCK_FILE, "a+", encoding="utf-8") as fh:
        if fcntl is not None:
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as e:
                raise BetaManagerError(
                    f"Уже выполняется другой процесс beta_manager. Lock: {LOCK_FILE}"
                ) from e

        fh.seek(0)
        fh.truncate()
        fh.write(f"pid={os.getpid()} started_at={utc_now().isoformat()}\n")
        fh.flush()

        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def is_safe_managed_path(path: Path) -> bool:
    try:
        resolved = path.resolve()
    except FileNotFoundError:
        resolved = path.expanduser().absolute()

    profiles_root = Path("~/.hermes/profiles").expanduser().resolve()
    return resolved != profiles_root and profiles_root in resolved.parents


def assert_safe_delete_target(path: Path) -> None:
    if not is_safe_managed_path(path):
        raise BetaManagerError(f"Небезопасный путь для удаления: {path}")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_snapshot(path: Path) -> dict:
    if not path.exists():
        return {"exists": False}

    stat = path.stat()
    return {
        "exists": True,
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "sha256": sha256_file(path),
    }


def collect_sync_manifest(profile_dir: Path) -> dict[str, dict]:
    return {name: file_snapshot(profile_dir / name) for name in SYNC_FILES}


def validate_main_profile() -> None:
    if not MAIN_PROFILE_DIR.exists():
        raise BetaManagerError(f"Main профиль не найден: {MAIN_PROFILE_DIR}")

    missing = [name for name in REQUIRED_MAIN_FILES if not (MAIN_PROFILE_DIR / name).exists()]
    if missing:
        raise BetaManagerError(
            f"В main-профиле отсутствуют обязательные файлы: {', '.join(missing)}"
        )


def validate_beta_profile(force: bool = False) -> None:
    if not BETA_PROFILE_DIR.exists():
        raise BetaManagerError(f"Beta профиль не найден: {BETA_PROFILE_DIR}")

    config_path = BETA_PROFILE_DIR / "config.yaml"
    if not config_path.exists():
        raise BetaManagerError("В beta-профиле отсутствует config.yaml")

    text = config_path.read_text(encoding="utf-8")
    if "profile_name: zera_beta" not in text and not force:
        raise BetaManagerError(
            "config.yaml беты не содержит 'profile_name: zera_beta'. "
            "Либо профиль поврежден, либо используйте --force."
        )


def write_text_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def copy_file_atomic(src: Path, dst: Path, dry_run: bool = False) -> None:
    if dry_run:
        logging.info("[dry-run] Копирование %s -> %s", src, dst)
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{dst.name}.",
        suffix=".tmp",
        dir=str(dst.parent),
    )
    os.close(fd)

    try:
        shutil.copy2(src, temp_name)
        os.replace(temp_name, dst)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def clone_tree_atomic(src: Path, dst: Path, dry_run: bool = False) -> None:
    if dry_run:
        logging.info("[dry-run] Клонирование дерева %s -> %s", src, dst)
        return

    if dst.exists():
        assert_safe_delete_target(dst)
        shutil.rmtree(dst)

    parent = dst.parent
    parent.mkdir(parents=True, exist_ok=True)
    temp_dst = parent / f".{dst.name}.tmp.{ts()}.{os.getpid()}"

    try:
        shutil.copytree(src, temp_dst, ignore=IGNORE_PATTERNS)
        os.replace(temp_dst, dst)
    finally:
        if temp_dst.exists():
            shutil.rmtree(temp_dst, ignore_errors=True)


def remove_tree(path: Path, dry_run: bool = False) -> None:
    if not path.exists():
        return

    assert_safe_delete_target(path)

    if dry_run:
        logging.info("[dry-run] Удаление каталога %s", path)
        return

    shutil.rmtree(path)


def write_json(path: Path, payload: dict, dry_run: bool = False) -> None:
    data = json.dumps(payload, ensure_ascii=False, indent=2)
    if dry_run:
        logging.info("[dry-run] Запись JSON %s", path)
        return
    write_text_atomic(path, data + "\n")


def rewrite_profile_name(config_path: Path, target_profile_name: str, dry_run: bool = False) -> bool:
    if not config_path.exists():
        return False

    original = config_path.read_text(encoding="utf-8")

    if PROFILE_NAME_PATTERN.search(original):
        updated = PROFILE_NAME_PATTERN.sub(
            lambda m: f"{m.group(1)}{m.group(2)}{target_profile_name}{m.group(2)}",
            original,
            count=1,
        )
    else:
        suffix = "" if original.endswith("\n") else "\n"
        updated = f"{original}{suffix}profile_name: {target_profile_name}\n"

    if updated == original:
        return False

    if dry_run:
        logging.info(
            "[dry-run] Был бы обновлен profile_name в %s -> %s",
            config_path,
            target_profile_name,
        )
        return True

    write_text_atomic(config_path, updated)
    return True


def create_main_backup(dry_run: bool = False) -> Path:
    backup_dir = BACKUP_ROOT / f"zera_main_backup_{ts()}"
    if dry_run:
        logging.info("[dry-run] Создание backup %s -> %s", MAIN_PROFILE_DIR, backup_dir)
        return backup_dir

    shutil.copytree(MAIN_PROFILE_DIR, backup_dir, ignore=IGNORE_PATTERNS)
    return backup_dir


def setup_beta(dry_run: bool = False) -> None:
    validate_main_profile()

    if BETA_PROFILE_DIR.exists():
        logging.info("Найдена старая beta-среда. Будет удалена перед пересозданием.")
        remove_tree(BETA_PROFILE_DIR, dry_run=dry_run)

    logging.info("Создание shadow-instance: %s -> %s", MAIN_PROFILE_DIR, BETA_PROFILE_DIR)
    clone_tree_atomic(MAIN_PROFILE_DIR, BETA_PROFILE_DIR, dry_run=dry_run)

    manifest = {
        "version": 2,
        "created_at": utc_now().isoformat(),
        "main_profile_dir": str(MAIN_PROFILE_DIR),
        "beta_profile_dir": str(BETA_PROFILE_DIR),
        "sync_files": list(SYNC_FILES),
        "source_snapshot": collect_sync_manifest(MAIN_PROFILE_DIR),
    }

    if not dry_run:
        rewrite_profile_name(BETA_PROFILE_DIR / "config.yaml", "zera_beta", dry_run=False)
        write_json(BETA_PROFILE_DIR / ".beta_manifest.json", manifest, dry_run=False)
        write_text_atomic(BETA_PROFILE_DIR / ".shadow_profile", "managed_by=beta_manager\n")
    else:
        logging.info("[dry-run] Обновление profile_name и запись manifest в beta-профиль")

    print(f"✅ Параллельная beta-среда инициализирована: {BETA_PROFILE_DIR}")


def promote_beta(dry_run: bool = False, keep_beta: bool = False, force: bool = False) -> None:
    validate_main_profile()
    validate_beta_profile(force=force)

    backup_dir = create_main_backup(dry_run=dry_run)
    logging.info("Создан backup main-среды: %s", backup_dir)

    promoted_files: list[str] = []

    for filename in SYNC_FILES:
        beta_file = BETA_PROFILE_DIR / filename
        main_file = MAIN_PROFILE_DIR / filename

        if not beta_file.exists():
            logging.info("Файл отсутствует в beta и будет пропущен: %s", beta_file)
            continue

        copy_file_atomic(beta_file, main_file, dry_run=dry_run)
        promoted_files.append(filename)

    if "config.yaml" in promoted_files:
        rewrite_profile_name(MAIN_PROFILE_DIR / "config.yaml", "zera", dry_run=dry_run)

    promotion_record = {
        "version": 2,
        "promoted_at": utc_now().isoformat(),
        "backup_dir": str(backup_dir),
        "main_profile_dir": str(MAIN_PROFILE_DIR),
        "beta_profile_dir": str(BETA_PROFILE_DIR),
        "promoted_files": promoted_files,
        "main_snapshot_after_promote": collect_sync_manifest(MAIN_PROFILE_DIR) if not dry_run else {},
    }
    write_json(LAST_PROMOTION_FILE, promotion_record, dry_run=dry_run)

    if not keep_beta:
        remove_tree(BETA_PROFILE_DIR, dry_run=dry_run)
        logging.info("Beta-среда удалена после promote.")
    else:
        logging.info("Beta-среда сохранена (--keep-beta).")

    print(
        "✅ Beta-конфигурация успешно промоутирована в main."
        f"{' [dry-run]' if dry_run else ''} Backup: {backup_dir}"
    )


def rollback_beta(dry_run: bool = False) -> None:
    if not BETA_PROFILE_DIR.exists():
        print("ℹ️ Beta-среда не существует, откатывать нечего.")
        return

    remove_tree(BETA_PROFILE_DIR, dry_run=dry_run)
    logging.info("Beta-среда удалена. Rollback beta-эксперимента завершен.")
    print(f"✅ Beta-среда удалена{' [dry-run]' if dry_run else ''}: {BETA_PROFILE_DIR}")


def restore_last_main(dry_run: bool = False) -> None:
    if not LAST_PROMOTION_FILE.exists():
        raise BetaManagerError("Нет данных о последнем promote. restore-main невозможен.")

    record = json.loads(LAST_PROMOTION_FILE.read_text(encoding="utf-8"))
    backup_dir = Path(record["backup_dir"])

    if not backup_dir.exists():
        raise BetaManagerError(f"Backup из последнего promote не найден: {backup_dir}")

    restored_files: list[str] = []

    for filename in record.get("promoted_files", []):
        src = backup_dir / filename
        dst = MAIN_PROFILE_DIR / filename

        if not src.exists():
            logging.warning("В backup отсутствует файл для восстановления: %s", src)
            continue

        copy_file_atomic(src, dst, dry_run=dry_run)
        restored_files.append(filename)

    if "config.yaml" in restored_files:
        rewrite_profile_name(MAIN_PROFILE_DIR / "config.yaml", "zera", dry_run=dry_run)

    print(
        "✅ Main-профиль восстановлен из последнего backup."
        f"{' [dry-run]' if dry_run else ''} Источник: {backup_dir}"
    )


def status() -> None:
    payload = {
        "main_profile_dir": str(MAIN_PROFILE_DIR),
        "main_exists": MAIN_PROFILE_DIR.exists(),
        "beta_profile_dir": str(BETA_PROFILE_DIR),
        "beta_exists": BETA_PROFILE_DIR.exists(),
        "last_promotion_file_exists": LAST_PROMOTION_FILE.exists(),
        "main_snapshot": collect_sync_manifest(MAIN_PROFILE_DIR) if MAIN_PROFILE_DIR.exists() else {},
        "beta_snapshot": collect_sync_manifest(BETA_PROFILE_DIR) if BETA_PROFILE_DIR.exists() else {},
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Shadow beta manager для профиля Hermes Zera."
    )
    parser.add_argument("--dry-run", action="store_true", help="Показать действия без изменений.")
    parser.add_argument("--verbose", action="store_true", help="Дублировать логи в stdout.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("setup", help="Создать zera_beta из zera.")

    promote_parser = subparsers.add_parser("promote", help="Промоутировать beta -> main.")
    promote_parser.add_argument("--keep-beta", action="store_true", help="Не удалять beta после promote.")
    promote_parser.add_argument("--force", action="store_true", help="Игнорировать часть preflight-check'ов.")

    subparsers.add_parser("rollback", help="Удалить beta-среду.")
    subparsers.add_parser("restore-main", help="Восстановить main из последнего backup.")
    subparsers.add_parser("status", help="Показать текущее состояние.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    configure_logging(verbose=args.verbose)

    try:
        with process_lock():
            if args.command == "setup":
                setup_beta(dry_run=args.dry_run)
            elif args.command == "promote":
                promote_beta(
                    dry_run=args.dry_run,
                    keep_beta=args.keep_beta,
                    force=args.force,
                )
            elif args.command == "rollback":
                rollback_beta(dry_run=args.dry_run)
            elif args.command == "restore-main":
                restore_last_main(dry_run=args.dry_run)
            elif args.command == "status":
                status()
            else:
                parser.error(f"Неизвестная команда: {args.command}")
        return 0

    except BetaManagerError as e:
        logging.error("%s", e)
        print(f"❌ {e}")
        return 2
    except Exception as e:
        logging.exception("Непредвиденная ошибка")
        print(f"❌ Непредвиденная ошибка: {e}")
        return 3


if __name__ == "__main__":
    raise SystemExit(main())