# 🚀 Полный Гайд: Деплой HDRezka Telegram Bot на VPS

**От нуля до работающего бота за 15 минут**

---

## 📋 Что Потребуется

- VPS (Ubuntu/Debian) с минимум 512MB RAM
- Домен (или можно без него)
- Cloudflare аккаунт (бесплатный)
- Telegram Bot Token

---

## Шаг 1: Подготовка VPS

### 1.1 Подключиться к VPS

```bash
ssh root@your-vps-ip
```

### 1.2 Обновить систему

```bash
apt update && apt upgrade -y
```

### 1.3 Установить Docker

```bash
# Установка Docker
curl -fsSL https://get.docker.com | sh

# Запустить Docker
systemctl enable docker
systemctl start docker

# Проверить
docker --version
docker compose version
```

Должно вывести:
```
Docker version 24.x.x
Docker Compose version v2.x.x
```

---

## Шаг 2: Загрузить Код на VPS

### Вариант A: Через Git (если есть репозиторий)

```bash
cd /opt
git clone https://your-repo.git rezkabot
cd rezkabot/bot
```

### Вариант B: Через SCP (с локальной машины)

**На локальной машине:**
```bash
cd /home/phexuss/Desktop/px-landing
scp -r bot/ root@your-vps-ip:/opt/rezkabot/
```

**На VPS:**
```bash
cd /opt/rezkabot
ls -la
```

Должны видеть:
```
main.py
config.py
server.py
handlers.py
docker-compose.prod.yml
Dockerfile.prod
...
```

---

## Шаг 3: Настроить Cloudflare Tunnel

### 3.1 Установить cloudflared

```bash
# Скачать
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared

# Сделать исполняемым
chmod +x cloudflared

# Переместить в систему
mv cloudflared /usr/local/bin/

# Проверить
cloudflared --version
```

### 3.2 Авторизоваться в Cloudflare

```bash
cloudflared tunnel login
```

**Это откроет ссылку в консоли вида:**
```
https://dash.cloudflare.com/argotunnel?...
```

**Действия:**
1. Скопируй эту ссылку
2. Открой в браузере
3. Войди в Cloudflare
4. Выбери свой домен (или создай новый)
5. Нажми "Authorize"
6. Вернись в терминал

Должно вывести:
```
You have successfully logged in.
```

### 3.3 Создать туннель

```bash
cloudflared tunnel create rezkabot
```

**Вывод будет примерно:**
```
Created tunnel rezkabot with id abc123-def456-ghi789
```

**⚠️ ВАЖНО: Скопируй этот ID!** Назовём его `TUNNEL_ID`

### 3.4 Настроить DNS (С доменом)

**Если у тебя есть домен:**

```bash
cloudflared tunnel route dns TUNNEL_ID bot.yourdomain.com
```

Замени:
- `TUNNEL_ID` - твой ID из шага 3.3
- `bot.yourdomain.com` - твой поддомен

**Вывод:**
```
2026-06-25T12:15:00Z INF Added CNAME bot.yourdomain.com which will route to this tunnel
```

### 3.5 Создать конфигурацию

```bash
# Создать директорию
mkdir -p ~/.cloudflared

# Создать конфиг
nano ~/.cloudflared/config.yml
```

**Вставь (замени TUNNEL_ID на свой):**

```yaml
tunnel: TUNNEL_ID
credentials-file: /root/.cloudflared/TUNNEL_ID.json

ingress:
  - hostname: bot.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
```

**Если НЕТ домена** (используй trycloudflare):
```yaml
tunnel: TUNNEL_ID
credentials-file: /root/.cloudflared/TUNNEL_ID.json

ingress:
  - service: http://localhost:8080
```

Сохрани: `Ctrl+O`, `Enter`, `Ctrl+X`

### 3.6 Запустить туннель как сервис

```bash
# Установить как сервис
cloudflared service install

# Запустить
systemctl start cloudflared

# Включить автозапуск
systemctl enable cloudflared

# Проверить статус
systemctl status cloudflared
```

