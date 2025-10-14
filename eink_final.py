#!/usr/bin/python3
# -*- coding:utf-8 -*-
import sys
import os
import time
import subprocess
from PIL import Image, ImageDraw, ImageFont
import socket
import urllib.request
import json
from waveshare_epd import epd2in13_V3

# Cycle through tabs: 15 sec Home, 10 sec System, 8 sec Connectivity
current_tab = 0
tab_durations = [20, 20, 20]  # seconds for each tab

def get_cpu_temp():
    """Get CPU temperature"""
    try:
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp = float(f.read()) / 1000.0
            return f"{temp:.1f}°C"
    except:
        return "N/A"

def get_cpu_usage():
    """Get CPU usage percentage"""
    try:
        result = subprocess.check_output(['top', '-bn1'], universal_newlines=True)
        lines = result.split('\n')
        for line in lines:
            if 'Cpu(s)' in line or '%Cpu' in line:
                parts = line.split(',')
                for part in parts:
                    if 'id' in part:
                        idle = float(part.split()[0])
                        return f"{100 - idle:.1f}%"
        return "N/A"
    except:
        return "N/A"

def get_ram_usage():
    """Get RAM usage"""
    try:
        mem = subprocess.check_output(['free', '-m'], universal_newlines=True).split('\n')[1].split()
        total = int(mem[1])
        used = int(mem[2])
        percent = (used / total) * 100
        return f"{used}/{total}MB ({percent:.0f}%)"
    except:
        return "N/A"

def get_disk_usage():
    """Get disk usage"""
    try:
        df = subprocess.check_output(['df', '-h', '/'], universal_newlines=True).split('\n')[1].split()
        return f"{df[2]}/{df[1]} ({df[4]})"
    except:
        return "N/A"

def get_wifi_status():
    """Get WiFi SSID"""
    try:
        result = subprocess.check_output(['iwgetid', '-r'], universal_newlines=True).strip()
        return result if result else "Not Connected"
    except:
        return "Not Connected"

