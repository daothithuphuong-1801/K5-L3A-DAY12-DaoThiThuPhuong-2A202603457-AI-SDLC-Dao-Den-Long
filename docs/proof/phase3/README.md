# Bằng chứng Phase 3 (Ticket-03, Contract v1.2)

Tái lập: `python3 tools/run_proof.py phase3` → [summary.md](summary.md), `*.jsonl`, [pytest.txt](pytest.txt) (44 passed). Spec: [phase3-spec.md](../../notes/phase3-spec.md) · ADR: [0001](../../adr/0001-lantern-fuel-and-dawn-win.md) · [CHANGELOG](../../../CHANGELOG.md).

| Yêu cầu | Bằng chứng | Kết quả |
|---|---|---|
| Hao dầu → `lantern_out` | [fuel_out.jsonl](fuel_out.jsonl): đèn có 3 dầu tắt đúng tick 180 | Đạt |
| Châm dầu + thắp lại (5, +40, relight) | [refuel_relight.jsonl](refuel_relight.jsonl): refuel 6 đom đóm → 100.0; L2 thắp lại với 5 đom đóm, `relight: true`; điểm 95 = 6·5 + 5·5 + 40 | Đạt |
| Bóng Mực hút dầu, cộng dồn, `fuel_drain` mỗi 60 tick | [drain.jsonl](drain.jsonl): S1, S2 hút L1 (28 dầu), đèn tắt ở tick 189 | Đạt |
| Thắng lúc bình minh + điểm | [dawn_win.jsonl](dawn_win.jsonl): `dawn_survived`, 471 điểm = 3·50 + (77 + 47 + 97) + 2·50 | Đạt |
| Thua khi thiếu đèn | [dawn_lose.jsonl](dawn_lose.jsonl): 2/5 < 3 → `dawn` | Đạt |
| Ngưỡng 30, chuyển trạng thái `drain`, +15, sức chứa, trường scenario | pytest (xem phase3-spec) | Đạt |
| Hồi quy Phase 1–2 (không bị thay) | 44 test, các scenario cũ vẫn chạy được và cho kết quả giống nhau giữa hai lần chạy | Đạt |
| Hiển thị: thanh dầu, sức chứa 6/14, "Đèn 2 · dầu 20", HUD "k/n (cần m)" | [fuel_drain.png](fuel_drain.png) | Đạt |
| Cài đặt "Bảng màu dễ phân biệt" | [settings_colorblind.png](settings_colorblind.png) | Đạt |
| Nhấp nháy 1 Hz, đèn tắt xẹp + rách, đổi màu khi bật chế độ mù màu | Kiểm bằng tay (chưa có ảnh riêng) | Đạt (kiểm bằng tay) |
