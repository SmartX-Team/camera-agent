# app/ptp_synchronization.py
import subprocess
import threading
import logging
import shutil
import time
import netifaces

def get_default_interface():
    gateways = netifaces.gateways()
    if 'default' in gateways and netifaces.AF_INET in gateways['default']:
        return gateways['default'][netifaces.AF_INET][1]
    return None

def check_ptpd_installed():
    return shutil.which('ptpd') is not None


def get_ptp_status():
    try:
        # ptpd 프로세스 확인
        ps_output = subprocess.check_output(["ps", "-ef"], text=True)
        if "ptpd" in ps_output:
            return "PTPd is running"
        else:
            return "PTPd is not running"
    except subprocess.CalledProcessError:
        return "Unable to check PTPd status"

def synchronize_with_ptp_server():
    if not check_ptpd_installed():
        logging.error("ptpd is not installed. Please install it first.")
        return

    interface_name = get_default_interface()
    if not interface_name:
        logging.error("Unable to determine default network interface.")
        return

    try:
        cmd = ['ptpd', '-s', '-i', interface_name]
        ptp_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logging.info(f"PTP synchronization started with ptpd on interface {interface_name}.")

        def log_output(stream):
            for line in iter(stream.readline, ''):
                logging.info(f"PTPD: {line.strip()}")
            stream.close()

        threading.Thread(target=log_output, args=(ptp_process.stdout,), daemon=True).start()
        threading.Thread(target=log_output, args=(ptp_process.stderr,), daemon=True).start()

        while True:
            if ptp_process.poll() is not None:
                logging.error("PTP process has terminated unexpectedly. Restarting...")
                ptp_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # PTP 동기화 상태 확인
            status = get_ptp_status()
            logging.info(f"PTP Status: {status}")
            time.sleep(60)  # 1분마다 상태 확인

    except Exception as e:
        logging.error(f"Failed to start PTP synchronization: {e}")