# Retro — Đảo Đèn Lồng (Day 12, AI SDLC)

## 1. Tổng hợp Evaluation 4 phase

| Phase | Yêu cầu chính | Đạt | Chưa đạt / rủi ro | Hỏng phase trước? |
|---|---|---|---|---|
| 1 — PRD-0, v1.0 | Đêm 1 chơi được, headless | Sim tất định, 19 test, scenario, harness (CLAUDE.md, hook Stop, skill, CI) | **Không commit/tag đúng giờ** | — |
| 2 — Ticket-02, v1.1 | Số chuẩn, 3 Đêm, Lướt, Gió Lạc, Bùa Gió, rơi, tạm dừng, HUD, âm thanh | 35 test, 18 scenario, 53–56 FPS ở cảnh thường | Chuỗi Đêm, âm thanh, câu nhắc chỉ kiểm bằng tay | Có: số liệu Phase 1 bị thay (đã sửa test kèm lý do) |
| 3 — Ticket-03, v1.2 | Dầu đèn, hút dầu, luật thắng bình minh, chế độ mù màu | 44 test, ADR 0001, CHANGELOG | Hiển thị nhấp nháy / đèn rách chỉ kiểm bằng tay | Có: luật thắng sớm bị thay (test `[T03]`) |
| 4 — Ticket-04, v1.3 | Bench, soak, bảng xếp hạng, accessibility, phát hành | 58 test, soak đạt, bảng xếp hạng + xuất file, đổi phím, phụ đề, chữ ≥ 18 px | **Bench trên máy mình 43 / 27 FPS < 60 / 30**; Release v1.0.0 đã tạo kèm video demo; build macOS phụ thuộc runner GitHub | Không (test `[T04]` chỉ nới cho số phiên bản và khóa cài đặt mới) |

## 2. Điều hiệu quả / không hiệu quả khi làm với AI
- **Hiệu quả:**
  - Viết lõi sim thuần Python (không phụ thuộc engine) **trước**, kèm test headless. Ba lần đổi luật (Phase 2, 3, 4) chỉ chạm vào `game/core` và test; phần hiển thị không phải viết lại luật.
  - Cho agent tự chụp màn hình (`--screenshot`) rồi **tự xem ảnh**. Cách này phát hiện được các lỗi mà test không thấy: chữ bị khối 3D che, mặt cỏ bị cull, vệt bóng đổ, toast tưởng là mất.
  - Dầu lưu bằng số nguyên đơn vị 1/60 (Phase 3), nên không có lỗi ngưỡng do số thực.
- **Không hiệu quả:**
  - Làm UI theo ảnh mẫu khiến AI bám quá sát thiết kế của người khác. Mình phải yêu cầu làm lại → mất token.
  - Không commit theo phase: lịch sử git không phản ánh đúng tiến độ, và tag `phase-1`/`phase-2` trỏ vào code Phase 3.
  - Bash heredoc trên Windows nhiều lần vỡ vì dấu nháy, tốn vài lượt chạy lại.

## 3. Những lần AI sai và cách phát hiện
| Lỗi | Phát hiện bằng | Sửa / harness |
|---|---|---|
| Test viết sai kỳ vọng (Phase 2: 4 test; Phase 3: 2 test) | Chạy pytest, đọc kỹ assert, tính tay | Sửa kỳ vọng kèm lý do, không nới tiêu chí; quy tắc trong CLAUDE.md "never weaken a test" |
| Recoil lùi 59/60 bước (1.967 m) | Test tính khoảng cách chính xác | Đếm ngược ngay tại bước di chuyển |
| `Button` có nhãn rỗng làm crash (2 lần) | Chạy chế độ screenshot | Sửa tận gốc trong `ui.button()` |
| UI dùng chung depth buffer; quầng sáng tối đục; mặt cỏ bị cull | Xem ảnh chụp | `set_clear_depth_active`, `unlit_shader`, double-sided |
| Bench 26 FPS: 7.000 entity thừa trong vòng `update` của Ursina | cProfile + đếm entity | Loại khỏi danh sách duyệt, gộp mesh, gọi Panda trực tiếp |

## 4. Harness giúp nhiều nhất
1. **Hook Stop chạy pytest:** đã chặn kết thúc ít nhất 2 lần khi test đỏ (ví dụ lúc thêm khóa `colorblind`).
2. **Chế độ `--screenshot --ui X` và skill `run-proof`:** bằng chứng tái lập được, và agent tự kiểm hình ảnh.
3. **CLAUDE.md ngắn:** quy tắc "core không import Ursina", "tuning chỉ đọc từ contract", "an toàn = `_safe()`" giúp tránh sửa sai chỗ khi đổi luật.
4. **CI** chạy test, headless, soak mỗi lần push.

## 5. Token / chi phí (ước tính)
| Phase | Token vào | Token ra |
|---|---|---|
| 1 (gồm 2 lần làm lại UI) | ~450k | ~110k |
| 2 | ~350k | ~90k |
| 3 | ~200k | ~45k |
| 4 | ~400k | ~100k |
| **Tổng** | **~1.4M** | **~345k** |

Cách tiết kiệm:
- Viết lõi + test trước, rồi kiểm bằng headless vì rẻ.
- Chỉ render ảnh khi cần xem bố cục.
- Gom nhiều sửa đổi nhỏ vào một script Python.
- Profile trước khi tối ưu thay vì đoán.

Tốn kém nhất là 2 lần làm lại giao diện ở Phase 1.

## 6. Nếu làm lại
- Commit và gắn tag **ngay khi hết mỗi phase** (thêm vào checklist trong CLAUDE.md).
- Chốt phong cách hình ảnh của riêng mình từ đầu, không dùng ảnh tham khảo của người khác.
- Thiết kế hiển thị cho nhiều thực thể (gộp mesh, instancing) ngay từ Phase 2, để không phải chữa cháy hiệu năng ở Phase 4.
- Thêm test tự động cho UI (chuỗi màn hình) bằng chế độ screenshot + so sánh ảnh.
