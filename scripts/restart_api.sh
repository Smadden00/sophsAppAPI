#!/bin/bash

# Script to shutdown and rebuild gunicorn for the API via systemd
# Usage: ./restart_api.sh
# Note: Requires sudo privileges for systemd service management

echo "======================================"
echo "Restarting API with Gunicorn"
echo "======================================"

# Configuration
APP_DIR="/home/ec2-user/sophsAppAPI"
SERVICE_NAME="sophsAppApi"
BIND_ADDRESS="127.0.0.1:5000"

# Step 1: Check service status before restart
echo ""
echo "Step 1: Checking current service status..."
sudo systemctl status $SERVICE_NAME --no-pager | head -n 10 || true

# Step 2: Activate virtual environment and update dependencies (optional)
echo ""
echo "Step 2: Updating dependencies..."

cd "$APP_DIR"

if [ -d "$APP_DIR/venv" ]; then
    echo "Activating virtual environment..."
    source "$APP_DIR/venv/bin/activate"
else
    echo "Warning: No virtual environment found. Using system Python."
fi

# Step 3: Restart the systemd service
echo ""
echo "Step 3: Restarting systemd service..."
sudo systemctl restart $SERVICE_NAME

# Wait for service to stabilize
echo "Waiting for service to start..."
sleep 3

# Step 4: Verify service is running
echo ""
echo "Step 4: Verifying service status..."
if sudo systemctl is-active --quiet $SERVICE_NAME; then
    echo ""
    echo "======================================"
    echo "✅ API successfully restarted!"
    echo "======================================"
    echo "Service: $SERVICE_NAME"
    echo "Binding: http://$BIND_ADDRESS"
    echo "Public access: via Nginx reverse proxy"
    echo ""
    echo "Useful commands:"
    echo "  Status:       sudo systemctl status $SERVICE_NAME"
    echo "  Stop:         sudo systemctl stop $SERVICE_NAME"
    echo "  Logs (live):  sudo journalctl -u $SERVICE_NAME -f"
    echo "  Logs (last):  sudo journalctl -u $SERVICE_NAME -n 100"
    echo "  Health check: curl http://$BIND_ADDRESS/api/health"
    echo ""
    
    # Show recent logs
    echo "Recent logs:"
    echo "---"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
else
    echo ""
    echo "❌ Error: Service failed to start!"
    echo ""
    echo "View detailed error logs with:"
    echo "  sudo journalctl -u $SERVICE_NAME -n 50 --no-pager"
    exit 1
fi
