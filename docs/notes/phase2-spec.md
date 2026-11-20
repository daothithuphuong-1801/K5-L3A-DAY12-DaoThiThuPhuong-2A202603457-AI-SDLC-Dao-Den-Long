# Phase 2 — Spec, giả định, tiêu chí nghiệm thu (Ticket-02, Contract v1.1)

## 1. Thay đổi so với Phase 1 (luật cũ bị thay)

| Phase 1 (tự chọn) | Phase 2 (chuẩn) | Ảnh hưởng test |
|---|---|---|
| pickup 1.5 m, interact 3 m, lantern_cost 5, pulse 1 đom đóm / 6 m / cd 2 s / choáng 3 s | 1.0 m, 2.0 m, 10, 3 đom đóm / 5 m (3D, tâm +0.8 m) / 3 s / 120 tick | Viết lại toàn bộ test số liệu với số mới |
| Điểm +10 khi **nhặt** đom đóm, +20 mỗi lần choáng, thưởng 1×giây | +10 mỗi đom đóm **nạp**, +5 mỗi Bóng Mực trúng Tỏa Sáng, 2×giây | `test_deposit_partial_nearest_and_score`, `test_win_bonus_after_tick` thay test điểm cũ |
| Rìa đảo chặn người chơi, `fall_enabled=false` | Rơi khỏi đảo (Y < −10) bị phạt, hồi sinh | Bỏ `test_player_stays_on_island` (luật đã bị thay), thêm `test_fall_lose_motes_respawn_and_last_flame` |
| 30 đom đóm ngẫu nhiên, sinh lại ngay khi nhặt | 20 đầu Đêm tại điểm chuẩn, +1 mỗi 240 tick, trần 30 | Bỏ `test_random_mode_spawns_and_respawns`, thêm `test_mote_spawn_schedule_and_cap` |
| 3 Bóng Mực ngay đầu Đêm, +1 mỗi 30 s, tối đa 6 | 2 con ở tick 300, rồi mỗi 8/7/6 s, tối đa 6/8/10, cách người chơi ≥ 15 m | `test_shade_spawn_schedule_ids_distance` |
| Rơi `floor(carried×0.5)` đom đóm, biến mất | Rơi ra vành 1.5–2.5 m, tồn tại 480 tick, nhặt lại được | `test_hit_drop_ring_invuln_recoil_one_per_tick`, `test_dropped_mote_ttl_and_repick` |
| Thắng xét ngay khi thắp đèn cuối | Xét sau mỗi tick: hết lửa → thua; đủ đèn → thắng (kể cả tick hết giờ); hết giờ → dawn | `test_dawn_and_win_on_last_tick` |
| Trạng thái Bóng Mực `chase`/`stunned` | `spawning`, `wander`, `chase`, `recoil`, `stunned` | `test_shade_chase_speed_detect_and_lose` |

Thiết kế: tách bản đồ ra `game/core/maps.py` (mỗi Đêm một class có `ground(x,z)` trả độ cao mặt đất hoặc `None` = biển mây, `obstacle()` cho tháp chuông). Sim chỉ hỏi `ground()`, nên tầng/dốc/cầu dùng chung một luật di chuyển: bước lên được nếu chênh ≤ 0.35 m (dốc), cao hơn là vách (chặn), thấp hơn thì rơi xuống.

## 2. Giả định cho chỗ ticket chưa nói

| # | Chỗ chưa rõ | Giả định |
|---|---|---|
| B1 | Tăng tốc ≤ 0.1 s | Đổi vận tốc tức thì (0 s), cả trên không |
| B2 | Thời gian `spawning` | 30 tick (Bóng Mực trồi lên khỏi sương), không di chuyển, không gây hit, vẫn trúng Tỏa Sáng |
| B3 | Tốc độ `wander` | 1.5 m/s tới điểm ngẫu nhiên trong 8 m (seeded) |
| B4 | Xuất phát Đêm 2 / Đêm 3 | Đêm 2: (0,0,0). Đêm 3: (0,0,−30) vì (0,0,0) nằm trong tháp chuông trên tầng 2 |
| B5 | Tương tác đèn khác tầng | Thêm điều kiện chênh cao ≤ 1.5 m (như nhặt) |
| B6 | Gió Lạc cướp khi nào | Chỉ khi đang `chase` (tức Mây mang ≥ 5 và trong 15 m) và chạm XZ ≤ 1.2 m |
| B7 | Gió Lạc `removed` | Vẫn nằm trong mảng `drifters` với state `removed`; không tính vào giới hạn 2 con |
| B8 | Bị đẩy khi choáng "gặp vật cản" | Vật cản = biển mây, tháp chuông, vùng an toàn đèn sáng |
| B9 | Vùng an toàn | Mép tính đúng 6.0 m (khoảng cách < 6 là "trong"); Bóng Mực bị đuổi ra 0.2 m/tick (≤ 30 tick) |
| B10 | Điểm trong headless khi thua | Báo điểm đã tích lũy của Đêm (nạp/thắp/Tỏa Sáng); bản chơi chỉ cộng vào tổng game các Đêm thắng |
| B11 | `invuln` trong snapshot | Boolean; `*_s` là giây còn lại |
| B12 | `night_start` | Ghi ngay sau snapshot tick 0 với `tick: 0` |
| B13 | Pause trong headless | Cạnh lên của `pause` bật/tắt; `end.state` = `paused` nếu kết thúc khi đang dừng |
| B14 | Gió Đêm 3 | Bắt đầu ở sim_tick 1800, 3600, …; hướng ngẫu nhiên (seeded); cộng 2 m/s vào vận tốc ngang; báo trước 120 tick (lá bay + âm thanh, chỉ ở bản có giao diện) |
| B15 | Đom đóm rơi khi bị đánh ra ngoài đảo | Vẫn tạo (y = độ cao chân Mây), có thể không nhặt được |

