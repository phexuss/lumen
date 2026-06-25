# HDRezka Telegram Bot - Production

🎬 Telegram бот для стриминга фильмов и сериалов из HDRezka напрямую в Telegram.

## 🚀 Быстрый Деплой

```bash
# На VPS
cd bot
cp .env.prod.example .env.prod
nano .env.prod  # Заполнить BOT_TOKEN, PUBLIC_URL
./deploy.sh
```

Готово! Бот запущен.

---

## 📋 Требования

- VPS с Docker
- Cloudflare аккаунт (для туннеля)
- Telegram Bot Token

---

## ⚙️ Настройка

### 1. Cloudflare Tunnel

```bash
cloudflared tunnel login
cloudflared tunnel create rezkabot
cloudflared tunnel route dns TUNNEL_ID bot.yourdomain.com
sudo cloudflared service install
```

Подробнее: [CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md)

### 2. Конфигурация

Скопируй `.env.prod.example` в `.env.prod`:

```env
BOT_TOKEN=your_bot_token
PUBLIC_URL=https://bot.yourdomain.com
ADMIN_IDS=your_telegram_id
```

### 3. Запуск

```bash
./deploy.sh
```

Или вручную:
```bash
docker compose -f docker-compose.prod.yml up -d
```

---

## 📊 Управление

```bash
# Логи
docker compose -f docker-compose.prod.yml logs -f

# Статус
docker compose -f docker-compose.prod.yml ps

# Перезапуск
docker compose -f docker-compose.prod.yml restart

# Остановка
docker compose -f docker-compose.prod.yml down
```

---

## 🎯 Возможности

✅ Поиск фильмов и сериалов  
✅ Выбор качества (360p-1080p)  
✅ Множественные переводы  
✅ Встроенный плеер Telegram с seeking  
✅ Кэширование для быстрого повтора  
✅ Автоматический рестарт  

---

## 🔧 Порты

По умолчанию: `8080`

Изменить в `docker-compose.prod.yml`:
```yaml
ports:
  - "8090:8080"
```

И в cloudflared config:
```yaml
service: http://localhost:8090
```

---

## 📖 Документация

- [PRODUCTION_DEPLOY.md](PRODUCTION_DEPLOY.md) - Полная инструкция деплоя
- [CLOUDFLARE_TUNNEL.md](CLOUDFLARE_TUNNEL.md) - Настройка Cloudflare

---

**Версия:** 2.0 Production  
**Дата:** 2026-06-25  
**Статус:** ✅ Production Ready
