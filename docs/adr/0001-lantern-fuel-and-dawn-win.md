# ADR 0001 — Đèn có nhiên liệu và luật thắng "giữ đảo sáng tới bình minh" (Ticket-03)

- Trạng thái: Đã chấp nhận (Phase 3, contract v1.2)
- Bối cảnh: Ở Phase 2, đèn chỉ có hai trạng thái `tắt → sáng` (một chiều), và game kết thúc ngay khi thắp hết đèn. Người chơi giỏi thắng sau khoảng 2 phút, nên cuối Đêm thiếu căng thẳng. Ticket-03 yêu cầu đèn có thể tắt lại, và mục tiêu đổi thành giữ đủ đèn sáng tới bình minh.

## Quyết định

1. **Mô hình trạng thái đèn** (`game/core/sim.py`, class `Lantern`):

   ```
   UNLIT(ever_lit=False) --nạp đủ 10--> LIT(fuel=100) --fuel<=0--> UNLIT(ever_lit=True, deposited=0)
   UNLIT(ever_lit=True)  --nạp đủ 5 --> LIT(fuel=100, relit_count+1)
   LIT --châm dầu (E)--> LIT (fuel += 10 x used, tối đa 100)
   LIT & fuel < 30  => mất vùng an toàn, thu hút Bóng Mực đang wander
   ```

   - Dầu lưu bằng **số nguyên đơn vị 1/60** (`fuel_u`, 100 dầu = 6000). Mỗi tick hao 1 đơn vị; mỗi Bóng Mực đang hút trừ thêm 5 đơn vị. Cách này tránh sai số số thực, nên so sánh ngưỡng (`>= 30` nghĩa là `>= 1800`) luôn chính xác. Chỉ đổi sang số thực khi xuất snapshot (1 chữ số thập phân).
   - Việc trừ dầu và tắt đèn đặt ở **bước 2** của tick (ngay sau các bộ đếm), đúng thứ tự ticket yêu cầu. Nhờ vậy, ở bước 5 Mây luôn thấy trạng thái đèn đã cập nhật của tick hiện tại.
   - Vùng an toàn chuyển thành **thuộc tính suy ra** (`Sim._safe(l) = lit and fuel_u >= 1800`) thay vì gắn cứng với `lit`. Mọi chỗ trước đây kiểm `l.lit` cho vùng an toàn (chặn ở mép, đẩy ra) đều chuyển sang dùng `_safe`.
   - Thêm trạng thái Bóng Mực **`drain`** với mục tiêu `target` (id đèn). Chuyển trạng thái nằm ở bước 8, còn lượng dầu bị hút được trừ ở bước 2. Khi đèn vượt ngưỡng 30 do được thắp hoặc châm, dùng chung cơ chế đuổi ra (`_evict_from`) như khi đèn vừa thắp.

2. **Luật thắng** (bước 11): bỏ thắng sớm và bỏ thưởng thời gian. Sau mọi cập nhật của tick: hết lửa → thua `no_flames` (xét trước tiên); nếu đã tới bình minh thì số đèn đang sáng ≥ `ceil(win_ratio × tổng)` → thắng `dawn_survived`, ngược lại → thua `dawn`. Điểm bình minh = Σ(50 + floor(dầu)) cho mỗi đèn đang sáng, cộng 50 cho mỗi Ngọn Lửa còn lại.

3. **Sức chứa** chuyển thành thuộc tính tính theo `successful_lights` (đếm cả lần thắp lại, không đếm đèn đặt sẵn qua scenario), thay cho hằng số `carry_capacity`.

## Hệ quả

- Ưu điểm: chỉ một nơi quyết định "an toàn" và một nơi trừ dầu, nên dễ kiểm chứng và giữ được tính tất định. Toàn bộ test Phase 2 không liên quan đến luật bị thay vẫn giữ nguyên.
- Đánh đổi: Bóng Mực `wander` giờ có chủ đích (tới đèn yếu, sau đó về đèn tắt gần nhất), nên di chuyển khác Phase 2. Không có test ẩn nào ràng buộc quỹ đạo `wander`, nên rủi ro thấp.
- Test bị thay: xem [CHANGELOG.md](../../CHANGELOG.md) và các test có đánh dấu `[T03]` trong `tests/test_headless.py`.
