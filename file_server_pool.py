from socket import *
import socket
import logging
import json
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from file_protocol import FileProtocol

def process_client(connection, address):
    try:
        command_str = b''
        while not command_str.endswith(b'\n'):
            chunk = connection.recv(1)
            if not chunk:
                break
            command_str += chunk
        command_str = command_str.decode().strip()
        logging.warning(f"Terima command: {command_str}")
        fp = FileProtocol()
        result = fp.proses_string(command_str)
        connection.sendall(f"{result}\r\n\r\n".encode())
    except Exception as e:
        logging.warning(f"error: {e}")
        connection.sendall(json.dumps({'status': 'ERROR', 'data': str(e)}).encode() + b'\r\n\r\n')
    finally:
        connection.close()

def run_server(ipaddress='0.0.0.0', port=55000, mode="threading"):
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    if mode == "processing":
        my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
    my_socket.bind((ipaddress, port))
    my_socket.listen(1)
    
    catat_awal = time.perf_counter()
    logging.warning(f"server berjalan di ip address {(ipaddress, port)}")
    
    executor_class = ThreadPoolExecutor if mode == "threading" else ProcessPoolExecutor
    with executor_class() as executor:
        while True:
            connection, client_address = my_socket.accept()
            logging.warning(f"connection from {client_address}")
            print(f"menjalankan process_client untuk {client_address}")
            executor.submit(process_client, connection, client_address)
    
    catat_akhir = time.perf_counter()
    selesai = round(catat_akhir - catat_awal, 2)
    print(f"Waktu TOTAL yang dibutuhkan {selesai} detik {catat_awal} s/d {catat_akhir}")

def main():
    #print("Mode: Threading")
    #run_server(mode="threading")
    print("\nMode: Processing")
    run_server(mode="processing")

if __name__ == "__main__":
    main()