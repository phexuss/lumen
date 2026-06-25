# HDRezka Telegram Bot - Production Deployment

## 🚀 Быстрый Деплой на VPS

### Предварительные Требования

- VPS с Docker и Docker Compose
- Cloudflare аккаунт
- Telegram Bot Token
- Домен (опционально, можно использовать Cloudflare Tunnel URL)

---

## Шаг 1: Подготовка VPS

```bash
# Подключиться к VPS
ssh user@your-vps-ip

# Установить Docker и Docker Compose
curl -fsSL https://get.docker.com | sh
sudo systemctl enable docker
sudo systemctl start docker

# Добавить пользователя в группу docker
sudo usermod -aG docker $USER
newgrp docker

# Проверить установку
docker --version
docker compose version
```

---

## Шаг 2: Загрузить Код на VPS

```bash
# Склонировать репозиторий
cd ~
git clone <your-repo-url> rezkabot
cd rezkabot/bot

# Или загрузить через scp
# scp -r bot/ user@vps:/home/user/rezkabot/
```

---

## Шаг 3: Настроить Cloudflare Tunnel

### Вариант A: С доменом

```bash
# Установить cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Авторизоваться
cloudflared tunnel login

# Создать туннель
cloudflared tunnel create rezkabot

# Настроить DNS
cloudflared tunnel route dns rezkabot bot.yourdomain.com

# Создать конфиг
cat > ~/.cloudflared/config.yml << EOF
tunnel: <tunnel-id>
credentials-file: /home/$USER/.cloudflared/<tunnel-id>.json

ingress:
  - hostname: bot.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
EOF

# Запустить как сервис
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared
```

### Вариант B: Без домена (Временный URL)

```bash
# Запустить в фоне
cloudflared tunnel --url http://localhost:8080 > tunnel.log 2>&1 &

# Получить URL
grep -oP 'https://[^\s]+\.trycloudflare\.com' tunnel.log

# Скопировать этот URL для PUBLIC_URL
```

---

## Шаг 4: Настроить Environment

```bash
cd ~/rezkabot/bot

# Создать production .env
cp .env.prod.example .env.prod

# Отредактировать
nano .env.prod
```

Заполнить:
```env
BOT_TOKEN=ваш_токен_бота
PUBLIC_URL=https://bot.yourdomain.com  # или cloudflare tunnel URL
ADMIN_IDS=ваш_telegram_id
```

---

## Шаг 5: Запустить Контейнер

```bash
# Собрать и запустить
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Проверить логи
docker compose -f docker-compose.prod.yml logs -f

# Проверить статус
docker compose -f docker-compose.prod.yml ps
```

---

## Шаг 6: Проверка

```bash
# Health check
curl http://localhost:8080/health

# Проверить через публичный URL
curl https://bot.yourdomain.com/health

# Логи бота
docker compose -f docker-compose.prod.yml logs -f rezkabot
```

В Telegram:
1. Найти бота
2. `/start`
3. Отправить название фильма
4. Получить ссылки!

---

## Управление

### Перезапуск
```bash
docker compose -f docker-compose.prod.yml restart
```

### Остановка
```bash
docker compose -f docker-compose.prod.yml down
```

### Обновление кода
```bash
git pull
docker compose -f docker-compose.prod.yml up -d --build
```

### Просмотр логов
```bash
# Все логи
docker compose -f docker-compose.prod.yml logs -f

# Последние 100 строк
docker compose -f docker-compose.prod.yml logs --tail=100

# Только бот
docker compose -f docker-compose.prod.yml logs -f rezkabot
```

### Очистка кэша
```bash
# Удалить файл кэша
rm -f data/cache.db

# Перезапустить
docker compose -f docker-compose.prod.yml restart
```

---

## Смена Портов (если 8080 занят)

Отредактировать `docker-compose.prod.yml`:
```yaml
ports:
  - "8090:8080"  # Внешний:Внутренний
```

И обновить cloudflared config:
```yaml
service: http://localhost:8090
```

---

## Мониторинг

### Проверка работы
```bash
# Статус контейнера
docker compose -f docker-compose.prod.yml ps

# Использование ресурсов
docker stats rezkabot

# Health check
watch -n 5 'curl -s http://localhost:8080/health'
```

### Автоматический рестарт
Уже настроен через `restart: unless-stopped` в docker-compose

---

## Troubleshooting

### Бот не запускается
```bash
# Проверить логи
docker compose -f docker-compose.prod.yml logs rezkabot

# Проверить .env
cat .env.prod

# Пересобрать контейнер
docker compose -f docker-compose.prod.yml up -d --build --force-recreate
```

### Cloudflare Tunnel не работает
```bash
# Проверить статус
sudo systemctl status cloudflared

# Перезапустить
sudo systemctl restart cloudflared

# Логи
sudo journalctl -u cloudflared -f
```

### Порт занят
```bash
# Найти процесс
sudo lsof -i :8080

# Убить процесс
sudo kill -9 <PID>

# Или изменить порт в docker-compose.prod.yml
```

### HDRezka заблокирован на VPS
Добавить прокси в `.env.prod`:
```env
REZKA_PROXY_URL=socks5://your-proxy:1080
```

---

## Бэкап и Восстановление

### Бэкап кэша
```bash
cp data/cache.db data/cache.db.backup
```

### Бэкап конфигурации
```bash
tar -czf rezkabot-backup.tar.gz .env.prod data/
```

### Восстановление
```bash
tar -xzf rezkabot-backup.tar.gz
docker compose -f docker-compose.prod.yml restart
```

---

## Безопасность

```bash
# Firewall
sudo ufw allow 22/tcp
sudo ufw allow 8080/tcp
sudo ufw enable

# Ограничить доступ к .env
chmod 600 .env.prod

# Обновления системы
sudo apt update && sudo apt upgrade -y
```

---

## Полный Рестарт (если что-то сломалось)

```bash
cd ~/rezkabot/bot

# Остановить и удалить
docker compose -f docker-compose.prod.yml down -v

# Пересобрать с нуля
docker compose -f docker-compose.prod.yml build --no-cache

# Запустить
docker compose -f docker-compose.prod.yml up -d

# Проверить логи
docker compose -f docker-compose.prod.yml logs -f
```

---

**Время деплоя:** ~10-15 минут  
**Требования:** 1 CPU, 512MB RAM минимум  
**Версия:** 2.0 (Production)  
**Дата:** 2026-06-25
