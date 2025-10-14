Step 1: Make sure the script is executable
bashchmod +x ~/projects/custom_services/pi_eink_hat_info/eink_final.py
Step 2: Create the systemd service file
bashsudo nano /etc/systemd/system/eink-display.service
Paste this:
ini[Unit]
Description=E-Ink Display Status Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/projects/custom_services/pi_eink_hat_info
ExecStart=/usr/bin/python3 /home/pi/projects/custom_services/pi_eink_hat_info/eink_final.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
Save with Ctrl+X, Y, Enter.
Step 3: Enable and start the service
bash# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable the service to start on boot
sudo systemctl enable eink-display.service

# Start the service now
sudo systemctl start eink-display.service
Step 4: Check if it's running
bashsudo systemctl status eink-display.service
You should see active (running) in green!
Useful Commands
Stop the service:
bashsudo systemctl stop eink-display.service
Restart the service:
bashsudo systemctl restart eink-display.service
View live logs:
bashjournalctl -u eink-display.service -f
View recent logs:
bashjournalctl -u eink-display.service -n 50
Disable auto-start on boot:
bashsudo systemctl disable eink-display.service
Test it works on reboot
bashsudo reboot
After the Pi reboots, SSH back in and check:
bashsudo systemctl status eink-display.service
