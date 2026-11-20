# Phase 3 — Spec, giả định, tiêu chí nghiệm thu (Ticket-03, Contract v1.2)

Quyết định thiết kế: [ADR 0001](../adr/0001-lantern-fuel-and-dawn-win.md). Breaking changes: [CHANGELOG.md](../../CHANGELOG.md).

## Giả định cho chỗ ticket chưa nói
| # | Chỗ chưa rõ | Giả định |
|---|---|---|
| C1 | Bóng Mực `wander` "đi về đèn tắt gần nhất như trước" | Khi không có đèn yếu, `wander` trôi về đèn tắt gần nhất (1.5 m/s); khi đã cách đèn đó ≤ 4 m thì đi lang thang ngẫu nhiên quanh đó |
| C2 | Tốc độ đi tới đèn yếu | Bằng tốc độ đuổi (4 / 4.5 m/s) |
| C3 | Bóng Mực `drain` có gây sát thương không | Không (đứng yên). Nếu Mây vào trong 6 m thì nó chuyển sang `chase` và lúc đó mới gây sát thương |
| C4 | `fuel_drain` | Mỗi con hút ghi một event sau mỗi 60 tick hút liên tục của con đó; `fuel` là lượng dầu sau khi trừ ở tick đó |
| C5 | Đèn "đầy dầu" | `fuel_u == 6000` tại bước 5. Vì dầu hao ở bước 2, đèn đang sáng gần như luôn nhận châm (≥ 1 đom đóm) |
| C6 | Điểm khi thua (headless) | Giữ điểm đã tích lũy trong Đêm, không có điểm bình minh; bản chơi chỉ cộng vào tổng game các Đêm thắng (giống Phase 2) |
| C7 | `successful_lights` từ scenario | Được tính vào sức chứa ngay từ tick 0 |

## Tiêu chí nghiệm thu
| Yêu cầu | Tiêu chí | Test / scenario |
|---|---|---|
| Hao dầu, tắt | Đèn sáng mất 1 dầu/s; fuel ≤ 0 → `lantern_out`, lit=false, deposited=0, ever_lit=true | `test_fuel_decay_and_lantern_out`, `fuel_out.json` |
| Châm dầu | used = min(mang, ceil((100−fuel)/10)), fuel = min(100, fuel+10·used), +5/đom đóm, event `refuel`; đèn đầy không được chọn | `test_refuel_math_full_ignored`, `refuel_relight.json` |
| Thắp lại | ever_lit cần 5, +40, `lantern_lit.relight=true`, relit_count+1 | `test_relight_cost_5_score_40_and_capacity_growth`, `refuel_relight.json` |
| Vùng an toàn theo dầu | fuel < 30 mất vùng; đúng 30 còn | `test_low_fuel_loses_safe_zone_exactly_30_keeps_it`, `test_safe_zone_boundary_exactly_30` |
| Hút dầu | wander → đèn yếu gần nhất → `drain` khi ≤ 2 m, 5/s mỗi con (cộng dồn), `fuel_drain` mỗi 60 tick | `test_wander_shade_drains_weak_lantern`, `drain.json` |
| Thoát `drain` | Mây ≤ 6 m → chase; châm lên ≥ 30 → đẩy ra mép ≤ 30 tick, không gây sát thương; Tỏa Sáng → stunned, +15 | `test_drain_transitions_chase_refuel_eviction_and_pulse_bonus` |
| Luật thắng | Không thắng sớm; bình minh: đèn sáng ≥ 3/5, 4/6, 5/7 → `dawn_survived`; thiếu → `dawn`; hết lửa luôn thua trước | `test_no_early_win_*`, `test_dawn_win_threshold_and_score`, `test_no_flames_beats_dawn_on_last_tick`, `dawn_win.json`, `dawn_lose.json` |
| Điểm bình minh | Σ(50 + floor(fuel)) + 50 × lửa | `test_dawn_win_threshold_and_score` (dawn_win.json: 471) |
| Sức chứa | 10 + 2 × successful_lights, tối đa 20; snapshot `player.capacity` | `test_relight_cost_5_score_40_and_capacity_growth` |
| Contract v1.2 | Khóa tuning mới, thời lượng 240/270/300, các trường snapshot/scenario mới, kiểm tra hợp lệ | `test_contract_v12_standard_numbers`, `test_snapshot_fields_and_night_start`, `test_scenario_lantern_fields_and_validation` |
| Hiển thị | Thanh dầu, nhấp nháy 1 Hz khi < 30, đèn tắt xẹp 20% + rách, chế độ mù màu (#00B3FF, #FFFFFF + ⚠) được lưu | Ảnh `docs/proof/phase3/fuel_drain.png`, `settings_colorblind.png`, kiểm bằng tay |
