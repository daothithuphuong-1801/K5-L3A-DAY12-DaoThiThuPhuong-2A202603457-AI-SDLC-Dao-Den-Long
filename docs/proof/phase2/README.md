# Bằng chứng Phase 2 (Ticket-02, Contract v1.1)

Tái lập: `python3 tools/run_proof.py phase2` (mỗi scenario chạy CLI thật 2 lần, so byte → [summary.md](summary.md), `*.jsonl`, [pytest.txt](pytest.txt)).
Spec + tiêu chí nghiệm thu: [docs/notes/phase2-spec.md](../../notes/phase2-spec.md).

| Yêu cầu | Cách kiểm chứng | Bằng chứng | Kết quả |
|---|---|---|---|
| Số liệu chuẩn trong contract v1.1 | `test_contract_v11_standard_numbers` | [game.contract.json](../../../game.contract.json) | Đạt |
| Snapshot v1.1 (night, wind, vel, grounded, invuln, *_cd_s, charm_s, motes/drifters/charms), `night_start` | `test_snapshot_fields_and_night_start` ×3 Đêm | [random_night.jsonl](random_night.jsonl) dòng 1–2 | Đạt |
| Thứ tự tick, tất định, ≤ 30 s / Đêm | `test_determinism_and_speed_full_night` (21.600 tick, < 1 s mỗi Đêm) | summary.md "deterministic: YES" | Đạt |
| Chạy 6 m/s, nhảy 7 m/s / −20 m/s² | `test_run_speed_instant_and_yaw`, `test_jump_physics_only_grounded` | pytest | Đạt |
| Lướt 14 m/s × 0.2 s, hồi 1.5 s, trên không giữ độ cao | `test_dash_*`, `test_air_dash_keeps_altitude` | [dash.jsonl](dash.jsonl) (dash tick 1, bị bỏ ở tick 31, lại ở tick 91) | Đạt |
| Nhặt ≤ 1.0 m & chênh cao ≤ 1.5 m, sức chứa 10, 20 điểm đầu, +1/240 tick, trần | `test_pickup_*`, `test_mote_spawn_schedule_and_cap` | [basic_light.jsonl](basic_light.jsonl) | Đạt |
| Đèn 10 đom đóm, bán kính 2 m, nạp từng phần, điểm +10/đom đóm +100/đèn, thưởng thắng | `test_deposit_*`, `test_win_bonus_after_tick`, `test_dawn_and_win_on_last_tick` | basic_light: score 200 | Đạt |
| Tỏa Sáng 3 đom đóm / 5 m 3D / 3 s, choáng 120 tick, đẩy 4 m trong 15 tick, +5 | `test_pulse_*` | [pulse_stun.jsonl](pulse_stun.jsonl): S1 trúng, S2 (cao 6.5 m) không | Đạt |
| Bóng Mực 4 / 4.5 m/s, phát hiện 12 / bỏ 18, lịch sinh, hit + rơi vành + recoil + bất tử 90 | `test_shade_*`, `test_hit_*`, `test_dropped_mote_ttl_and_repick` | [random_night.jsonl](random_night.jsonl) (S1,S2 @300, S3 @780), [hit_lose.jsonl](hit_lose.jsonl) | Đạt |
| Vùng an toàn: chặn mép 6 m, đuổi ra ≤ 30 tick khi đèn vừa thắp | `test_safe_zone_block_and_eviction` | [safe_zone.jsonl](safe_zone.jsonl), [safe_zone_evict.jsonl](safe_zone_evict.jsonl) | Đạt |
| Rơi khỏi đảo | `test_fall_lose_motes_respawn_and_last_flame` | [fall.jsonl](fall.jsonl): `player_hit by=fall lost=4` | Đạt |
| Đêm 2: cầu, bục nhảy | `test_night2_bridge_and_pad_flight` | [n2_pad.jsonl](n2_pad.jsonl), [n2_overview.png](n2_overview.png) | Đạt |
| Đêm 3: tầng, dốc, bục, tháp, gió | `test_night3_cliff_ramp_pad_tower`, `test_night3_wind_gust` | [n3_tiers.jsonl](n3_tiers.jsonl), [n3_pad.jsonl](n3_pad.jsonl), [n3_wind.jsonl](n3_wind.jsonl), [n3_overview.png](n3_overview.png) | Đạt |
| Gió Lạc | `test_drifter_*` | [n2_drifter.jsonl](n2_drifter.jsonl): steal tick 16, drop tick 26; [n2_drifter_charm.png](n2_drifter_charm.png) | Đạt |
| Bùa Gió | `test_charm_speed_dash_no_cooldown_respawn` | [n2_charm.jsonl](n2_charm.jsonl): charm tick 10, dash 31 và 46 (không hồi) | Đạt |
| Tạm dừng | `test_pause_freezes_sim` | [pause.jsonl](pause.jsonl) | Đạt |
| Chuỗi 3 Đêm, Intro Ông Đăng, kết quả, Bình Minh | Chơi tay + ảnh | [ui_intro.png](ui_intro.png), [ui_result.png](ui_result.png), [ui_dawn.png](ui_dawn.png) | Đạt (kiểm bằng tay, chưa có test tự động) |
| Cài đặt lưu giữa các lần mở | `test_settings_roundtrip` + ảnh | [ui_settings.png](ui_settings.png) | Đạt |
| Âm thanh (nhạc + 11 hiệu ứng) | Nghe khi chơi | `game/assets/sounds/` | Đạt (kiểm bằng tay) |
| HUD đầy đủ + mũi tên chỉ đèn + nhắc E | Ảnh | [n1_play.png](n1_play.png) (mũi tên "25 m"), [n2_drifter_charm.png](n2_drifter_charm.png) | Đạt; nhắc "E — Nạp ánh sáng" kiểm bằng tay |
| Bảng màu chuẩn, ánh sáng môi trường 0.15 + 0.55×tỉ lệ | Đọc mã (`world.py`, `ui.py`) + ảnh | | Đạt (màu nền; ánh sáng thực tế còn nhân với ánh trăng/bóng) |
| ≥ 30 FPS ở 1280×720 | `python -m game.app --bench 15 --night N` | [fps.txt](fps.txt): 56.2 / 55.1 / 52.9 FPS | Đạt (máy Windows 11, Intel i-series 8 luồng, GPU tích hợp) |
| Hồi quy Phase 1 với số chuẩn | Toàn bộ test Phase 1 viết lại theo số mới, chạy cùng bộ | [pytest.txt](pytest.txt) 35 passed | Đạt |

Ghi chú trung thực: ảnh được chụp bằng `--screenshot` (`--ui`, `--scenario`). Các mục "kiểm bằng tay" chưa có test tự động. Đo FPS chỉ trên máy của mình, chưa đo trên máy chấm.
