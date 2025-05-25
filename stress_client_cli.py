import socket
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import logging
import sys
import base64

# Setup logging to capture errors
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='stress_test_client.log', filemode='w')
console = logging.StreamHandler()
console.setLevel(logging.INFO)
logging.getLogger().addHandler(console)

# Simulated file sizes (for throughput calculation)
FILE_SIZES = {
    "10MB": 10 * 1024 * 1024,  # 10MB
    "50MB": 50 * 1024 * 1024,  # 50MB
    "100MB": 100 * 1024 * 1024  # 100MB
}

BUFFER_SIZE = 5242880  # 5MB buffer for socket settings

# Client implementation
def send_command(command_str="", timeout=10):
    retries = 0
    max_retries = 5
    while retries < max_retries:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
        sock.settimeout(timeout)
        try:
            sock.connect(('172.16.16.101', 55000))  # Connect to server device
            sock.sendall((command_str + '\n').encode('utf-8'))
            data_received = ""
            while True:
                data = sock.recv(BUFFER_SIZE)  # 5MB buffer
                if not data:
                    break
                data_received += data.decode('utf-8', errors='ignore')
                if "\r\n\r\n" in data_received:
                    try:
                        result = json.loads(data_received)
                        return result
                    except json.JSONDecodeError:
                        continue
            retries += 1
            time.sleep(2)  # Increased retry delay
        except Exception as e:
            logging.error(f"Send command error: {e}")
            retries += 1
            time.sleep(2)
        finally:
            try:
                sock.close()
            except:
                pass
    return False

def remote_get(filename, timeout):
    start_time = time.perf_counter()
    command_str = f"GET {filename}"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
    sock.settimeout(timeout)
    try:
        sock.connect(('172.16.16.101', 55000))
        sock.sendall((command_str + '\n').encode('utf-8'))
        data_received = ""
        while True:
            data = sock.recv(BUFFER_SIZE)
            if not data:
                break
            data_received += data.decode('utf-8', errors='ignore')
            if "\r\n\r\n" in data_received:
                try:
                    result = json.loads(data_received)
                    break
                except json.JSONDecodeError:
                    continue
        if result and result.get('status') == 'OK':
            with open(filename, 'wb') as fp:
                while True:
                    chunk = sock.recv(BUFFER_SIZE)
                    if not chunk or b'\r\n\r\n' in chunk:
                        chunk = chunk.replace(b'\r\n\r\n', b'')
                        if chunk:
                            fp.write(base64.b64decode(chunk))
                        break
                    fp.write(base64.b64decode(chunk))
            elapsed_time = time.perf_counter() - start_time
            file_size = os.path.getsize(filename)
            throughput = file_size / elapsed_time if elapsed_time > 0 else 0
            return True, elapsed_time, throughput
        return False, 0, 0
    except Exception as e:
        logging.error(f"Download error: {e}")
        return False, 0, 0
    finally:
        try:
            sock.close()
        except:
            pass

def remote_upload(filename, timeout):
    try:
        start_time = time.perf_counter()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, BUFFER_SIZE)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, BUFFER_SIZE)
        sock.settimeout(timeout)
        try:
            sock.connect(('172.16.16.101', 55000))
            command_str = f"UPLOAD {filename}"
            sock.sendall((command_str + '\n').encode('utf-8'))
            with open(filename, 'rb') as fp:
                while True:
                    data = fp.read(BUFFER_SIZE)  # Stream in 5MB chunks
                    if not data:
                        break
                    sock.sendall(base64.b64encode(data))
            sock.sendall(b'\r\n\r\n')
            data_received = ""
            while True:
                data = sock.recv(BUFFER_SIZE)
                if not data:
                    break
                data_received += data.decode('utf-8', errors='ignore')
                if "\r\n\r\n" in data_received:
                    try:
                        result = json.loads(data_received)
                        if result.get('status') == 'OK':
                            elapsed_time = time.perf_counter() - start_time
                            file_size = FILE_SIZES[filename.replace("test_", "").replace(".bin", "")]
                            throughput = file_size / elapsed_time if elapsed_time > 0 else 0
                            return True, elapsed_time, throughput
                    except json.JSONDecodeError:
                        continue
        finally:
            try:
                sock.close()
            except:
                pass
    except Exception as e:
        logging.error(f"Upload error: {e}")
    return False, 0, 0

def stress_test(operation, filename, max_workers, mode, server_mode):
    executor_class = ThreadPoolExecutor if mode == "threading" else ProcessPoolExecutor
    successes = 0
    total_time = 0
    total_throughput = 0
    
    timeout = 10 if "10MB" in filename else 20 if "50MB" in filename else 40
    
    max_concurrent = 25 if max_workers > 25 else max_workers
    batches = (max_workers + max_concurrent - 1) // max_concurrent
    
    for batch in range(batches):
        start_idx = batch * max_concurrent
        end_idx = min(start_idx + max_concurrent, max_workers)
        batch_size = end_idx - start_idx
        
        with executor_class(max_workers=batch_size) as executor:
            futures = []
            for _ in range(batch_size):
                if operation == "download":
                    futures.append(executor.submit(remote_get, filename, timeout))
                else:
                    futures.append(executor.submit(remote_upload, filename, timeout))
            
            for future in futures:
                try:
                    success, elapsed_time, throughput = future.result(timeout=timeout)
                    if success:
                        successes += 1
                        total_time += elapsed_time
                        total_throughput += throughput
                except Exception as e:
                    logging.error(f"Stress test error: {e}")
        time.sleep(2)  # Increased delay between batches to prevent server overload
    
    avg_time = total_time / successes if successes > 0 else 0
    avg_throughput = total_throughput / successes if successes > 0 else 0
    return successes, max_workers - successes, avg_time, avg_throughput

def main():
    file_sizes = ["10MB", "50MB", "100MB"]
    client_workers = [1, 5, 50]
    server_workers = [1, 5, 50]
    operations = ['download', 'upload']
    client_modes = ['threading', 'processing']
    server_modes = ['threading', 'processing']
    
    # Ensure test files exist on client
    for size in [10, 50, 100]:
        filename = f"test_{size}MB.bin"
        with open(filename, 'wb') as fp:
            fp.write(os.urandom(size * 1024 * 1024))
    
    for server_mode in server_modes:
        # Wait for server to be ready in the current mode
        while True:
            response = send_command("READY")
            if response and response.get('status') == 'READY' and response.get('mode') == server_mode:
                break
            time.sleep(2)
        
        for client_mode in client_modes:
            test_number = 1
            for operation in operations:
                for size_mb in file_sizes:
                    for client_worker_count in client_workers:
                        for server_worker_count in server_workers:
                            print(f"Test {test_number}: {operation}, {size_mb}, {client_worker_count} client workers, {server_worker_count} server workers, client mode {client_mode}, server mode {server_mode}")
                            filename = f"test_{size_mb}.bin"
                            successes, failures, avg_time, avg_throughput = stress_test(operation, filename, client_worker_count, client_mode, server_mode)
                            result_str = f"RESULT {test_number} {operation} {size_mb} {client_worker_count} {server_worker_count} {client_mode} {server_mode} {successes} {failures} {avg_time:.2f} {avg_throughput:.2f}"
                            response = send_command(result_str)
                            if not response or response.get('status') != 'OK':
                                logging.error(f"Failed to record result for test {test_number}")
                            test_number += 1
            print(f"Completed combination: client mode {client_mode}, server mode {server_mode}")
        time.sleep(5)  # Allow server to switch modes

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.error(f"Main execution error: {e}")
        sys.exit(1)