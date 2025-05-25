### **Penjelasan Isi Kode `stress_client_cli.py` (Client)**

1. **Impor Modul**:
   - `socket`: Digunakan untuk komunikasi jaringan, seperti telepon untuk menghubungkan client dan server.
   - `json`: Untuk memformat dan membaca data dalam format JSON, seperti menulis dan membaca pesan terstruktur.
   - `time`: Untuk mengukur waktu eksekusi, seperti stopwatch untuk menghitung durasi layanan.
   - `os`: Untuk mengelola file di sistem, seperti membuat atau membaca file.
   - `concurrent.futures`: Menyediakan `ThreadPoolExecutor` dan `ProcessPoolExecutor` untuk menjalankan banyak tugas secara bersamaan, seperti mengatur beberapa pelayan atau pelanggan.
   - `logging`: Untuk mencatat informasi atau error, seperti buku log restoran.
   - `sys`: Untuk mengelola eksekusi program, misalnya keluar dari program jika terjadi error.
   - `base64`: Untuk mengkodekan dan mendekodekan data file, seperti mengemas makanan agar aman dikirim.

2. **Pengaturan Logging**:
   - Kode mengatur sistem logging untuk mencatat informasi dan error ke file `stress_test_client.log` dan juga menampilkan ke konsol.
   - Format log mencakup waktu, level (misalnya INFO atau ERROR), dan pesan, seperti mencatat "Pelanggan memesan pada jam 08:00, berhasil".
   - Ini membantu melacak apa yang terjadi selama pengujian.

3. **Konstanta**:
   - `FILE_SIZES`: Kamus yang mendefinisikan ukuran file untuk pengujian:
     - `"10MB"`: 10 megabyte (10 * 1024 * 1024 bytes).
     - `"50MB"`: 50 megabyte.
     - `"100MB"`: 100 megabyte.
     - Ini seperti menentukan ukuran pesanan: kecil, sedang, besar.
   - `BUFFER_SIZE`: 5MB (5242880 bytes), ukuran potongan data yang dikirim atau diterima, seperti porsi makanan yang dibawa pelayan sekali angkut.

4. **Fungsi `send_command`**:
   - **Tujuan**: Mengirim perintah ke server dan menerima respons, seperti pelanggan memesan via telepon.
   - **Proses**:
     - Membuat soket (koneksi) ke server di alamat `172.16.16.101` dan port `55000`.
     - Mengatur buffer soket ke 5MB dan timeout (batas waktu menunggu, default 10 detik).
     - Mengirim perintah (misalnya "GET file.txt") dengan tambahan `\n` di akhir.
     - Menerima respons dalam potongan 5MB hingga menemukan penanda `\r\n\r\n`.
     - Mengurai respons sebagai JSON.
     - Jika gagal (misalnya server tidak respons), mencoba ulang hingga 5 kali dengan jeda 2 detik.
   - **Output**: Mengembalikan hasil JSON dari server atau `False` jika gagal.
   - **Analogi**: Seperti pelanggan menelepon restoran, memesan, dan menunggu konfirmasi pesanan.

5. **Fungsi `remote_get`**:
   - **Tujuan**: Mengunduh file dari server, seperti pelanggan minta makanan dikirim.
   - **Proses**:
     - Mencatat waktu mulai dengan `time.perf_counter()`.
     - Membuat soket dan mengirim perintah "GET nama_file" (misalnya "GET test_10MB.bin").
     - Menerima respons JSON dari server yang mengkonfirmasi status "OK".
     - Menerima data file dalam potongan 5MB, mendekode dari base64, dan menyimpan ke file lokal.
     - Menghentikan penerimaan saat menemukan `\r\n\r\n`.
     - Menghitung waktu selesai, ukuran file, dan throughput (ukuran file dibagi waktu, dalam bytes per detik).
   - **Output**: Mengembalikan tuple `(sukses, waktu, throughput)`:
     - `sukses`: `True` jika berhasil, `False` jika gagal.
     - `waktu`: Durasi dalam detik.
     - `throughput`: Kecepatan transfer dalam bytes per detik.
   - **Analogi**: Pelanggan memesan pizza, menerima potongan demi potongan, dan mencatat berapa lama pengiriman.

6. **Fungsi `remote_upload`**:
   - **Tujuan**: Mengunggah file ke server, seperti pelanggan mengirimkan pembayaran.
   - **Proses**:
     - Mencatat waktu mulai.
     - Membuat soket dan mengirim perintah "UPLOAD nama_file".
     - Membaca file lokal dalam potongan 5MB, mengkodekan ke base64, dan mengirim ke server.
     - Mengirim penanda `\r\n\r\n` setelah selesai.
     - Menerima respons JSON dari server untuk konfirmasi status "OK".
     - Menghitung waktu, ukuran file (dari `FILE_SIZES`), dan throughput.
   - **Output**: Sama seperti `remote_get`, tuple `(sukses, waktu, throughput)`.
   - **Analogi**: Pelanggan mengirimkan kotak makanan ke restoran, potong-potong, dan menunggu restoran bilang "Sudah diterima!".