def get_ip_address():
    """Get local IP address"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "No IP"

def is_online():
    """Check if Pi is online"""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

def get_ssh_users():
    """Get list of SSH users"""
    try:
        result = subprocess.check_output(['who'], universal_newlines=True)
        lines = [line.strip() for line in result.split('\n') if line.strip()]
        return lines if lines else ["No SSH users"]
    except:
        return ["Error"]

def scan_wifi_networks():
    """Scan for available WiFi networks with signal strength"""
    try:
        result = subprocess.check_output(['sudo', 'iwlist', 'wlan0', 'scan'], 
                                        universal_newlines=True, timeout=10)
        networks = []
        current_ssid = None
        current_quality = 0
        
        for line in result.split('\n'):
            if 'ESSID:' in line:
                ssid = line.split('ESSID:')[1].strip('"')
                if ssid:
                    current_ssid = ssid
            elif 'Quality=' in line and current_ssid:
                try:
                    quality_str = line.split('Quality=')[1].split()[0]
                    parts = quality_str.split('/')
                    quality = int(parts[0])
                    max_quality = int(parts[1])
                    quality_percent = (quality / max_quality) * 100
                    networks.append((current_ssid, quality_percent))
                    current_ssid = None
                except:
                    pass
        
        # Sort by signal strength, remove duplicates
        networks = sorted(set(networks), key=lambda x: x[1], reverse=True)
        return networks[:3] if networks else []
    except:
        return []

def get_weather():
    """Get real weather from wttr.in"""
    try:
        url = "http://wttr.in/Buffalo?format=j1"
        response = urllib.request.urlopen(url, timeout=5)
        data = json.loads(response.read().decode())
        
        current = data['current_condition'][0]
        temp_f = current['temp_F']
        condition = current['weatherDesc'][0]['value']
        
        # Shorten long conditions
        if len(condition) > 15:
            condition = condition[:12] + "..."
        
        return {
            "temp": f"{temp_f}°F",
            "condition": condition,
            "location": "Buffalo"
        }
    except:
        return {
            "temp": "??°F",
            "condition": "No data",
            "location": "Buffalo"
        }

def draw_tabs(draw, font_small, current_tab):
    """Draw tab buttons at the top"""
    tab_names = ["Home", "System", "Connect"]
    tab_width = 250 // 3
    
    for i, name in enumerate(tab_names):
        x = i * tab_width
        if i == current_tab:
            draw.rectangle([x, 0, x + tab_width - 1, 18], fill=0, outline=0)
            text_color = 255
        else:
            draw.rectangle([x, 0, x + tab_width - 1, 18], fill=255, outline=0)
            text_color = 0
        
        draw.line([x, 0, x, 18], fill=0, width=1)
        draw.line([x, 18, x + tab_width, 18], fill=0, width=1)
        
        try:
            text_bbox = draw.textbbox((0, 0), name, font=font_small)
            text_width = text_bbox[2] - text_bbox[0]
        except:
            text_width = len(name) * 6
        text_x = x + (tab_width - text_width) // 2
        draw.text((text_x, 3), name, font=font_small, fill=text_color)

def create_screen(epd, current_tab):
    """Create the screen image for current tab"""
    image = Image.new('1', (epd.height, epd.width), 255)
    draw = ImageDraw.Draw(image)
    
    try:
        font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
        font_normal = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 11)
        font_small = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)
        font_tiny = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 8)
    except:
        font_title = ImageFont.load_default()
        font_normal = ImageFont.load_default()
        font_small = ImageFont.load_default()
        font_tiny = ImageFont.load_default()
    
    draw_tabs(draw, font_small, current_tab)
    
    y = 28
    
    if current_tab == 0:  # Home Tab
        # Time (large)
        current_time = time.strftime("%H:%M:%S")
        draw.text((10, y), current_time, font=font_title, fill=0)
        y += 25
        
        # Day of week
        draw.text((10, y), time.strftime("%A"), font=font_normal, fill=0)
        y += 15
        
        # Date
        draw.text((10, y), time.strftime("%B %d, %Y"), font=font_small, fill=0)
        y += 18
        
        # Timezone
        draw.text((10, y), f"Timezone: {time.strftime('%Z (UTC%z)')}", font=font_small, fill=0)
        y += 18
        
        # Separator line
        draw.line([5, y, 245, y], fill=0, width=1)
        y += 5
        
        # Weather - all in one line: Buffalo | 65°F | Partly cloudy
        weather = get_weather()
        weather_line = f"{weather['location']} | {weather['temp']} | {weather['condition']}"
        draw.text((10, y), weather_line, font=font_small, fill=0)
        
    elif current_tab == 1:  # System Tab
        # Online status
        status = "● ONLINE" if is_online() else "○ OFFLINE"
        draw.text((5, y), status, font=font_normal, fill=0)
        y += 18
        
        # IP Address
        draw.text((5, y), f"IP: {get_ip_address()}", font=font_small, fill=0)
        y += 16
        
        # Separator
        draw.line([5, y, 245, y], fill=0, width=1)
        y += 4
        
        # CPU
        draw.text((5, y), f"CPU: {get_cpu_usage()}", font=font_small, fill=0)
        y += 13
        
        # Temperature
        draw.text((5, y), f"Temp: {get_cpu_temp()}", font=font_small, fill=0)
        y += 15
        
        # RAM and Disk on same line with icons
        ram = get_ram_usage()
        disk = get_disk_usage()
        draw.text((5, y), f"💾 {ram}", font=font_tiny, fill=0)
        y += 11
        draw.text((5, y), f"💿 {disk}", font=font_tiny, fill=0)
        
    elif current_tab == 2:  # Connectivity Tab
        # WiFi and IP on same line
        wifi = get_wifi_status()
        ip = get_ip_address()
        
        if wifi == "Not Connected":
            wifi_line = f"WiFi: Not Connected | {ip}"
        else:
            wifi_display = wifi[:15] if len(wifi) > 15 else wifi
            wifi_line = f"{wifi_display} | {ip}"
        
        draw.text((5, y), wifi_line, font=font_normal, fill=0)
        y += 16
        
        # Separator
        draw.line([5, y, 245, y], fill=0, width=1)
        y += 4
        
        # SSH Sessions
        draw.text((5, y), "SSH Sessions:", font=font_small, fill=0)
        y += 12
        ssh_users = get_ssh_users()
        for user in ssh_users[:2]:
            draw.text((8, y), user[:32], font=font_tiny, fill=0)
            y += 10
        
        y += 4
        
        # Separator
        draw.line([5, y, 245, y], fill=0, width=1)
        y += 4
        
        # Nearby networks with signal strength
        draw.text((5, y), "Nearby Networks:", font=font_small, fill=0)
        y += 12
        
        networks = scan_wifi_networks()
        if not networks:
            draw.text((8, y), "Scanning...", font=font_tiny, fill=0)
        else:
            # Show top 2-3 networks
            max_networks = 3 if wifi == "Not Connected" else 2
            
            for ssid, strength in networks[:max_networks]:
                # Signal strength bars
                bars = int(strength / 25)  # 0-4 bars
                signal = "▂" * max(1, bars) + "▁" * (4 - bars)
                
                ssid_display = ssid[:20] if len(ssid) > 20 else ssid
                draw.text((8, y), f"{signal} {ssid_display}", font=font_tiny, fill=0)
                y += 10
        
        y += 3
        
        # Instructions
        draw.line([5, y, 245, y], fill=0, width=1)
        y += 4
        draw.text((5, y), "Connect: sudo raspi-config", font=font_tiny, fill=0)
    
    # Rotate image 180 degrees (flip upside down)
    image = image.rotate(180)
    
    return image

def main():
    global current_tab
    
    try:
        print("=" * 50)
        print("E-INK RASPBERRY PI STATUS MONITOR")
        print("=" * 50)
        print("\nInitializing e-Paper display...")
        epd = epd2in13_V3.EPD()
        epd.init()
        epd.Clear()
        
        print("✓ Display initialized successfully!")
        print("\nAuto-rotating tabs:")
        print("  • Home (time/date/weather): 15 seconds")
        print("  • System (stats): 10 seconds")
        print("  • Connectivity (WiFi/SSH): 8 seconds")
        print("\nPress Ctrl+C to stop")
        print("=" * 50)
        print()
        
        while True:
            # Draw current tab
            tab_name = ["Home", "System", "Connectivity"][current_tab]
            duration = tab_durations[current_tab]
            
            print(f"[{time.strftime('%H:%M:%S')}] Displaying {tab_name} tab for {duration}s...")
            
            image = create_screen(epd, current_tab)
            epd.display(epd.getbuffer(image))
            
            # Wait for tab duration
            time.sleep(duration)
            
            # Switch to next tab
            current_tab = (current_tab + 1) % 3
        
    except KeyboardInterrupt:
        print("\n\n" + "=" * 50)
        print("Shutting down...")
        try:
            epd.Clear()
            epd.sleep()
            print("✓ Display cleared and put to sleep")
        except:
            pass
        epd2in13_V3.epdconfig.module_exit()
        print("✓ Cleanup complete")
        print("=" * 50)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        epd2in13_V3.epdconfig.module_exit()

if __name__ == '__main__':
    main()