## 3. Tiêu chí nghiệm thu cho các mục ở Phần 3

| Tính năng | Tiêu chí (kiểm chứng được) | Test / scenario |
|---|---|---|
| **Lướt** | Bấm `dash` (cạnh lên) → event `dash`, đi 14 m/s × 12 tick = 2.8 m theo hướng di chuyển, đứng yên thì theo hướng mặt (đầu Đêm +Z); hồi 90 tick tính từ lúc bắt đầu; trên không giữ nguyên Y | `test_dash_distance_cooldown_and_facing`, `test_air_dash_keeps_altitude`, `dash.json` |
| **Gió Lạc** | Sinh tick 1200, 2400… (Đêm 2, 3, tối đa 2, id D1…); idle → chase khi mang ≥ 5 và ≤ 15 m; chạm cướp min(3, mang) + `drifter_steal`; flee 240 tick rồi `removed`; Tỏa Sáng lúc chase → flee không cướp; lúc flee có đồ → `drifter_drop`, thả đom đóm rơi, biến mất sau 120 tick; không làm mất lửa | `test_drifter_steal_flee_and_pulse_drop`, `test_drifter_idle_below_5_and_pulse_chase_to_flee`, `test_drifter_spawn_schedule_night2`, `n2_drifter.json` |
| **Bùa Gió** | Nhặt như đom đóm → `charm_picked {charm_id, charm_ticks: 600}`; tốc độ 7.2 m/s; Lướt không hồi chiêu; xuất hiện lại sau 2700 tick; vị trí Đêm 2 (35,0,0), Đêm 3 (±30,0,25) | `test_charm_speed_dash_no_cooldown_respawn`, `n2_charm.json` |
| **Bản đồ Đêm 2** | Hai đảo r = 28 + cầu tre x∈[26,44], z∈[−2,2]; bục nhảy bắn vy 14, ngang 24 về tâm đảo kia, bay ~1.4 s, phím không ghi đè | `test_night2_bridge_and_pad_flight`, `n2_pad.json`, ảnh `n2_overview.png` |
| **Bản đồ Đêm 3** | Tầng 1 (Y=3, vành 12–24, z>0), tầng 2 (Y=6, r ≤ 8), vách không leo được, 2 dốc 30°/150°, bục (0,3,13) đưa lên tầng 2, tháp r = 2 chặn, gió mỗi 30 s 5 s 2 m/s | `test_night3_cliff_ramp_pad_tower`, `test_night3_wind_gust`, `n3_tiers.json`, `n3_pad.json`, `n3_wind.json` |
| **Rơi khỏi đảo** | Y < −10: một lần, bỏ qua bất tử, −1 lửa, mất hết đom đóm (`player_hit by=fall, lost`), chờ 60 tick, hồi sinh tại xuất phát, bất tử 90 tick; hết lửa thua ngay | `test_fall_lose_motes_respawn_and_last_flame`, `fall.json` |
| **Tạm dừng** | `pause` cạnh lên → `paused`; tick tăng, sim_tick/thời gian/hồi chiêu/spawn/TTL đứng yên, snapshot `state: paused`; bấm lại → `resumed` | `test_pause_freezes_sim`, `pause.json`; bản chơi: Esc/P, menu Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu (`ui_*.png`) |
| **Chuỗi 3 Đêm** | Menu → Intro (tên đảo + lời Ông Đăng) → chơi → kết quả → Đêm kế; thắng Đêm 3 → màn Bình Minh với tổng điểm (tổng các Đêm đã thắng); thua → Chơi lại Đêm | Kiểm bằng tay + ảnh `ui_intro.png`, `ui_result.png`, `ui_dawn.png` |
| **Cài đặt** | Âm lượng và độ nhạy chuột, lưu ở `~/.dao_den_long/settings.json`, đọc lại khi mở game | `test_settings_roundtrip`, ảnh `ui_settings.png` |
| **Âm thanh** | Nhạc nền + hiệu ứng: nhặt, thắp đèn, tỏa sáng, bị đánh, nhảy, lướt, thắng, thua, Bóng Mực xuất hiện, đếm ngược 10 s (mỗi giây), gió | `tools/gen_sounds.py` → `game/assets/sounds/*.wav`; gắn trong `Game.on_event` (kiểm bằng tay) |
| **HUD** | Lửa trên trái; mm:ss trên giữa, đỏ #FF5A5F + nhấp nháy khi ≤ 30 s; đèn k/n + điểm trên phải; thanh 10 ô dưới giữa; hồi chiêu Lướt/Tỏa Sáng dưới phải; nhắc "E — Nạp ánh sáng (x/10)" khi đứng gần đèn; mũi tên chỉ đèn chưa sáng gần nhất khi nó ngoài màn hình | Ảnh `n1_play.png`, `n2_drifter_charm.png` |
| **Bảng màu** | Các thành phần liệt kê dùng đúng hex (xem `game/view/world.py`, `ui.py`); ánh sáng môi trường = 0.15 + 0.55 × tỉ lệ đèn sáng | `world.set_ambience`, ảnh |
| **Hiệu năng** | Headless một Đêm 21.600 tick ≤ 30 s; bản thường ≥ 30 FPS ở 1280×720 | `test_determinism_and_speed_full_night` (< 1 s/Đêm), `docs/proof/phase2/fps.txt` (53–56 FPS) |