7. **Fungsi `stress_test`**:
   - **Tujuan**: Menjalankan pengujian stres dengan banyak pekerja secara bersamaan, seperti mengirim banyak pelanggan ke restoran sekaligus.
   - **Parameter**:
     - `operation`: "download" atau "upload".
     - `filename`: Nama file (misalnya "test_10MB.bin").
     - `max_workers`: Jumlah pekerja (1, 5, atau 50).
     - `mode`: "threading" (thread pool) atau "processing" (process pool).
     - `server_mode`: Mode server (tidak digunakan langsung, hanya untuk pelaporan).
   - **Proses**:
     - Memilih `ThreadPoolExecutor` atau `ProcessPoolExecutor` berdasarkan `mode`.
     - Menentukan timeout berdasarkan ukuran file: 10 detik (10MB), 20 detik (50MB), 40 detik (100MB).
     - Membagi pekerja ke dalam batch (maksimal 25 pekerja per batch) untuk mencegah server kewalahan.
     - Untuk setiap batch:
       - Membuat pool dengan jumlah pekerja sesuai batch.
       - Menugaskan tugas (`remote_get` atau `remote_upload`) ke setiap pekerja.
       - Mengumpulkan hasil (sukses/gagal, waktu, throughput).
       - Menambahkan jeda 2 detik antar batch.
     - Menghitung rata-rata waktu dan throughput dari pekerja yang sukses.
   - **Output**: Tuple `(sukses, gagal, rata_waktu, rata_throughput)`:
     - `sukses`: Jumlah pekerja yang berhasil.
     - `gagal`: Jumlah pekerja yang gagal (`max_workers - sukses`).
     - `rata_waktu`: Rata-rata waktu per pekerja sukses.
     - `rata_throughput`: Rata-rata throughput per pekerja sukses.
   - **Analogi**: Mengatur 50 pelanggan untuk memesan pizza sekaligus, tapi dibagi jadi kelompok kecil biar pelayan nggak panik.

8. **Fungsi `main`**:
   - **Tujuan**: Mengatur semua pengujian dengan berbagai kombinasi parameter.
   - **Proses**:
     - Mendefinisikan parameter pengujian:
       - `file_sizes`: ["10MB", "50MB", "100MB"].
       - `client_workers`: [1, 5, 50].
       - `server_workers`: [1, 5, 50].
       - `operations`: ["download", "upload"].
       - `client_modes`: ["threading", "processing"].
       - `server_modes`: ["threading", "processing"].
     - Membuat file uji (10MB, 50MB, 100MB) menggunakan `os.urandom`.
     - Untuk setiap mode server:
       - Menunggu server siap dengan mengirim perintah "READY" hingga respons sesuai.
       - Untuk setiap mode client, operasi, ukuran file, jumlah pekerja client, dan jumlah pekerja server:
         - Menjalankan `stress_test`.
         - Mencetak informasi tes (misalnya "Test 1: download, 10MB, 5 client workers...").
         - Mengirim hasil ke server dengan perintah "RESULT" dalam format:
           ```
           RESULT nomor operasi ukuran client_workers server_workers client_mode server_mode sukses gagal rata_waktu rata_throughput
           ```
         - Memeriksa respons server untuk memastikan hasil diterima.
     - Menambahkan jeda 5 detik antar mode server untuk transisi.
   - **Analogi**: Mengatur rencana besar untuk menguji restoran dengan berbagai jumlah pelanggan, ukuran pesanan, dan cara kerja pelayan.

9. **Blok Utama (`if __name__ == "__main__"`)**:
   - Menjalankan fungsi `main` dalam blok try-except untuk menangani error.
   - Jika terjadi error, mencatat ke log dan keluar dari program dengan status 1.
   - **Analogi**: Memulai operasi restoran dan memastikan semuanya berjalan mulus.

---

### **Penjelasan Isi Kode `run_stress_test.py` (Server)**

1. **Impor Modul**:
   - Sama seperti `stress_client_cli.py`: `socket`, `json`, `time`, `os`, `pandas`, `concurrent.futures`, `threading`, `sys`, `logging`, `base64`.
   - Tambahan `pandas` untuk membuat dan menyimpan tabel data ke file CSV.
   - **Analogi**: Membawa alat-alat yang dibutuhkan pelayan untuk melayani dan mencatat pesanan.

