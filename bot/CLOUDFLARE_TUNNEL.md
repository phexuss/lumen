## Cloudflare Tunnel Setup Guide

### Метод 1: С Доменом (Рекомендуется)

```bash
# Установить cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared
sudo mv cloudflared /usr/local/bin/

# Авторизоваться (откроется браузер)
cloudflared tunnel login

# Создать туннель
cloudflared tunnel create rezkabot

# Получить tunnel ID
cloudflared tunnel list

# Настроить DNS (замени TUNNEL_ID и твой домен)
cloudflared tunnel route dns TUNNEL_ID bot.yourdomain.com

# Создать конфигурацию
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: TUNNEL_ID
credentials-file: /root/.cloudflared/TUNNEL_ID.json

ingress:
  - hostname: bot.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
EOF

# Запустить как сервис
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Проверить
sudo systemctl status cloudflared
```

В `.env.prod` установи:
```
PUBLIC_URL=https://bot.yourdomain.com
```

---

### Метод 2: Без Домена (Quick Test)

```bash
# Запустить временный туннель
cloudflared tunnel --url http://localhost:8080
```

Скопируй URL вида `https://random-name.trycloudflare.com` и установи в `.env.prod`:
```
PUBLIC_URL=https://random-name.trycloudflare.com
```

⚠️ **Внимание:** Этот URL временный! Для продакшена используй метод 1.

---

### Проверка

```bash
# Проверить что туннель работает
curl https://bot.yourdomain.com/health

# Должно вернуть:
# {"status":"ok","service":"hdrezka-proxy"}
```

---

### Troubleshooting

**Туннель не запускается:**
```bash
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f
```

**DNS не работает:**
- Подожди 5-10 минут для распространения DNS
- Проверь: `dig bot.yourdomain.com`

**403 Forbidden:**
- Проверь что бот запущен: `docker ps`
- Проверь порт: `curl http://localhost:8080/health`