Должно быть `Active: active (running)`

### 3.7 Получить публичный URL

**Если с доменом:**
```
https://bot.yourdomain.com
```

**Если без домена:**
```bash
# Проверить логи
journalctl -u cloudflared -f
```

Найди строку вида:
```
https://abc-def-ghi.trycloudflare.com
```

**Это твой PUBLIC_URL!** Скопируй его.

---

## Шаг 4: Настроить Bot Token

### 4.1 Получить токен (если нет)

1. Открой Telegram
2. Найди **@BotFather**
3. Отправь `/newbot`
4. Следуй инструкциям
5. Скопируй токен вида: `123456789:ABC-DEF...`

### 4.2 Получить свой Telegram ID

1. Открой Telegram
2. Найди **@userinfobot**
3. Отправь `/start`
4. Скопируй свой ID (число)

---

## Шаг 5: Настроить Environment

### 5.1 Создать .env.prod

```bash
cd /opt/rezkabot

# Скопировать пример
cp .env.prod.example .env.prod

# Редактировать
nano .env.prod
```

### 5.2 Заполнить данные

```env
# Твой Bot Token от BotFather
BOT_TOKEN=123456789:ABC-DEF...

# Твой публичный URL из шага 3.7
PUBLIC_URL=https://bot.yourdomain.com

# Твой Telegram ID из шага 4.2
ADMIN_IDS=123456789

# Остальное можно не трогать (или изменить зеркало если нужно)
REZKA_MIRROR=https://hdrezka-home.tv
```

Сохрани: `Ctrl+O`, `Enter`, `Ctrl+X`

---

## Шаг 6: Запустить Бота

### 6.1 Запустить через deploy.sh

```bash
cd /opt/rezkabot

# Сделать скрипт исполняемым
chmod +x deploy.sh

# Запустить
./deploy.sh
```

Или вручную:

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d
```

### 6.2 Проверить запуск

```bash
# Проверить контейнер
docker ps

# Должен быть запущен: rezkabot
```

### 6.3 Смотреть логи

```bash
docker compose -f docker-compose.prod.yml logs -f
```

**Должно быть:**
```
============================================================
HDRezka Telegram Bot Starting
============================================================
Bot: @123456789...
FastAPI: 0.0.0.0:8080
Public URL: https://bot.yourdomain.com
Rezka Mirror: https://hdrezka-home.tv
Cache: memory (enabled)
============================================================
INFO:     Started server process [1]
INFO:     Uvicorn running on http://0.0.0.0:8080
Start polling for bot...
```

---

## Шаг 7: Проверка

### 7.1 Проверить Health Endpoint

```bash
# Локально
curl http://localhost:8080/health

# Должно вернуть:
{"status":"ok","service":"hdrezka-proxy"}
```

### 7.2 Проверить публичный URL

```bash
curl https://bot.yourdomain.com/health
```

Тот же ответ!

### 7.3 Проверить в Telegram

1. Открой Telegram
2. Найди своего бота (имя из BotFather)
3. Отправь `/start`

**Должен ответить:**
```
🎬 Welcome to HDRezka Streaming Bot!

Send me a movie or series name to search.
Example: Inception
...
```

### 7.4 Протестировать поиск

Отправь боту:
```
deadpool
```

**Должен ответить:**
```
📋 Found X results for 'deadpool':
Select a title to watch:

[1] Дэдпул ⭐ 7.59
[2] Дэдпул 2 ⭐ 7.42
...
```

✅ **РАБОТАЕТ!**

---

## 🎉 Готово!

Бот запущен и работает! Теперь можешь:

- Искать фильмы
- Выбирать качество
- Смотреть прямо в Telegram
- Или получать ссылки для браузера

---

## 📊 Управление Ботом

### Просмотр логов
```bash
cd /opt/rezkabot
docker compose -f docker-compose.prod.yml logs -f
```

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
cd /opt/rezkabot
git pull  # или scp новый код
docker compose -f docker-compose.prod.yml up -d --build
```

