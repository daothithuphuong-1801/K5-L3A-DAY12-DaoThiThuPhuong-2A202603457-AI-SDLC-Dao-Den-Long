# Nhật ký dùng AI

Công cụ: Claude Code (Opus) trong VS Code. Harness: `CLAUDE.md`, hook Stop `.claude/hooks/require_green.py` (chặn kết thúc khi pytest đỏ), skill `.claude/skills/run-proof`, CI GitHub Actions.

## Phase 1

| Bước | Lời nhắc chính / việc | Kết quả |
|---|---|---|
| 1 | "Đọc tất cả file lab" → tóm tắt yêu cầu, lịch, rubric | Hiểu phạm vi; ghi chú README lab chỉ là khung, yêu cầu ở lab board |
| 2 | Dán PRD-0 → "hướng dẫn tôi làm" | Đề xuất Python + Ursina, bảng giả định, bộ tuning, kế hoạch 60 phút |
| 3 | "ok làm luôn, không tự commit" | Agent viết contract → sim → headless → 19 test → app → proof → docs; người duyệt và commit thủ công |
| 4 | "Di chuyển bằng mũi tên, UI đẹp hơn, chuyển động mượt hơn" | Chỉ sửa `game/app.py` (view): mũi tên = di chuyển, camera chuyển sang Z/C; nội suy giữa 2 tick + easing camera/xoay; HUD dạng panel. `core` không đổi → 19 test vẫn xanh, chụp lại ảnh để kiểm |
| 5 | Gửi ảnh mẫu "thiết kế đẹp như thế này, góc nhìn cố định" | Agent dựng lại theo ảnh mẫu (nền xanh ngọc, kính tối, chữ serif) |
| 6 | "Không được sao chép như ảnh, đổi bố cục, phông, màu, nhân vật, phong cảnh" | Làm lại thiết kế riêng: đảo làng quê dưới trăng (tre, đào, ao sen, đường gạch), Mây chibi áo bà ba + khăn đỏ, đèn lụa đỏ cột gỗ, Bóng Mực giọt mực; UI giấy kem + font Mali, dock dưới, thanh đêm→bình minh. Camera cố định yaw 0 (khớp `cam_yaw_deg=0` của contract). `core` không đổi |

Lỗi của AI / sự cố đã phát hiện:
- AI bám ảnh mẫu quá sát (bố cục, màu, câu chữ), có nguy cơ trùng bài khác → người dùng chặn lại; ghi vào `CLAUDE.md` quy tắc "thiết kế phải tự làm, ảnh tham khảo chỉ để lấy cảm hứng".
- Đèn mặt trời làm tối các vật thể phát sáng (Panda bật ánh sáng cố định cho mọi node) → dùng `unlit_shader` + `setLightOff` cho đom đóm/quầng sáng.
- Mặt cỏ bị cull mặt sau và z-fight với nắp vách đảo (thấy màu nâu sọc trong ảnh) → bật double-sided, hạ vách 5 cm; mặt đất không đổ bóng (camera mask) để hết vệt shadow acne.
- Chữ toast "biến mất": thực ra hết thời gian hiển thị nhưng bóng nền không mờ theo → mờ cả bóng; UI dùng bin `fixed` cố định thứ tự vẽ.
- Quầng sáng trong suốt quanh đom đóm hiện thành vòng tối đục (thấy trong ảnh chụp) → bỏ.
- Test `random_mode_spawns` ban đầu đỏ: người chơi đứng yên bị Bóng Mực giết trước giây 30 nên không thấy `shade_spawned`. Đây là lỗi **của test** (game đúng) → sửa scenario cho flames=100, không làm yếu khẳng định.
- `look_at_2d` của Ursina 7 không nhận tuple → crash khi mở game; phát hiện nhờ chạy chế độ screenshot, thay bằng tính `atan2`.
- Ký tự ←/→ không có trong font → hiện ô vuông (thấy trong ảnh chụp); đổi sang chữ.
- Chữ "THẮNG" bị khối đèn 3D che: UI dùng chung depth buffer → bật clear depth cho UI display region. Phát hiện bằng cách **xem ảnh thật**, không phải tin lời agent.

## Phase 2 (Ticket-02, contract v1.1)

| Bước | Lời nhắc chính / việc | Kết quả |
|---|---|---|
| 1 | Dán Ticket-02 → "đọc thật kỹ và làm" | Agent ưu tiên theo điểm: lõi sim + contract v1.1 + test trước (chấm tự động 30đ), rồi hiển thị, rồi tài liệu |
| 2 | Lõi | Tách `core/maps.py` (3 bản đồ, `ground()`), viết lại `sim.py` theo đúng thứ tự 12 bước, headless thêm dash/pause/night_start |
| 3 | Test | 35 test (hồi quy Phase 1 theo số chuẩn + mỗi tính năng mới) + 18 scenario; full Đêm 21.600 tick < 1 s |
| 4 | Hiển thị | Dựng 3 bản đồ từ `maps.py`, Gió Lạc/Bùa Gió, HUD đúng vị trí ticket, bảng màu chuẩn, chuỗi 3 Đêm + Ông Đăng + Bình Minh, Cài đặt lưu file, âm thanh tự tổng hợp, `--bench` đo FPS (53–56) |

