# Bằng chứng Phase 4 (Ticket-04, Contract v1.3)

Máy đo: Windows 11 (10.0.26200), Intel Core thế hệ 11 (Family 6 Model 140, 8 luồng), GPU tích hợp Intel Iris Xe (OpenGL 4.6), chạy pin/sạc mặc định. Tái lập: lệnh ghi ở từng dòng.

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Contract v1.3 (`bench_cmd`, `soak_cmd`, mọi số v1.0–v1.2 giữ nguyên) | `test_contract_v13_commands` | [game.contract.json](../../../game.contract.json) | Đạt |
| Benchmark: cảnh chuẩn (200 Bóng Mực wander, 100 đom đóm, L1–L3 dầu 100, Mây đứng yên, camera bay vòng r 30 m, y 15 m, 15 s/vòng, ngược chiều kim đồng hồ), 3 s khởi động, vsync tắt, 1280×720 | `python3 -m game.bench --seed 42 --duration 30 --out bench.json`; `test_bench_scene_rules` kiểm luật của cảnh | [bench.json](bench.json) | Lệnh chạy đúng, thoát mã 0, đủ trường. **Trên máy này chưa đạt ngưỡng FPS:** avg 43.0 (cần ≥ 60), p1_low 27.3 (cần ≥ 30). load_ms 4193 (≤ 10000: đạt). |
| Soak 10 Đêm, 0 crash, mem_end ≤ 1.2 × mem_start | `python3 -m game.soak --seed 7 --nights 10 --out soak.json`; `test_soak_short_run`; chạy cả trong CI | [soak.json](soak.json): crashes 0, 22.5 → 22.5 MB | Đạt |
| Bảng xếp hạng: tên 3–12 ký tự (có dấu được), top 10, sắp theo điểm, bằng điểm thì ai đạt trước đứng trên, lưu đĩa, ISO 8601 có múi giờ | `test_leaderboard_name_rule`, `test_leaderboard_top10_order_ties_persist` | [phase4_name.png](phase4_name.png), [phase4_board.png](phase4_board.png) | Đạt |
| `--export-leaderboard out.json` | `test_export_leaderboard_cli` | [leaderboard_export.json](leaderboard_export.json) | Đạt |
| Đổi phím (9 hành động), phát hiện trùng, khôi phục mặc định, được lưu | `test_key_conflict_and_defaults` + ảnh | [phase4_controls.png](phase4_controls.png) | Đạt (báo trùng phím: kiểm bằng tay) |
| Phụ đề / chỉ báo: Bóng Mực xuất hiện (+ mũi tên ở mép), gió sắp thổi, 10 s cuối, đèn < 30 dầu | Chơi tay | `Hud.caption`, `Game._shade_cue_arrow` | Đạt (kiểm bằng tay, chưa có ảnh) |
| Giảm chuyển động (tắt rung camera, chớp màn hình, nhấp nháy đồng hồ) | Chơi tay | [phase4_settings.png](phase4_settings.png) | Đạt (kiểm bằng tay) |
| Chữ UI ≥ 18 px ở 1280×720; tùy chọn ×1.25 | Mọi chữ UI có cỡ ≥ 1.0 (= 0.025 × 720 px) trong `ui.txt()`; chữ lớn dựng lại UI với ×1.25 | [phase4_play.png](phase4_play.png), [phase4_board.png](phase4_board.png) (chữ lớn) | Đạt |
| README (ảnh, yêu cầu hệ thống, cài đặt ≤ 3 lệnh, điều khiển, test/headless/bench/soak), CHANGELOG cho 4 phase, CREDITS, LICENSE | Đọc tài liệu | [README](../../../README.md), [CHANGELOG](../../../CHANGELOG.md) | Đạt |
| Release v1.0.0 có bản chạy được | Push tag `v1.0.0` → workflow `release.yml` build bằng PyInstaller cho Linux/macOS/Windows + gói mã nguồn | `.github/workflows/release.yml` | **Chưa kiểm chứng:** workflow chưa chạy (cần push tag). Gói mã nguồn kèm `run.sh`/`run.bat` luôn dùng được |
| Hồi quy Phase 1–3 | 58 test | `python -m pytest -q` | Đạt |

Ghi chú trung thực:
- **FPS:** mình đã tối ưu, avg từ 26 lên 43:
  - gộp mesh Bóng Mực (3 node mỗi con),
  - bỏ entity tĩnh khỏi vòng `update` của Ursina,
  - gọi Panda trực tiếp khi đồng bộ vị trí,
  - MSAA 2×, bóng đổ 1024.

  Nhưng trên GPU tích hợp, cảnh 200 Bóng Mực vẫn chưa đạt 60 FPS.
- **Video demo:** chưa có. Tác giả cần tự quay.