### Очистка кэша
```bash
rm -f data/cache.db
docker compose -f docker-compose.prod.yml restart
```

---

## 🔧 Если Порт 8080 Занят

### Изменить порт

Отредактируй `docker-compose.prod.yml`:
```bash
nano docker-compose.prod.yml
```

Найди:
```yaml
ports:
  - "8080:8080"
```

Измени на:
```yaml
ports:
  - "8090:8080"  # Или любой свободный порт
```

И обнови cloudflared config:
```bash
nano ~/.cloudflared/config.yml
```

Измени:
```yaml
service: http://localhost:8090  # Новый порт
```

Перезапусти:
```bash
systemctl restart cloudflared
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 🐛 Troubleshooting

### Бот не запускается

```bash
# Проверить логи
docker compose -f docker-compose.prod.yml logs

# Пересоздать контейнер
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build --force-recreate
```

### Cloudflare Tunnel не работает

```bash
# Проверить статус
systemctl status cloudflared

# Проверить логи
journalctl -u cloudflared -f

# Перезапустить
systemctl restart cloudflared
```

### Health endpoint не отвечает

```bash
# Проверить что контейнер запущен
docker ps

# Проверить порт
netstat -tlnp | grep 8080

# Проверить firewall
ufw status
ufw allow 8080/tcp
```

### HDRezka заблокирован на VPS

Добавь прокси в `.env.prod`:
```env
REZKA_PROXY_URL=socks5://your-proxy:1080
```

Перезапусти:
```bash
docker compose -f docker-compose.prod.yml restart
```

### Видео не работает в Telegram

1. Проверь что PUBLIC_URL правильный
2. Проверь что cloudflare tunnel работает: `curl https://bot.yourdomain.com/health`
3. Проверь логи бота: `docker logs rezkabot`

Если всё равно не работает - бот отправит ссылку текстом (fallback)

---

## 🔒 Безопасность

### Firewall

```bash
# Установить ufw
apt install ufw

# Открыть SSH
ufw allow 22/tcp

# НЕ открывать 8080 (работает через Cloudflare Tunnel)

# Включить
ufw enable
```

### Обновления

```bash
# Регулярно обновлять систему
apt update && apt upgrade -y

# Обновлять Docker образы
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Бэкап

```bash
# Бэкап конфигурации
tar -czf rezkabot-backup-$(date +%Y%m%d).tar.gz \
  .env.prod \
  data/ \
  ~/.cloudflared/

# Сохранить куда-то безопасно
scp rezkabot-backup-*.tar.gz user@backup-server:/backups/
```

---

## 📈 Мониторинг

### Использование ресурсов

```bash
# CPU/RAM
docker stats rezkabot

# Логи в реальном времени
docker logs -f rezkabot

# Размер кэша
du -h data/cache.db
```

### Автозапуск

Уже настроен через:
- `restart: unless-stopped` в docker-compose
- `systemctl enable cloudflared`

При перезагрузке VPS всё запустится автоматически!

---

## 🎯 Итоговая Проверка

✅ VPS настроен  
✅ Docker установлен  
✅ Cloudflare Tunnel работает  
✅ Бот запущен  
✅ Health endpoint отвечает  
✅ Бот отвечает в Telegram  
✅ Поиск работает  
✅ Видео отправляется  

**🎉 Всё готово!**

---

**Время деплоя:** 15-20 минут  
**Сложность:** Средняя  
**Версия:** 2.0 Production  
**Дата:** 2026-06-25

---

## 📞 Помощь

Если что-то не работает:

1. Проверь логи: `docker logs -f rezkabot`
2. Проверь cloudflare: `journalctl -u cloudflared -f`
3. Проверь health: `curl http://localhost:8080/health`
4. Проверь публичный URL: `curl https://bot.yourdomain.com/health`

Всё работает - кайфуй! 🚀
