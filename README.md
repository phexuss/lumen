# Lumen Movie Bot

🎬 Telegram бот для стриминга фильмов и сериалов из HDRezka напрямую в Telegram.

## ✨ Возможности

- 🔍 Поиск фильмов и сериалов
- 🎥 Встроенный плеер Telegram с seeking/rewinding
- 📺 Множественные качества (360p-1080p)
- 🌐 Выбор переводов и озвучек
- 💾 Кэширование для быстрого повтора
- 🐳 Docker деплой одной командой
- 🔒 Cloudflare Tunnel для HTTPS

## 🚀 Быстрый Старт

```bash
cd bot
cp .env.prod.example .env.prod
nano .env.prod  # Заполнить BOT_TOKEN, PUBLIC_URL
./deploy.sh
```

## 📖 Документация

- [FULL_DEPLOY_GUIDE.md](bot/FULL_DEPLOY_GUIDE.md) - Полный гайд деплоя (15 минут)
- [CLOUDFLARE_TUNNEL.md](bot/CLOUDFLARE_TUNNEL.md) - Настройка Cloudflare
- [PRODUCTION_DEPLOY.md](bot/PRODUCTION_DEPLOY.md) - Production best practices

## 🏗️ Структура

```
.
├── bot/                    # Telegram bot application
│   ├── main.py            # Entry point
│   ├── config.py          # Configuration
│   ├── server.py          # FastAPI streaming proxy
│   ├── handlers.py        # Telegram handlers
│   ├── services/          # Business logic
│   ├── cache/             # Caching layer
│   └── docker-compose.prod.yml
└── HdRezkaApi/            # HDRezka library
```

## 🛠️ Технологии

- Python 3.11+
- aiogram 3.x (Telegram Bot)
- FastAPI (Streaming proxy)
- Docker & Docker Compose
- Cloudflare Tunnel (HTTPS)
- SQLite (Caching)

## 📋 Требования

- VPS с Docker
- Cloudflare аккаунт
- Telegram Bot Token

## 🎯 Деплой на Production

Полный гайд: [FULL_DEPLOY_GUIDE.md](bot/FULL_DEPLOY_GUIDE.md)

**Кратко:**
1. Настроить Cloudflare Tunnel
2. Скопировать код на VPS
3. Настроить `.env.prod`
4. Запустить `./deploy.sh`
5. Готово! 🎉

## 📊 Управление

```bash
# Логи
docker compose -f bot/docker-compose.prod.yml logs -f

# Перезапуск
docker compose -f bot/docker-compose.prod.yml restart

# Остановка
docker compose -f bot/docker-compose.prod.yml down
```

## 🤝 Contributing

Pull requests приветствуются!

## 📄 License

MIT

## 🙏 Credits

- [HdRezkaApi](https://github.com/SuperZombi/HdRezkaApi) - HDRezka library
- [aiogram](https://github.com/aiogram/aiogram) - Telegram Bot framework
- [FastAPI](https://github.com/tiangolo/fastapi) - Web framework

---

**Version:** 2.0  
**Status:** Production Ready ✅