2. **Pengaturan Logging**:
   - Mengatur logging ke file `stress_test_server.log` dan konsol, sama seperti client.
   - **Analogi**: Buku catatan pelayan untuk mencatat apa yang terjadi di restoran.

3. **Variabel Global dan Konstanta**:
   - `results`: Kamus untuk menyimpan hasil pengujian, dengan kunci berdasarkan kombinasi mode server dan client (misalnya "threading_processing").
   - `BUFFER_SIZE`: 5MB, sama seperti client.
   - `current_max_workers`: Jumlah pekerja server, awalnya 50, tapi bisa berubah berdasarkan perintah dari client.
   - **Analogi**: Buku menu dan jumlah pelayan yang siap bekerja.

4. **Fungsi `server_process`**:
   - **Tujuan**: Menjalankan server untuk menerima koneksi dari client.
   - **Parameter**:
     - `mode`: "threading" atau "processing".
     - `port`: Port untuk mendengarkan (55000).
     - `stop_event`: Objek untuk menghentikan server.
     - `ready_event`: Objek untuk memberi sinyal server siap.
   - **Proses**:
     - Membuat soket, mengatur opsi seperti `SO_REUSEADDR` (agar port bisa digunakan ulang) dan buffer 5MB.
     - Jika mode "processing", mencoba mengatur `SO_REUSEPORT` (untuk mendukung proses paralel).
     - Mengikat soket ke alamat `0.0.0.0` (semua alamat) dan port `55000`, lalu mendengarkan hingga 100 koneksi.
     - Mengatur timeout soket 2 detik untuk menghindari pemblokiran.
     - Memilih `ThreadPoolExecutor` atau `ProcessPoolExecutor` berdasarkan mode.
     - Dalam loop, menerima koneksi client dan menugaskan ke pool untuk ditangani oleh `handle_client`.
     - Jika `stop_event` diaktifkan, menutup soket dan menghentikan server.
   - **Analogi**: Pelayan membuka pintu restoran, menunggu pelanggan, dan menugaskan pesanan ke tim pelayan.

5. **Fungsi `handle_client`**:
   - **Tujuan**: Menangani permintaan dari satu client.
   - **Parameter**:
     - `connection`: Soket untuk komunikasi dengan client.
     - `address`: Alamat client.
     - `mode`: Mode server ("threading" atau "processing").
   - **Proses**:
     - Menerima perintah dari client hingga menemukan `\n`.
     - Mengurai perintah:
       - **"READY"**: Mengirim respons JSON `{status: "READY", mode: mode}`.
       - **"RESULT"**: Mengurai string perintah untuk mendapatkan data tes (nomor, operasi, ukuran file, dll.), memperbarui `current_max_workers`, menyimpan hasil ke `results`, dan menulis ke file CSV menggunakan pandas.
       - **"GET"**: Mengirim file yang diminta dalam potongan 5MB, dikodekan base64, diakhiri dengan `\r\n\r\n`.
       - **"UPLOAD"**: Menerima file dalam potongan 5MB, mendekode dari base64, menyimpan ke direktori `files`, dan mengirim konfirmasi JSON.
     - Menangani error dengan mencatat ke log dan menutup koneksi.
   - **Analogi**: Pelayan mendengar pesanan pelanggan, mengambil makanan dari dapur atau menerima pembayaran, dan mencatat ulasan pelanggan.

6. **Fungsi `main`**:
   - **Tujuan**: Mengatur operasi server untuk berbagai mode.
   - **Proses**:
     - Menghapus file CSV lama yang dimulai dengan "stress_test_results_".
     - Mendefinisikan mode server: ["threading", "processing"].
     - Untuk setiap mode:
       - Membuat `stop_event` dan `ready_event` untuk kontrol.
       - Menjalankan `server_process` dalam thread terpisah.
       - Menunggu server siap (`ready_event.wait()`).
       - Menjalankan loop untuk menjaga server tetap hidup hingga dihentikan (misalnya dengan Ctrl+C).
       - Jika dihentikan, mengatur `stop_event`, menunggu thread selesai, dan menyimpan hasil yang belum tersimpan ke CSV.
   - **Analogi**: Mengatur jadwal kerja restoran, membuka pintu untuk pelanggan, dan memastikan semua pesanan tercatat.

7. **Blok Utama (`if __name__ == "__main__"`)**:
   - Menjalankan fungsi `main` dalam blok try-except.
   - Mencatat error ke log dan keluar dengan status 1 jika terjadi masalah.
   - **Analogi**: Membuka restoran dan memastikan operasi berjalan lancar.
