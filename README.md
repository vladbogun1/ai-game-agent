# AI Game Agent

ИИ-агент для управления игрой на Windows через анализ изображения экрана и управление клавиатурой/мышью.

## Возможности

- Захват экрана (Desktop Duplication API через `mss`).
- Быстрое свёрнутое «состояние кадра» вместо передачи сырых изображений в LLM.
- Управление клавиатурой и мышью (через `pynput`).
- Поддержка Ollama для локальных LLM-моделей.

## Требования

- Windows 10/11
- NVIDIA GPU (рекомендуется RTX 4070+)
- Python 3.11+
- Установленный Ollama

## Установка

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Настройка Ollama

1. Установите Ollama: https://ollama.com/
2. Запустите локальный сервер:

```bash
ollama serve
```

3. Загрузите модель с поддержкой зрения (пример):

```bash
ollama pull llava:7b
```

> Можно использовать и другие модели, например `llava:13b` или `llava:latest`, но требования к VRAM будут выше.

## Быстрый старт

Запуск в «сухом» режиме (ничего не нажимает, только логирует действия):

```bash
python main.py --dry-run \
  --model llava:7b \
  --task "mine_ore" \
  --context "start in mine, pickaxe equipped" \
  --rules "avoid enemies, return when inventory full"
```

Запуск с реальным управлением (ОСТОРОЖНО):

```bash
python main.py \
  --model llava:7b \
  --task "mine_ore" \
  --context "start in mine, pickaxe equipped" \
  --rules "avoid enemies, return when inventory full"
```

## Параметры CLI

- `--model` — имя модели Ollama (например, `llava:7b`).
- `--ollama-url` — адрес Ollama API (по умолчанию `http://localhost:11434`).
- `--task` — основная задача агента.
- `--context` — стартовый контекст.
- `--rules` — ограничения и правила.
- `--dry-run` — не управлять вводом, только логировать.
- `--monitor` — индекс монитора (1 — основной).
- `--width`, `--height` — размер анализируемого кадра.
- `--delay` — задержка между циклами.

## Безопасность

Рекомендуется сначала использовать `--dry-run` и запускать агента в тестовой среде.
