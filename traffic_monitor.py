#!/usr/bin/env python3
"""
Simple Traffic Monitor for Cron Job
1. Detect traffic spikes and send alerts
2. Send health checks
Designed to run every 10 minutes via cron.
"""

import subprocess
import re
import statistics
import requests
import json
import os
from typing import List, Dict, NamedTuple, Optional
from datetime import datetime
import logging

# ===== 전역 설정 =====
APPS_SCRIPT_URL = "https://script.google.com/macros/s/fake-key/exec" # default value
HISTORY_FILE = "traffic_history.json"
SPIKE_THRESHOLD = 2.0
MAX_HISTORY = 20

class TrafficData(NamedTuple):
    """Data structure for traffic measurements"""
    timestamp: str
    time: str
    rx_bytes: float
    tx_bytes: float
    total_bytes: float
    avg_rate_bps: float

class TrafficMonitor:
    def __init__(self, server_name: str, server_ip: str, interface: str, apps_script_url: str = None, history_file: str = None, debug: bool = False):
        """
        Initialize the traffic monitor
        
        Args:
            server_name: Server name for identification
            server_ip: Server IP address for identification
            interface: Network interface to monitor
            apps_script_url: Google Apps Script URL for notifications
            history_file: Path to traffic history JSON file
            debug: Enable debug output
        """
        self.server_name = server_name
        self.server_ip = server_ip
        self.interface = interface
        self.debug = debug
        
        # Update global APPS_SCRIPT_URL if provided
        if apps_script_url:
            global APPS_SCRIPT_URL
            APPS_SCRIPT_URL = apps_script_url
            
        # Update global HISTORY_FILE if provided
        if history_file:
            global HISTORY_FILE
            HISTORY_FILE = history_file
        
        # Setup logging
        logging.basicConfig(
            level=logging.DEBUG if debug else logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_history(self) -> List[Dict]:
        """Load traffic history from file"""
        if not os.path.exists(HISTORY_FILE):
            self.logger.info("History file not found, starting with empty history")
            return []
        
        try:
            with open(HISTORY_FILE, 'r') as f:
                history = json.load(f)
            self.logger.info(f"Loaded {len(history)} historical records")
            return history
        except (json.JSONDecodeError, IOError) as e:
            self.logger.error(f"Failed to load history file: {e}")
            return []
    
    def save_history(self, history: List[Dict]):
        """Save traffic history to file"""
        try:
            # Keep only the most recent MAX_HISTORY records
            if len(history) > MAX_HISTORY:
                history = history[-MAX_HISTORY:]
            
            with open(HISTORY_FILE, 'w') as f:
                json.dump(history, f, indent=2)
            
            self.logger.info(f"Saved {len(history)} records to history file")
        except IOError as e:
            self.logger.error(f"Failed to save history file: {e}")
    
    def add_to_history(self, current_data: TrafficData) -> List[Dict]:
        """Add current measurement to history and return updated history"""
        history = self.load_history()
        
        # Convert current data to dict for JSON serialization
        current_record = {
            'timestamp': current_data.timestamp,
            'time': current_data.time,
            'rx_bytes': current_data.rx_bytes,
            'tx_bytes': current_data.tx_bytes,
            'total_bytes': current_data.total_bytes,
            'avg_rate_bps': current_data.avg_rate_bps
        }
        
        history.append(current_record)
        
        # Keep only the most recent records
        if len(history) > MAX_HISTORY:
            history = history[-MAX_HISTORY:]
        
        self.save_history(history)
        return history
    
    def calculate_historical_stats(self, history: List[Dict]) -> Dict:
        """Calculate statistics from historical data"""
        if not history:
            return {}
        
        total_bytes = [record['total_bytes'] for record in history]
        
        stats = {
            'total_traffic': {
                'mean': statistics.mean(total_bytes),
                'stdev': statistics.stdev(total_bytes) if len(total_bytes) > 1 else 0,
                'count': len(total_bytes)
            }
        }
        
        return stats
    
    def detect_spike(self, current_data: TrafficData, historical_stats: Dict) -> tuple[bool, float]:
        """
        Detect if current measurement is a spike based on historical data
        
        Returns:
            (is_spike, z_score)
        """
        if not historical_stats or 'total_traffic' not in historical_stats:
            self.logger.info("No historical data available for spike detection")
            return False, 0.0
        
        mean = historical_stats['total_traffic']['mean']
        stdev = historical_stats['total_traffic']['stdev']
        
        if stdev == 0:
            self.logger.info("Standard deviation is 0, cannot detect spikes")
            return False, 0.0
        
        z_score = (current_data.total_bytes - mean) / stdev
        threshold = mean + (SPIKE_THRESHOLD * stdev)
        
        is_spike = current_data.total_bytes > threshold
        
        if self.debug:
            self.logger.debug(f"Spike detection: current={self.format_bytes(current_data.total_bytes)}, "
                            f"mean={self.format_bytes(mean)}, threshold={self.format_bytes(threshold)}, "
                            f"z_score={z_score:.2f}, is_spike={is_spike}")
        
        return is_spike, z_score
    
    def send_to_apps_script(self, data: Dict) -> bool:
        """Send data to Google Apps Script"""
        try:
            response = requests.post(
                APPS_SCRIPT_URL,
                json=data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            
            self.logger.info(f"Successfully sent {data.get('type', 'unknown')} to Apps Script")
            if self.debug:
                self.logger.debug(f"Response: {response.text}")
            
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to send data to Apps Script: {e}")
            return False
    
    def send_health_check(self, current_data: TrafficData):
        """Send health check with current status"""
        health_data = {
            "type": "health_check",
            "timestamp": current_data.timestamp,
            "server_name": self.server_name,
            "server_ip": self.server_ip,
            "interface": self.interface,
            "status": "healthy",
            "service": "traffic_monitor"
        }
        
        success = self.send_to_apps_script(health_data)
        if success:
            print(f"Health check sent successfully - {self.server_name} ({self.server_ip}) - {self.interface}")
        else:
            print(f"Health check failed - {self.server_name} ({self.server_ip}) - {self.interface}")
    
    def send_spike_alert(self, current_data: TrafficData, z_score: float, historical_stats: Dict):
        """Send spike alert to Apps Script"""
        alert_data = {
            "type": "spike_alert",
            "timestamp": current_data.timestamp,
            "server_name": self.server_name,
            "server_ip": self.server_ip,
            "interface": self.interface,
            "spike_time": current_data.time,
            "current_traffic": {
                "total_bytes": current_data.total_bytes,
                "rx_bytes": current_data.rx_bytes,
                "tx_bytes": current_data.tx_bytes,
                "avg_rate_bps": current_data.avg_rate_bps,
                "total_formatted": self.format_bytes(current_data.total_bytes),
                "rx_formatted": self.format_bytes(current_data.rx_bytes),
                "tx_formatted": self.format_bytes(current_data.tx_bytes),
                "rate_formatted": self.format_rate(current_data.avg_rate_bps)
            },
            "z_score": round(z_score, 2),
            "threshold": SPIKE_THRESHOLD,
            "historical_stats": {
                "mean": historical_stats['total_traffic']['mean'],
                "stdev": historical_stats['total_traffic']['stdev'],
                "count": historical_stats['total_traffic']['count'],
                "mean_formatted": self.format_bytes(historical_stats['total_traffic']['mean']),
                "stdev_formatted": self.format_bytes(historical_stats['total_traffic']['stdev'])
            }
        }
        
        self.send_to_apps_script(alert_data)
    
    def run_vnstat(self) -> str:
        """Run vnstat command and return output"""
        try:
            result = subprocess.run(
                ["vnstat", "-i", self.interface, "-5"],
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to run vnstat: {e}")
        except FileNotFoundError:
            raise RuntimeError("vnstat command not found. Please install vnstat.")
    
    def convert_to_bytes(self, value_str: str) -> float:
        """Convert traffic values to bytes"""
        value_str = value_str.strip().lower()
        
        match = re.match(r'([\d.]+)\s*([kmgt]?i?b)', value_str)
        if not match:
            return 0.0
        
        value = float(match.group(1))
        unit = match.group(2)
        
        multipliers = {
            'b': 1,
            'kib': 1024,
            'mib': 1024**2,
            'gib': 1024**3,
            'tib': 1024**4,
        }
        
        return value * multipliers.get(unit, 1)
    
    def convert_rate_to_bps(self, rate_str: str) -> float:
        """Convert rate values to bits per second"""
        rate_str = rate_str.strip().lower()
        
        if 'bit/s' in rate_str:
            match = re.match(r'([\d.]+)\s*(k|m|g|t)?\s*bit/s', rate_str)
            if match:
                value = float(match.group(1))
                unit = match.group(2) or ''
                
                multipliers = {'': 1, 'k': 1000, 'm': 1000**2, 'g': 1000**3, 't': 1000**4}
                return value * multipliers.get(unit, 1)
        
        return 0.0
    
    def get_current_traffic_data(self) -> Optional[TrafficData]:
        """Get current traffic data from vnstat"""
        try:
            output = self.run_vnstat()
            lines = output.strip().split('\n')
            
            # Find the most recent data (usually the last line with time data)
            latest_data = None
            
            for line in lines:
                if re.search(r'\d{2}:\d{2}', line):
                    parts = [part.strip() for part in line.split('|')]
                    
                    if len(parts) >= 4:
                        try:
                            time_rx_part = parts[0].strip()
                            time_match = re.search(r'(\d{2}:\d{2})', time_rx_part)
                            if not time_match:
                                continue
                            time = time_match.group(1)
                            
                            rx_match = re.search(r'\d{2}:\d{2}\s+(.+)', time_rx_part)
                            if rx_match:
                                rx_str = rx_match.group(1).strip()
                            else:
                                rx_str = "0 B"
                            
                            tx_str = parts[1].strip()
                            total_str = parts[2].strip()
                            rate_str = parts[3].strip()
                            
                            rx_bytes = self.convert_to_bytes(rx_str)
                            tx_bytes = self.convert_to_bytes(tx_str)
                            total_bytes = self.convert_to_bytes(total_str)
                            avg_rate_bps = self.convert_rate_to_bps(rate_str)
                            
                            latest_data = TrafficData(
                                timestamp=datetime.now().isoformat(),
                                time=time,
                                rx_bytes=rx_bytes,
                                tx_bytes=tx_bytes,
                                total_bytes=total_bytes,
                                avg_rate_bps=avg_rate_bps
                            )
                            
                        except (ValueError, IndexError) as e:
                            self.logger.warning(f"Could not parse line: {line} - {e}")
                            continue
            
            return latest_data
            
        except Exception as e:
            self.logger.error(f"Failed to get current traffic data: {e}")
            return None
    
    def format_bytes(self, bytes_value: float) -> str:
        """Format bytes in human-readable format"""
        for unit in ['B', 'KiB', 'MiB', 'GiB', 'TiB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PiB"
    
    def format_rate(self, rate_bps: float) -> str:
        """Format rate in human-readable format"""
        for unit in ['bit/s', 'kbit/s', 'Mbit/s', 'Gbit/s']:
            if rate_bps < 1000.0:
                return f"{rate_bps:.2f} {unit}"
            rate_bps /= 1000.0
        return f"{rate_bps:.2f} Tbit/s"
    
    def run_check(self):
        """
        Main function to run single check (called by cron)
        1. Get current traffic data
        2. Load historical data
        3. Check for spikes
        4. Send health check
        5. Update history
        """
        self.logger.info(f"Starting traffic check for {self.server_name} ({self.server_ip}) - {self.interface}")
        
        try:
            # 1. Get current traffic data
            current_data = self.get_current_traffic_data()
            if not current_data:
                self.logger.error("No current traffic data available")
                return False
            
            self.logger.info(f"Current traffic: {self.format_bytes(current_data.total_bytes)} "
                           f"(RX: {self.format_bytes(current_data.rx_bytes)}, "
                           f"TX: {self.format_bytes(current_data.tx_bytes)})")
            
            # 2. Load historical data and calculate stats
            history = self.load_history()
            historical_stats = self.calculate_historical_stats(history)
            
            # 3. Check for spikes
            is_spike, z_score = self.detect_spike(current_data, historical_stats)
            
            if is_spike:
                self.logger.warning(f"SPIKE DETECTED! Z-score: {z_score:.2f}")
                self.send_spike_alert(current_data, z_score, historical_stats)
            else:
                self.logger.info(f"Normal traffic (z-score: {z_score:.2f})")
            
            # 4. Send health check
            self.send_health_check(current_data)
            
            # 5. Update history
            self.add_to_history(current_data)
            
            self.logger.info("Traffic check completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Traffic check failed: {e}")
            
            # Send error health check
            error_data = {
                "type": "health_check",
                "timestamp": datetime.now().isoformat(),
                "server_name": self.server_name,
                "server_ip": self.server_ip,
                "interface": self.interface,
                "status": "error",
                "service": "traffic_monitor",
                "error_message": str(e)
            }
            try:
                self.send_to_apps_script(error_data)
            except:
                pass  # 에러 전송도 실패하면 무시
            
            return False

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Simple network traffic monitor')
    parser.add_argument('--server-name', required=True,
                       help='Server name for identification')
    parser.add_argument('--server-ip', required=True,
                       help='Server IP address for identification')
    parser.add_argument('--interface', required=True,
                       help='Network interface to monitor')
    parser.add_argument('--apps-script-url', required=True,
                       help='Google Apps Script webhook URL')
    parser.add_argument('--history-file', 
                       help='Path to traffic history JSON file')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    monitor = TrafficMonitor(
        server_name=args.server_name,
        server_ip=args.server_ip,
        interface=args.interface,
        apps_script_url=args.apps_script_url,
        history_file=args.history_file,
        debug=args.debug
    )
    
    success = monitor.run_check()
    exit(0 if success else 1)

if __name__ == "__main__":
    main()