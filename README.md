# Đảo Đèn Lồng

> Video demo: _(sẽ bổ sung ở Phase 4)_ · Đề lab: [LAB.md](LAB.md) · Bằng chứng: [Phase 1](docs/proof/phase1/README.md) · [Phase 2](docs/proof/phase2/README.md) · [Phase 3](docs/proof/phase3/README.md) · [CHANGELOG](CHANGELOG.md) · [ADR 0001](docs/adr/0001-lantern-fuel-and-dawn-win.md)

Game 3D góc nhìn thứ ba qua 3 Đêm. Mây, người giữ đèn nhỏ tuổi đội nón lá, gom đom đóm để thắp lại các Đèn Lồng Lớn trên Đảo Bến, Đảo Cau và Đảo Chuông trước bình minh. Trên đường đi phải né Bóng Mực và Gió Lạc.

## Cài đặt và chạy (macOS / Linux / Windows, Python ≥ 3.10)

```bash
python3 -m pip install -r requirements.txt   # cài Ursina (engine 3D)
python3 -m game.app                          # chơi: Menu → Đêm 1 → 2 → 3 → Bình Minh
```

Chế độ headless (Test Contract **v1.2**, không cần cửa sổ, GPU hay Ursina):

```bash
python3 -m game.headless --seed 1 --night 1|2|3 --ticks 21600 --out out.jsonl [--scenario s.json] [--inputs i.json] [--snapshot-every 10]
```

- Chạy test: `python3 -m pip install -r requirements-dev.txt && python3 -m pytest -q`
- Sinh lại bằng chứng: `python3 tools/run_proof.py phase3`
- Đo FPS: `python3 -m game.app --night 1 --bench 15`
- Tạo lại âm thanh: `python3 tools/gen_sounds.py`

## Điều khiển

| Phím | Hành động |
|---|---|
| Phím mũi tên hoặc W A S D | Chạy (camera cố định góc chéo, ↑ là đi lên màn hình) |
| Space | Nhảy |
| Shift | Lướt (14 m/s trong 0.2 s, hồi 1.5 s) |
| E | Nạp đom đóm để thắp đèn, thắp lại đèn đã tắt, hoặc châm dầu cho đèn đang sáng (trong 2 m) |
| F (hoặc Q) | Tỏa Sáng: tốn 3 đom đóm, làm choáng và đẩy lùi Bóng Mực trong 5 m, đuổi Gió Lạc |
| Giữ chuột phải và kéo | Xoay góc nhìn (độ nhạy chỉnh trong Cài đặt) |
| Esc hoặc P | Tạm dừng: Tiếp tục / Chơi lại Đêm / Cài đặt / Về menu |
| R | Chơi lại Đêm |
| Enter | Bấm nút chính trên màn hình đang mở |

## Luật chơi (Ticket-02 + Ticket-03 "Đèn cạn dầu")

- **Mục tiêu:** giữ đảo sáng tới bình minh. Thắng khi còn sống lúc hết giờ và số đèn đang sáng ≥ 60% (3/5, 4/6, 5/7). Thắp đủ đèn không làm Đêm kết thúc sớm.
- **Ba Đêm:**
  - Đêm 1 — Đảo Bến: 5 đèn, 240 s.
  - Đêm 2 — Đảo Cau: 2 đảo nối bằng cầu tre, có bục nhảy, 6 đèn, 270 s.
  - Đêm 3 — Đảo Chuông: 3 tầng, có dốc, bục nhảy, gió mạnh mỗi 30 s, 7 đèn, 300 s.
- **Đèn có dầu:**
  - Thắp lần đầu cần 10 đom đóm. Đèn vừa thắp có 100 dầu và hao 1 dầu mỗi giây.
  - Bấm E ở đèn đang sáng để châm dầu: mỗi đom đóm thêm 10 dầu.
  - Hết dầu thì đèn tắt. Thắp lại đèn đã từng sáng chỉ cần 5 đom đóm.
  - Đèn còn từ 30 dầu trở lên có vùng an toàn bán kính 6 m.
- **Bóng Mực:**
  - Đuổi Mây với tốc độ 4 m/s (Đêm 3 là 4.5 m/s).
  - Khi đang đi lang thang, chúng tìm tới đèn yếu (dưới 30 dầu) để **hút dầu** (5 dầu/giây mỗi con).
  - Tỏa Sáng làm chúng choáng.
- **Đom đóm:** nhặt trong 1 m. Sức chứa bắt đầu là 10, mỗi lần thắp thành công tăng 2, tối đa 20.
- **Gió Lạc** (Đêm 2, 3): cướp đom đóm. **Bùa Gió:** chạy nhanh hơn, Lướt không cần hồi chiêu. **Rơi khỏi đảo:** mất 1 Ngọn Lửa và toàn bộ đom đóm.

## Cách tính điểm

