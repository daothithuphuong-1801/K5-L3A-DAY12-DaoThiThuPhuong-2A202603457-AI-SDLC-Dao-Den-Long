## Đảo Đèn Lồng v1.0.0 — Bình minh

Game 3D, 3 Đêm (Đảo Bến, Đảo Cau, Đảo Chuông). Test Contract v1.3.

### Tải và chạy
- `DaoDenLong-v1.0.0-Linux.zip` / `-macOS.zip` / `-Windows.zip`: giải nén rồi chạy `DaoDenLong` (`DaoDenLong.exe` trên Windows). Đây là bản dựng sẵn bằng PyInstaller, không cần cài Python.
- `DaoDenLong-v1.0.0-source.zip`: mã nguồn. Cần Python 3.10+, chạy bằng `./run.sh` (macOS/Linux) hoặc `run.bat` (Windows).
- Từ git: `python3 -m pip install -r requirements.txt && python3 -m game.app`.
- Trên macOS, lần đầu mở bản dựng sẵn có thể cần chuột phải → Open, vì bản dựng chưa được ký.

### Lệnh theo Test Contract
- Headless: `python3 -m game.headless`
- Benchmark: `python3 -m game.bench --seed 42 --duration 30 --out bench.json`
- Soak test: `python3 -m game.soak --seed 7 --nights 10 --out soak.json`
- Xuất bảng xếp hạng: `python3 -m game.app --export-leaderboard out.json`

Chi tiết thay đổi: xem CHANGELOG.md.
