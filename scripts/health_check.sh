#!/bin/bash

echo "========================================"
echo "      CareerDev AI Health Check"
echo "========================================"
date
echo ""

# 1. Check Docker Containers
echo "[1] Checking Docker Containers..."
if command -v docker &> /dev/null; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
else
    echo "⚠️  Docker command not found!"
fi
echo ""

# 2. Check Ports (80 & 443)
echo "[2] Checking Listening Ports (80 & 443)..."
if command -v netstat &> /dev/null; then
    netstat -tuln | grep -E ':80|:443' || echo "⚠️  Ports 80/443 not found via netstat."
elif command -v ss &> /dev/null; then
    ss -tuln | grep -E ':80|:443' || echo "⚠️  Ports 80/443 not found via ss."
else
    echo "⚠️  Neither 'netstat' nor 'ss' found."
fi
echo ""

# 3. Check SSL Certificate
echo "[3] Checking SSL Certificate (careerdev-ai.online)..."
TARGET="careerdev-ai.online"
# Try to connect locally first if DNS points elsewhere, otherwise use domain
# Since we are on the server (presumably), we might want to check localhost:443 if domain is not yet propagated.
# But user requirement is "SSL Check".
timeout 5 openssl s_client -connect $TARGET:443 -servername $TARGET 2>/dev/null | openssl x509 -noout -dates || echo "⚠️  Could not retrieve SSL certificate from $TARGET"
echo ""

# 4. Tail Logs
echo "[4] Tailing Logs (Last 50 lines)..."
echo "--- APP Container ---"
docker logs --tail 50 app 2>&1 || echo "⚠️  Could not read logs for 'app'"
echo ""
echo "--- Webserver Container ---"
docker logs --tail 50 webserver 2>&1 || echo "⚠️  Could not read logs for 'webserver'"

echo ""
echo "========================================"
echo "Health Check Complete."