Lỗi của AI / sự cố đã phát hiện (Phase 2):
- 4 test đỏ lần đầu đều là **test viết sai** (quên Bóng Mực đã đuổi 1 bước trước khi chạm; choáng 120 tick tính cả tick kích hoạt; Bùa Gió nằm trên cầu làm tăng tốc; dốc chưa lên hết). Sửa kỳ vọng kèm lý do, không nới lỏng tiêu chí.
- 1 lỗi thật do test bắt được: recoil đếm ngược ở bước 2 nên chỉ lùi 59/60 bước (1.967 m) → chuyển bộ đếm recoil về bước di chuyển.
- `Button` của Ursina không có `text_entity` khi nhãn rỗng → crash lúc dựng màn Kết quả; phát hiện bằng chạy chế độ screenshot.
- Proof scenario để Mây chạy mãi rồi rơi khỏi đảo nhiều lần (bằng chứng rối) → thêm frame dừng.

Token/chi phí ước tính Phase 2: ~350k token vào / ~90k token ra. Tiết kiệm: viết lõi + test trước, kiểm bằng headless (rẻ); chỉ render ảnh khi cần xem bố cục; dùng script Python một lần cho nhiều sửa đổi nhỏ.

## Phase 3 (Ticket-03, contract v1.2)

| Bước | Lời nhắc / việc | Kết quả |
|---|---|---|
| 1 | Dán Ticket-03 → "đọc và làm phase 3" | Lõi trước: dầu theo đơn vị nguyên 1/60, `_safe()` thay cho `lit`, trạng thái `drain`, luật thắng bình minh, điểm mới, sức chứa |
| 2 | Test | Sửa 7 test bị luật mới thay (đánh dấu `[T03]` kèm lý do, không skip), thêm 10 test mới → 44 passed; thêm 5 scenario bằng chứng |
| 3 | Hiển thị + tài liệu | Thanh dầu, nhấp nháy 1 Hz, đèn tắt xẹp + rách, chế độ mù màu, HUD `k/n (cần m)`; ADR 0001, CHANGELOG |

Lỗi của AI / sự cố (Phase 3):
- Hai test mới viết sai: kiểm "đèn đầy không được chọn" nhưng quên rằng dầu đã hao ở bước 2 trước bước tương tác; kiểm "đúng 30 vẫn an toàn" với 30.02 dầu nhưng chỉ sau 1 tick đã dưới 30. Sửa bằng cách tắt hao dầu trong test và thêm test ở cấp đơn vị dầu (1800).
- Lặp lại lỗi `Button` có nhãn rỗng (đã gặp ở Phase 2) → lần này sửa tận gốc trong hàm `button()` để không tái diễn.
- Heredoc trong bash vỡ khi chứa nhiều dấu nháy → chuyển sang script Python trong scratchpad.

Token/chi phí ước tính Phase 3: ~200k token vào / ~45k token ra.

## Phase 4 (Ticket-04, contract v1.3)

| Bước | Lời nhắc / việc | Kết quả |
|---|---|---|
| 1 | Dán Ticket-04 → "đọc và làm" | Ưu tiên phần chấm tự động: bench/soak CLI, contract v1.3, bảng xếp hạng + lệnh xuất file, test |
| 2 | Bench quá chậm (26 FPS) | cProfile + đếm entity → 7.000 entity thừa trong vòng update của Ursina, 8 node mỗi Bóng Mực, setter chậm → tối ưu lên 43 FPS (vẫn < 60 trên GPU tích hợp, ghi trung thực) |
| 3 | Accessibility + phát hành | Đổi phím có báo trùng, phụ đề, giảm chuyển động, chữ ≥ 18 px / ×1.25; workflow release PyInstaller; README, CHANGELOG 4 phase, retro |

Lỗi của AI / sự cố (Phase 4):
- Đo hiệu năng bằng `sed` vào chuỗi có `\n` không khớp → tưởng đã tắt MSAA nhưng chưa. Phát hiện khi đọc lại file; sửa bằng công cụ Edit.
- Đường dẫn `/tmp` trong Git Bash bị đổi khác nhau giữa tham số CLI và chuỗi trong `python -c` → bảng xếp hạng trong ảnh bị trống. Không phải lỗi game; chuyển sang đường dẫn tương đối.
- Thêm khóa cài đặt làm đỏ test cũ → hook Stop chặn; cập nhật test `[T04]` kèm lý do.

Token/chi phí ước tính Phase 4: ~400k token vào / ~100k token ra. Tổng dự án ước tính ~1.4M vào / ~345k ra (chi tiết trong docs/retro.md).

Bài học → harness: ghi vào `CLAUDE.md` quy tắc "core không import ursina", "tuning chỉ đọc từ contract", "không làm yếu test". Thêm chế độ `--screenshot` để agent tự chụp và tự xem kết quả hiển thị.

Token/chi phí ước tính Phase 1: ~150k token vào / ~35k token ra (≈ 1 phiên Claude Code). Tiết kiệm: đọc 6 file lab một lần bằng 1 lệnh; viết cả module một lượt thay vì sửa vụn; kiểm chứng bằng headless + pytest (rẻ) trước, chỉ mở game 3D để chụp ảnh khi cần.
