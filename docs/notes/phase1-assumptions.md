# Phase 1 — Giả định & tiêu chí nghiệm thu

Nguồn: PRD-0 + Test Contract v1.0. Chỗ PRD mơ hồ → giả định dưới đây (số thực tế ở `game.contract.json`).

## Giả định

| # | Chỗ mơ hồ | Giả định |
|---|---|---|
| A1 | Công nghệ | Python 3 + Ursina. Logic tách riêng (`game/core`) để headless không cần GPU |
| A2 | Hình đảo | Tròn bán kính 40 m, mặt đất Y=0; đèn L1..L5 trên vòng 25 m, L1 tại (0,0,25), cách nhau 72°: Ln = (25·sin(72°·(n−1)), 0, 25·cos(72°·(n−1))), ví dụ L2 ≈ (23.776, 0, 7.725) |
| A3 | Rơi khỏi đảo | Không có: người chơi bị kẹp tại rìa → `fall_enabled=false` |
| A4 | "Máu" | = `flames` (3). Chạm Bóng Mực → −1, bất tử `invuln_s` |
| A5 | Rơi đom đóm khi bị chạm | `floor(carried × hit_drop_ratio)`; đom đóm rơi mất hẳn |
| A6 | Mang đom đóm | Tối đa `carry_capacity`; đầy thì không nhặt (đom đóm vẫn trên đất) |
| A7 | Nạp đèn | Cạnh lên của `interact`, đèn **chưa sáng** gần nhất trong `interact_radius` (hoà → id nhỏ hơn); nạp `min(carried, cost − deposited)`; sáng khi đủ `lantern_cost`. Nạp từng phần được |
| A8 | "Tỏa sáng tốn ánh sáng" | Tốn `pulse_cost` đom đóm đang mang. Thiếu hoặc đang hồi chiêu → không có gì xảy ra, không phát event |
| A9 | Hiệu ứng tỏa sáng | Bóng Mực trong `pulse_radius` (kể cả đang choáng) bị choáng `pulse_stun_s` (đặt lại), đẩy ra xa người chơi `pulse_push_m`; +`per_stun` mỗi con. Event `pulse` phát kể cả khi không trúng con nào |
| A10 | "Bóng Mực sợ đèn" | Chỉ đèn **đã sáng** có vùng an toàn `safe_radius`; Bóng Mực bị đẩy ra mép (safe_radius + 0.01 m) |
| A11 | Bóng Mực | Bay ở Y=1 (tâm), đuổi thẳng theo XZ với `shade_speed`; choáng thì đứng yên, không gây sát thương. Mặc định 3 con ở rìa 38 m, +1 mỗi 30 s (event `shade_spawned`), tối đa 6 |
| A12 | Đom đóm | Mặc định 30 con rải ngẫu nhiên (seed) trong vành 4–38 m; nhặt 1 con thì sinh 1 con mới (chỉ khi `random_motes`) |
| A13 | Thua | Hết flames → `no_flames`; hết thời gian Đêm → `dawn` |
| A14 | Điểm thắng | Thưởng `floor(time_left) × per_second_left + flames × per_flame_left`, chỉ khi thắng |
| A15 | Nhảy | Chỉ đổi Y (không ảnh hưởng khoảng cách XZ) |
| A16 | Scenario | `motes`/`shades` có mặt thì thay danh sách mặc định (kể cả khi `random_*` true, chỉ ảnh hưởng sinh thêm). `time_left_s` đặt độ dài còn lại. Lantern id lạ / sai kiểu → exit 2 |
| A17 | `dash` | Chưa có; chấp nhận trong inputs nhưng bỏ qua |
| A18 | Snapshot | Chỉ phát ở tick chia hết cho `--snapshot-every` (không thêm snapshot cuối); trạng thái cuối nằm ở dòng `end` |

## Thứ tự xử lý 1 tick (k → k+1)
1 giảm bộ đếm (bất tử, hồi chiêu, choáng) → 2 di chuyển/nhảy → 3 nhặt → 4 nạp đèn (có thể thắng, dừng tick) → 5 tỏa sáng → 6 sinh Bóng Mực → 7 Bóng Mực di chuyển → 8 va chạm (có thể thua) → 9 kiểm tra bình minh.

## Tiêu chí nghiệm thu (→ test trong `tests/test_headless.py`)

| Yêu cầu | Tiêu chí | Test |
|---|---|---|
| Contract file | Đủ trường, v1.0 | `test_contract_file_complete` |
| Định dạng output | snapshot mỗi N tick từ 0, dòng `end` cuối | `test_output_format_and_snapshot_cadence` |
| Tất định | cùng seed/inputs → output giống hệt; seed khác → khác | `test_determinism_same_seed_identical` |
| Lỗi đầu vào | tick trùng / JSON hỏng / move ngoài [−1,1] / lantern lạ → exit 2 | `test_bad_inputs_exit_2` |
| Mô hình tick | event của bước k ghi tick k+1; tốc độ = player_speed, vector chuẩn hoá | `test_event_tick_is_k_plus_1_and_movement_speed` |
| Xoay camera | công thức yaw của contract | `test_cam_yaw_rotation` |
| Scenario không phát event/điểm | đèn đặt sẵn lit không cộng điểm | `test_scenario_setup_emits_nothing_and_lit_preset_no_score` |
| Nhặt + nạp + thắp | luồng đầy đủ qua CLI | `test_full_light_scenario_file` |
| Sức chứa | không vượt carry_capacity | `test_carry_capacity` |
| Nạp từng phần, bán kính, cạnh lên | | `test_partial_deposit_and_interact_radius` |
| Thắng + điểm thưởng | | `test_win_all_lit_with_bonus` |
| Bị chạm, bất tử, rơi, thua | | `test_shade_hit_invuln_drop_and_lose` |
| Bóng Mực đuổi | đúng shade_speed | `test_shade_chases_at_speed` |
| Tỏa sáng | choáng, đẩy, tốn, hồi chiêu, hết choáng | `test_pulse_stun_push_cost_cooldown`, `test_pulse_needs_light` |
| Vùng an toàn | không bao giờ ≤ safe_radius | `test_shade_cannot_enter_safe_radius_of_lit_lantern` |
| Bình minh | thua `dawn` đúng tick | `test_dawn_loses` |
| Sinh ngẫu nhiên | 30 đom đóm, S1–S3, S4 ở tick 1800 | `test_random_mode_spawns_and_respawns` |
| Đảo | không ra khỏi bán kính 40 | `test_player_stays_on_island` |