| Sự kiện | Điểm |
|---|---|
| Mỗi đom đóm nạp vào đèn (thắp, thắp lại hoặc châm dầu) | +5 |
| Thắp lần đầu / thắp lại | +100 / +40 |
| Bóng Mực trúng Tỏa Sáng | +5 (+15 nếu nó đang hút dầu) |
| Bình minh (khi thắng): mỗi đèn đang sáng | +50 + số dầu còn lại |
| Bình minh (khi thắng): mỗi Ngọn Lửa còn lại | +50 |

Tổng điểm game là tổng điểm các Đêm đã thắng.

## Test Contract v1.1

- `game.contract.json` ở gốc repo. Không có giá trị `null`. Game đọc tuning trực tiếp từ file này.
- Thứ tự xử lý một tick theo đúng ticket. Bản đồ chuẩn nằm trong `game/core/maps.py`.
- Các giả định cho chỗ ticket chưa quy định (ví dụ: `spawning` kéo dài 30 tick, Đêm 3 xuất phát tại (0,0,−30), `invuln` là boolean): xem [phase2-spec.md](docs/notes/phase2-spec.md) mục 2.
- Một Đêm đầy đủ chạy dưới 1 giây. Thay đổi phá tương thích của v1.2: [CHANGELOG.md](CHANGELOG.md). Quyết định thiết kế: [ADR 0001](docs/adr/0001-lantern-fuel-and-dawn-win.md). Giả định Phase 3: [phase3-spec.md](docs/notes/phase3-spec.md).

## Cấu trúc

```
game/core/sim.py      toàn bộ luật chơi (Python thuần, tất định)
game/core/maps.py     3 bản đồ chuẩn: mặt đất, tầng, dốc, cầu, bục nhảy, tháp
game/headless.py      CLI theo Test Contract
game/app.py           chuỗi 3 Đêm, đồng bộ hình ảnh/âm thanh (không chứa luật)
game/view/            shader, phong cảnh, nhân vật, HUD và màn hình, âm thanh/cài đặt
game/assets/          font Mali (OFL), âm thanh tự tổng hợp
tests/                pytest (44 test) + tests/scenarios/*.json (mỗi tính năng ≥ 1 scenario)
tools/                run_proof.py (bằng chứng), gen_sounds.py (âm thanh)
CLAUDE.md, .claude/   harness AI (hook Stop chạy pytest, skill run-proof)
docs/notes/           spec, giả định, nhật ký dùng AI
```

## Sáng tạo của tôi

Toàn bộ phần thêm chỉ nằm ở lớp hiển thị (`game/view/`), không làm đổi đầu ra headless. Màu của các thành phần mà ticket liệt kê theo đúng bảng màu chuẩn; phần còn lại do mình tự thiết kế.

- **Phong cảnh làng quê dưới trăng:** rặng tre, cây đào hồng, hoa nhỏ, đá, đường đá màu cát, hàng rào gỗ, trăng, sao và biển mây.
  - Đêm 2 có cầu tre trên cọc gỗ.
  - Đêm 3 có các tầng vách đất, dốc lát cát, và tháp chuông mái ngói có quả chuông vàng.
- **Ông Đăng:** người làm đèn già, nhân vật mới của mình. Ông nói một câu dặn riêng ở màn giới thiệu mỗi Đêm.
- **Mây:** dáng chibi, áo kem, khăn đỏ, nón lá treo đèn lồng nhỏ đung đưa. Mây nhún theo bước chạy, nghiêng người khi lướt, nhấp nháy khi bất tử.
- **Bóng Mực:** hình giọt mực có đuôi ngoe nguẩy và viền phát sáng tím. Khi xuất hiện, nó trồi lên từ mặt đất.
- **Gió Lạc:** dải lụa xám xanh uốn lượn. **Bùa Gió:** lá bùa xoay tròn, phát sáng.
- **Gió mạnh:** lá bay ngang màn hình và có tiếng gió báo trước 2 s.
- **Âm thanh:** tự tổng hợp bằng code (`tools/gen_sounds.py`): nhạc ru đêm theo âm giai ngũ cung, cùng 13 hiệu ứng.
- **Đèn cạn dầu:** thanh dầu trên đèn, đèn nhấp nháy khi sắp hết dầu; đèn tắt bị xẹp và có vết rách nên nhận ra được mà không cần nhìn màu. Có chế độ "Bảng màu dễ phân biệt" trong Cài đặt. Bóng Mực phập phồng khi đang hút dầu.
- **Ánh sáng:** shader tự viết. Đèn đã thắp chiếu vầng sáng ấm xuống đúng tầng của nó. Cả đảo sáng dần theo số đèn đã thắp.

Bằng chứng phần lõi vẫn đúng: [pytest.txt](docs/proof/phase3/pytest.txt) (44 passed). `game/core` không import Ursina.

## Giấy phép

[LICENSE](LICENSE) (MIT) · [CREDITS.md](CREDITS.md)
