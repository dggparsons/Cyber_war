#!/bin/bash
# SSL Deployment Debugging Script
# Run this on the VM via: ssh azureuser@20.127.99.1 'bash -s' < debug-ssl.sh

echo "========================================"
echo "  SSL Deployment Debug Report"
echo "========================================"
echo ""

echo "1. Container Status:"
echo "-------------------"
cd ~/Cyber_war
sudo docker compose -f docker-compose.ssl.yml ps
echo ""

echo "2. Caddy Logs (last 50 lines):"
echo "-------------------------------"
sudo docker compose -f docker-compose.ssl.yml logs --tail=50 caddy
echo ""

echo "3. Backend Health Check (internal):"
echo "------------------------------------"
sudo docker compose -f docker-compose.ssl.yml exec -T backend curl -s http://localhost:5050/api/health/ || echo "Backend not responding"
echo ""

echo "4. Frontend Check (internal):"
echo "------------------------------"
sudo docker compose -f docker-compose.ssl.yml exec -T caddy curl -s http://frontend:80 | head -c 100
echo ""

echo "5. Port Listening Status:"
echo "-------------------------"
sudo netstat -tulpn | grep -E ':(80|443|5050|4173)'
echo ""

echo "6. DNS Resolution Test:"
echo "-----------------------"
nslookup un.blorebank.net
echo ""

echo "7. Caddy Config Check:"
echo "----------------------"
cat ~/Cyber_war/Caddyfile
echo ""

echo "8. Docker Networks:"
echo "-------------------"
sudo docker network ls
sudo docker network inspect cyber_war_default 2>/dev/null | grep -A 5 "Containers" || echo "No network found"
echo ""

echo "========================================"
echo "  Debug Report Complete"
echo "========================================"

