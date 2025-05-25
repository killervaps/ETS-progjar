import socket
import json
import base64
import logging
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

server_address = ('0.0.0.0', 7777)

def send_command(command_str=""):
    global server_address
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(server_address)
    logging.warning(f"connecting to {server_address}")
    try:
        logging.warning(f"sending message ")
        sock.sendall((command_str + '\n').encode())  # Tambahkan '\n' di sini
        data_received = ""
        while True:
            data = sock.recv(16)
            if data:
                data_received += data.decode()
                if "\r\n\r\n" in data_received:
                    break
            else:
                break
        hasil = json.loads(data_received)
        logging.warning("data received from server:")
        return hasil
    except:
        logging.warning("error during data receiving")
        return False

def remote_list():
    command_str = "LIST"
    hasil = send_command(command_str)
    if (hasil['status'] == 'OK'):
        print("daftar file : ")
        for nmfile in hasil['data']:
            print(f"- {nmfile}")
        return True
    else:
        print("Gagal")
        return False

def remote_get(filename=""):
    command_str = f"GET {filename}"
    hasil = send_command(command_str)
    if (hasil['status'] == 'OK'):
        namafile = hasil['data_namafile']
        isifile = base64.b64decode(hasil['data_file'])
        fp = open(namafile, 'wb+')
        fp.write(isifile)
        fp.close()
        print(f"Berhasil mendownload {filename}")
        return True
    else:
        print("Gagal")
        return False

def remote_upload(filename=""):
    try:
        with open(filename, 'rb') as fp:
            file_content = base64.b64encode(fp.read()).decode()
        command_str = f"UPLOAD {filename} {file_content}"
        hasil = send_command(command_str)
        if (hasil['status'] == 'OK'):
            print("Upload berhasil")
            return True
        else:
            print(f"Upload gagal: {hasil['data']}")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def download_semua(mode="threading"):
    tasks = [
        ("LIST", None),
        ("GET", "contoh.jpg"),
        ("GET", "pokijan.jpg"),
        ("UPLOAD", "contoh.pdf")
    ]
    
    catat_awal = time.perf_counter()
    
    executor_class = ThreadPoolExecutor if mode == "threading" else ProcessPoolExecutor
    with executor_class() as executor:
        for task_type, param in tasks:
            print(f"menjalankan {task_type} {param if param else ''}")
            if task_type == "LIST":
                executor.submit(remote_list)
            elif task_type == "GET":
                executor.submit(remote_get, param)
            elif task_type == "UPLOAD":
                executor.submit(remote_upload, param)
    
    catat_akhir = time.perf_counter()
    selesai = round(catat_akhir - catat_awal, 2)
    print(f"Waktu TOTAL yang dibutuhkan {selesai} detik {catat_awal} s/d {catat_akhir}")

if __name__ == '__main__':
    server_address = ('172.16.16.101', 55000)
    # Jalankan dengan threading
    #print("Mode: Threading")
    #download_semua(mode="threading")
    # Jalankan dengan processing
    print("\nMode: Processing")
    download_semua(mode="processing")