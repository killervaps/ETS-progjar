import socket
import json
import time
import os
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
import sys
import logging
import base64

# Setup logging to capture errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='stress_test_server.log', filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

results = {}  # Dictionary to store results for each mode combination
BUFFER_SIZE = 5242880  # 5MB buffer
current_max_workers = 50  # Global variable to store max_workers dynamically

def server_process(mode, port, stop_event, ready_event):
    global current_max_workers
    my_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)
    my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
    if mode == "processing":
        try:
            my_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            pass
    try:
        my_socket.bind(('0.0.0.0', port))
        my_socket.listen(100)
        logging.info(f"Server started on port {port} in {mode} mode with {current_max_workers} workers")
        ready_event.set()  # Signal that server is ready
    except Exception as e:
        logging.error(f"Failed to start server on port {port}: {e}")
        ready_event.set()
        return
    
    executor_class = ThreadPoolExecutor if mode == "threading" else ProcessPoolExecutor
    with executor_class(max_workers=current_max_workers) as executor:
        while not stop_event.is_set():
            try:
                my_socket.settimeout(2.0)
                connection, client_address = my_socket.accept()
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
                executor.submit(handle_client, connection, client_address, mode)
            except socket.timeout:
                continue
            except Exception as e:
                logging.error(f"Server error: {e}")
                break
    my_socket.close()

def handle_client(connection, address, mode):
    global current_max_workers
    try:
        command_str = b''
        while not command_str.endswith(b'\n'):
            chunk = connection.recv(BUFFER_SIZE)  # 5MB buffer for receiving commands
            if not chunk:
                break
            command_str += chunk
        command_str = command_str.decode('utf-8', errors='ignore').strip()
        
        parts = command_str.split(maxsplit=1)
        if parts[0] == "READY":
            connection.sendall(f'{{"status": "READY", "mode": "{mode}"}}\r\n\r\n'.encode('utf-8'))
        elif parts[0] == "RESULT":
            parts = command_str.split()
            test_num = int(parts[1])
            operation = parts[2]
            volume = parts[3]
            client_worker_count = int(parts[4])
            server_worker_count = int(parts[5])
            mode_client = parts[6]
            mode_server = parts[7]
            successes = int(parts[8])
            failures = int(parts[9])
            avg_time = float(parts[10])
            avg_throughput = float(parts[11])
            
            # Update max_workers based on server_worker_count
            current_max_workers = max(1, server_worker_count)  # Ensure at least 1 worker
            
            mode_key = f"{mode_server}_{mode_client}"
            if mode_key not in results:
                results[mode_key] = []
            
            results[mode_key].append({
                'Nomor': test_num,
                'Operasi': operation,
                'Volume': volume,
                'Jumlah client worker pool': client_worker_count,
                'Jumlah server worker pool': server_worker_count,
                'Mode Client': mode_client,
                'Mode Server': mode_server,
                'Waktu total per client': round(avg_time, 2),
                'Throughput per client': round(avg_throughput, 2),
                'Worker client sukses': successes,
                'Worker client gagal': failures,
                'Worker server sukses': successes,
                'Worker server gagal': failures
            })
            
            filename = f"stress_test_results_{mode_server}_{mode_client}.csv"
            try:
                df = pd.DataFrame(results[mode_key])
                df.to_csv(filename, index=False, sep=';', encoding='utf-8-sig')
                logging.info(f"Saved results to {filename}")
            except Exception as e:
                logging.error(f"Failed to save CSV {filename}: {e}")
            
            connection.sendall(f'{{"status": "OK"}}\r\n\r\n'.encode('utf-8'))
        else:
            filename = parts[1]
            filepath = os.path.join('files', filename)
            if parts[0] == "GET":
                result = {"status": "OK", "data_namafile": filename}
                connection.sendall(f"{json.dumps(result)}\r\n\r\n".encode('utf-8'))
                with open(filepath, 'rb') as fp:
                    while True:
                        data = fp.read(BUFFER_SIZE)  # Stream in 5MB chunks
                        if not data:
                            break
                        connection.sendall(base64.b64encode(data))
                connection.sendall(b'\r\n\r\n')
            elif parts[0] == "UPLOAD":
                with open(filepath, 'wb') as fp:
                    while True:
                        chunk = connection.recv(BUFFER_SIZE)
                        if not chunk or b'\r\n\r\n' in chunk:
                            chunk = chunk.replace(b'\r\n\r\n', b'')
                            if chunk:
                                fp.write(base64.b64decode(chunk))
                            break
                        fp.write(base64.b64decode(chunk))
                result = {"status": "OK", "data": "Uploaded"}
                connection.sendall(f"{json.dumps(result)}\r\n\r\n".encode('utf-8'))
    except Exception as e:
        logging.error(f"Handle client error: {e}")
    finally:
        try:
            connection.close()
        except:
            pass

def main():
    # Remove old CSV files
    for csv_file in os.listdir():
        if csv_file.startswith('stress_test_results_') and csv_file.endswith('.csv'):
            os.remove(csv_file)
    
    server_modes = ['threading', 'processing']
    for mode in server_modes:
        stop_event = threading.Event()
        ready_event = threading.Event()
        server_thread = threading.Thread(target=server_process, args=(mode, 55000, stop_event, ready_event))
        server_thread.start()
        ready_event.wait()
        
        print(f"Server is running in {mode} mode and waiting for client requests...")
        try:
            while True:
                time.sleep(1)  # Keep server running
        except KeyboardInterrupt:
            print(f"Shutting down server in {mode} mode...")
            stop_event.set()
            server_thread.join()
            # Save any pending results
            for mode_key, result_list in results.items():
                if result_list:
                    filename = f"stress_test_results_{mode_key}.csv"
                    try:
                        df = pd.DataFrame(result_list)
                        df.to_csv(filename, index=False, sep=';', encoding='utf-8-sig')
                        logging.info(f"Saved results to {filename}")
                    except Exception as e:
                        logging.error(f"Failed to save CSV {filename}: {e}")
            break

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Main execution error: {e}")
        sys.exit(1)