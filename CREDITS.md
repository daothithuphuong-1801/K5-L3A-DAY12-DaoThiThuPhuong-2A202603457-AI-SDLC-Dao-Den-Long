# Credits

- Nhân vật, bối cảnh, tên gọi: bản gốc của lab Day 12 "Đảo Đèn Lồng".
- Engine: [Ursina](https://www.ursinaengine.org/) (MIT) trên Panda3D (BSD).
- Font: Mali (Cadson Demak, SIL Open Font License 1.1), bản quyền tại `game/assets/fonts/OFL-Mali.txt`, tải từ github.com/google/fonts.
- Âm thanh: nhạc nền và 13 hiệu ứng do tác giả **tự tổng hợp bằng code** (`tools/gen_sounds.py`, sóng sin/răng cưa/nhiễu), không dùng mẫu âm thanh bên ngoài.
- Nhân vật Ông Đăng (người làm đèn) và lời thoại: tự viết.
- Texture `radial_gradient`, `vertical_gradient` đi kèm Ursina (MIT).
- Mọi mô hình 3D (Mây, đèn, Bóng Mực, cây, tre, ao...) do tác giả dựng từ khối cơ bản/procedural trong code; shader viết riêng. Không dùng model/âm thanh bên ngoài.
- Thiết kế hình ảnh và giao diện là bản tự làm, không sao chép bố cục/màu/chữ của bài khác.
- Thư viện: psutil (BSD, đo bộ nhớ), PyInstaller (GPL kèm ngoại lệ cho bản dựng, chỉ dùng để đóng gói), pytest (MIT, chỉ dùng cho test).
- Công cụ AI tạo nội dung: Claude Code (Anthropic, model Claude Opus) đã viết phần lớn mã nguồn, test, tài liệu, thiết kế hình khối procedural và mã tổng hợp âm thanh. Tác giả điều phối, review và kiểm chứng. Không dùng AI tạo ảnh hay âm thanh dạng file.
