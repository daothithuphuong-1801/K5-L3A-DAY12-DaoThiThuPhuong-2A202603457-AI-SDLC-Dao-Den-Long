# Changelog

## [phase-3] — Ticket-03 "Đèn cạn dầu" — Contract v1.2

### Breaking changes
- `contract_version` đổi thành `"1.2"`. Thời lượng Đêm 1/2/3 đổi thành **240 / 270 / 300 s** (trước là 300/330/360).
- Tuning thêm các khóa: `fuel_max`, `fuel_decay_per_s`, `fuel_per_mote`, `relight_cost`, `win_ratio`, `drain_per_s`, `low_fuel_threshold`, `capacity_max`.
- **Luật thắng:** bỏ thắng sớm. `game_over.reason` không còn `all_lit`; thắng nay chỉ có lý do `dawn_survived` (còn sống tới bình minh và số đèn đang sáng ≥ ceil(0.6 × tổng)).
- **Điểm:**
  - Đom đóm nạp vào đèn: **+5** (trước +10), tính cả khi châm dầu.
  - Thắp lần đầu +100; thắp lại +40.
  - Bóng Mực trúng Tỏa Sáng: +5, hoặc +15 nếu nó đang hút dầu.
  - Lúc bình minh, mỗi đèn đang sáng: +50 + floor(dầu).
  - Bỏ thưởng thời gian (`per_second_left` = 0).
- **Đèn có thể tắt:** dầu hao 1/s; về 0 thì đèn tắt và phát event `lantern_out`. Đèn đang sáng nhưng chưa đầy dầu giờ vẫn là mục tiêu của nút Tương tác (châm dầu).
- **Vùng an toàn** chỉ còn khi dầu ≥ 30 (đúng 30 vẫn an toàn).
- **Bóng Mực** có thêm trạng thái `drain` và trường scenario `target_lantern_id`.
- **Sức chứa** không còn cố định 10: bằng 10 + 2 × số lần thắp thành công, tối đa 20.
- **Snapshot:**
  - Mỗi đèn thêm `fuel` (1 chữ số thập phân; đèn tắt là 0), `ever_lit`, `relit_count`.
  - `player` thêm `capacity`.
- **Event:**
  - Mới: `refuel`, `lantern_out`, `fuel_drain` (mỗi 60 tick đang hút).
  - `lantern_lit` thêm trường `relight`.
- **Scenario:**
  - Đèn nhận thêm `fuel` và `ever_lit`; đèn `lit: true` mà không ghi `fuel` thì mặc định 100. `fuel` ngoài khoảng [0, 100] → mã thoát 2.
  - `player` nhận thêm `successful_lights`.

### Test thay đổi (lý do: luật cũ bị Ticket-03 thay thế)
- `test_contract_v11_standard_numbers` → `test_contract_v12_standard_numbers` (số liệu mới).
- `test_win_bonus_after_tick` và `test_dawn_and_win_on_last_tick`: **xóa**, vì thắng sớm và thưởng thời gian không còn. Thay bằng `test_no_early_win_all_lit_keeps_playing`, `test_dawn_win_threshold_and_score`, `test_no_flames_beats_dawn_on_last_tick`, `test_dawn_loses_without_enough_lanterns`.
- `test_deposit_partial_nearest_and_score`: đổi điểm thành +5 mỗi đom đóm; kiểm thêm `relight: false`.
- `test_snapshot_fields_and_night_start`, `test_pause_freezes_sim`: đổi thời lượng Đêm thành 240/270/300 s.
- Mới: các test về dầu, châm dầu, thắp lại, sức chứa, ngưỡng 30, hút dầu, chuyển trạng thái `drain`, và trường scenario mới.

### Khác (không phá tương thích)
- Bản chơi:
  - Thanh dầu trên đèn; nhấp nháy 1 Hz khi dầu < 30.
  - Đèn tắt bị xẹp 20% và có vết rách trên giấy.
  - Câu nhắc nút E theo ngữ cảnh (Nạp / Thắp lại / Châm dầu).
  - HUD hiển thị `k/n (cần m)` và sức chứa tối đa 20 ô.
  - Cài đặt "Bảng màu dễ phân biệt" (được lưu): Bóng Mực đổi sang viền/mắt #00B3FF, màu cảnh báo đổi sang #FFFFFF kèm biểu tượng ⚠.
- Tài liệu: thêm ADR [docs/adr/0001-lantern-fuel-and-dawn-win.md](docs/adr/0001-lantern-fuel-and-dawn-win.md).

## [phase-2] — Ticket-02 — Contract v1.1
- Số liệu chuẩn, 3 Đêm, Lướt, Gió Lạc, Bùa Gió, rơi khỏi đảo, tạm dừng. Chi tiết: [docs/notes/phase2-spec.md](docs/notes/phase2-spec.md).

## [phase-1] — PRD-0 — Contract v1.0
- Đêm 1 chơi được, chế độ headless, harness AI.
