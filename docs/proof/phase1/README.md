# Bằng chứng Phase 1

Tái lập: `python3 tools/run_proof.py phase1` (chạy CLI thật 2 lần mỗi scenario, so sánh byte, lưu JSONL + [summary.md](summary.md) + [pytest.txt](pytest.txt)).

| Yêu cầu PRD-0 / Contract | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Màn Đêm 1 – Đảo Bến, đảo tròn, 5 đèn | Snapshot tick 0 + ảnh | [random_night.jsonl](random_night.jsonl) dòng 1, [shot_menu.png](shot_menu.png) | Đạt |
| Đi lại, nhảy, camera 3D | Test tốc độ/yaw; scenario random_night có jump; chơi thật | `test_cam_yaw_rotation`, [shot_play.png](shot_play.png) | Đạt |
| Đom đóm rải rác, nhặt được | Scenario basic_light | [summary.md#basic_light](summary.md) – 5 × `mote_picked` | Đạt |
| Nạp ánh sáng thắp đèn | basic_light: deposit 5 → `lantern_lit` L1 tick 221 | [basic_light.jsonl](basic_light.jsonl) | Đạt |
| Bóng Mực đuổi, chạm mất máu | hit_lose: `player_hit` tick 1 và 91 (bất tử 90 tick), thua `no_flames` | [hit_lose.jsonl](hit_lose.jsonl) | Đạt |
| Tỏa sáng xua Bóng Mực, tốn ánh sáng | pulse_stun: S1 choáng + đẩy, S2 (20 m) không; lần 2 trong hồi chiêu không phát | [pulse_stun.jsonl](pulse_stun.jsonl) | Đạt |
| Bóng Mực sợ đèn | safe_zone: đứng cạnh L1 đã sáng 60 s, không bị chạm | [safe_zone.jsonl](safe_zone.jsonl), `test_shade_cannot_enter_safe_radius_of_lit_lantern` | Đạt |
| Thắng / thua / điểm | `test_win_all_lit_with_bonus`, dawn.json, hit_lose.json; ảnh màn thắng (549 = 100 + 299 + 3×50) | [shot_won.png](shot_won.png), [dawn.jsonl](dawn.jsonl) | Đạt |
| HUD | Ảnh: Lửa, đom đóm, đèn, thời gian, điểm, hồi chiêu | [shot_play.png](shot_play.png), [shot_lantern.png](shot_lantern.png) (đèn L2 sáng, vùng an toàn, Bóng Mực) | Đạt |
| Chơi lại sau thắng/thua | Nút "Chơi lại" / phím R tạo Sim mới; màn tạm nghỉ | [shot_won.png](shot_won.png), [shot_pause.png](shot_pause.png), `Game.restart` | Đạt (kiểm bằng tay, chưa có test tự động) |
| Headless đúng contract, exit 2 khi sai đầu vào | 19 test pytest | [pytest.txt](pytest.txt) | Đạt |
| Tất định | Mỗi scenario chạy 2 lần giống hệt | [summary.md](summary.md) “deterministic: YES” | Đạt |
| Chạy trên macOS/Linux | CI ubuntu-latest chạy pytest + lệnh headless `python3` | `.github/workflows/ci.yml` | Đạt cho headless (chờ CI xanh sau khi push); bản có giao diện mới thử trên Windows |

Ghi chú trung thực: ảnh chụp bằng chế độ `--screenshot` (`--ui menu|help|pause|play`, `--autoplay` = tự đi thẳng + bấm E) trên Windows 11; ảnh [shot_help.png](shot_help.png) là màn Cách chơi.
