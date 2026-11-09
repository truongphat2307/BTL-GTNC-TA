# Bài tập Address Segmentation bằng Python

## Cập nhật giới hạn thời gian và viết tắt

Mục tiêu là **mỗi request không quá 0,05 giây**. Engine dùng ngân sách xử lý 40 ms/request và 8 ms/trường, kiểm tra đồng hồ ngay trong vòng lặp tra cứu. Nếu trường hết thời gian hoặc alias có quá 512 ứng viên, bỏ toàn bộ kết quả tạm của trường đó, trả `null` và tiếp tục trường kế tiếp. Một trường mơ hồ cũng trả `null`. Không coi trung bình thấp là đủ: benchmark đếm mọi request chạm/vượt 50 ms.

Đây là giới hạn hợp tác trong Python, không thể bảo đảm thời gian thực cứng nếu hệ điều hành treo tiến trình hoặc máy quá tải. Số đo chỉ gồm hàm `parse()`, không gồm khởi động Python, nạp database, truyền mạng và I/O. Muốn phản hồi toàn ứng dụng trong 50 ms cần giữ engine trong bộ nhớ và đo thêm phần giao tiếp.

Viết tắt hỗ trợ rõ nghĩa theo yêu cầu:

- `BĐ`, `BD`, `B.Đ`, `B.D` → `bán đảo` (có nhận chữ thường).
- `HXH`, `H.X.H` → `Hồ Xuân Hương`.
- Alias đường trong database: `LTK`, `SVH`, `NTP`; alias tỉnh: `TP HCM`, `TPHCM`, `HN`...

`BĐ` chỉ mở rộng cụm địa lý, không tạo thêm trường “bán đảo”. Nếu địa danh không nằm trong từ điển thì vẫn để trống. Trong ứng dụng mà BĐ có thể là Bình Định/Ba Đình, cần đổi cấu hình `ABBREVIATIONS` hoặc thêm alias có phạm vi; không tự gán BĐ cho các nghĩa khác. Tên đường HXH chỉ được trả về nếu có trong database và phù hợp tỉnh đã nhận dạng.

Chạy ví dụ:

```sh
python -X utf8 segmenter.py --version after --address "12 HXH, TP HCM"
python -X utf8 segmenter.py --version after --address "BĐ qqqqqq, TP HCM"
```

`testcases_abbreviations.json` có 44 testcase viết tắt bổ sung trên hai snapshot; unit test có fixture bán đảo minh họa (không phải địa chỉ thật), trường bị bỏ qua, 600 ứng viên trùng, đồng hồ mô phỏng hết hạn và input dài. `evaluate.py` kiểm tra thêm 64 request 80 token. Tổng benchmark: 26.828 request; bộ unit test: 16 test. Expected được khai báo độc lập với output parser.

Kết quả thực đo bản cập nhật trên máy này (chạy tuần tự theo 27 batch, không cache kết quả): trung bình **0,002388 s**, p99 **0,007236 s**, lớn nhất **0,039408 s**, **0/26.828 request vượt hoặc bằng 0,05 s**. 44/44 testcase viết tắt và 64/64 testcase dài qua; toàn bộ benchmark đúng 26.704/26.828 (99,54%), còn 124 trường hợp chưa khớp, được giữ nguyên trong `failures.json`. Có thể mất một phần độ chính xác khi bỏ trường hết ngân sách, đúng ưu tiên thời gian phản hồi. Đây là kiểm thử tự tạo, chưa phải điểm trên test giảng viên.

Để chạy theo batch nếu môi trường giới hạn thời lượng tiến trình:

```sh
python evaluate.py --batch-index 0
# Tiếp tục index 1 đến 26, chạy tuần tự.
python evaluate.py --merge-batches
```

Chạy `python evaluate.py` bình thường vẫn thực hiện trọn bộ trong một tiến trình. `load_seconds` khi gộp batch là thời gian nạp chậm nhất trong các batch, không cộng vào latency từng request.

## Chạy nhanh (Python 3.10 trở lên)

Không cài thư viện, không cần Internet khi chạy. Mở terminal trong thư mục này:

```sh
python -X utf8 segmenter.py --version after --address "268 Lý Thường Kiệt, Phường Diên Hồng, TP. HCM"
python -X utf8 segmenter.py --version before --district --address "Xã Thuận Thành, Huyện Cần Giuộc, Tỉnh Long An"
python -m unittest test_segmenter.py
python -X utf8 evaluate.py
```

Output có `result.street`, `result.ward`, `result.province` và thời gian xử lý tính bằng giây. Tên trả về chính là nhãn trong database; không tìm thấy hoặc mơ hồ trả `null`. Truyền `--district` nếu muốn thêm huyện cũ.

Ứng dụng Python nên nạp một lần:

```python
from segmenter import Segmenter
engine = Segmenter.load('database.json')
result = engine.parse('268 Lý Thường Kiệt, Diên Hồng, TP HCM', version='after')
print(result)
```

CLI không truyền `--address` nhận JSON Lines qua stdin, mỗi dòng một request:

```json
{"address":"268 Lý Thường Kiệt, Diên Hồng, TP HCM","version":"after"}
```

Luôn chọn `before` hoặc `after` khi biết phiên bản. Nếu bỏ version, các tên trùng ở hai snapshot có thể trả null để tránh tự chọn sai quan hệ hành chính. Không tự chuyển địa chỉ cũ sang mới: tách địa chỉ và chuyển đổi địa giới là hai bài toán riêng.

## Dữ liệu kèm theo và nguồn

- `source_data/before.json`: snapshot v2.4.1 của https://github.com/thanglequoc/vietnamese-provinces-database (63 tỉnh, 696 huyện, 10.035 xã/phường). Đây là snapshot đầu năm 2025 của nguồn, không khẳng định đầy đủ mọi thay đổi ngay trước 01/07/2025.
- `source_data/after.json`: snapshot v3.0.0 cùng repository (34 tỉnh, 3.321 xã/phường), phục vụ mô hình sau đợt sáp nhập 2025. Không khẳng định cập nhật đến 2026.
- `source_data/streets_HCM.json`: https://github.com/thien0291/vietnam_dataset, file `data/SG.json` nhánh master, tải ngày 26/10/2026. Có 4.078 tên đường duy nhất sau khi lọc tên quá ngắn; chỉ là danh sách lịch sử TP.HCM, không bao phủ toàn quốc. Dùng lại tên đường để nhận dạng trong hai phiên bản; KHÔNG có xác minh tồn tại hoặc quan hệ đường-phường sau sáp nhập. Các tên chỉ có số/ngắn dưới 4 ký tự chuẩn hóa bị loại để giảm nhầm số nhà; có thể thêm lại với quy tắc riêng.
- Giấy phép nguồn được giữ ở `source_data/LICENSE*.txt`. Dữ liệu cộng đồng, cần kiểm chứng khi dùng thực tế.
- `database.json`: dữ liệu đã chuyển về schema chung, không bịa phường hoặc tự gán đường vào phường. `data_summary.json`: thống kê.

Đề gợi ý 10 phường/tỉnh và khoảng 70 đường/phường. Bộ hiện tại chưa đáp ứng độ phủ đường phố đó: không có nguồn đường-phường toàn quốc đã xác minh. Toàn bộ dữ liệu hành chính có sẵn; cần bổ sung đường thực tế hoặc database giảng viên để đánh giá đúng bài chấm riêng.

Schema một bản ghi:

```json
{"id":"after:ward:00004","kind":"ward","name":"Phường Ba Đình","parent_id":"after:province:01","version":"after","aliases":[]}
```

`kind` thuộc province/district/ward/street. ID duy nhất, parent phải tồn tại và không có chu trình. Alias là tương đương do người quản lý cung cấp, không suy diễn mọi chữ viết tắt. Ví dụ muốn output `LTK`, đổi name thành `LTK` và thêm alias `Lý Thường Kiệt` (unit test có kiểm tra đúng ví dụ đề). Sửa dữ liệu xong nạp lại engine.

## Thuật toán và tốc độ

1. Unicode NFD, bỏ dấu, chuẩn hóa đ/Đ, dấu câu, tách CamelCase.
2. Tạo dictionary alias và chỉ mục chuỗi xóa một ký tự trong lúc khởi tạo.
3. Xét các cụm từ liên tiếp có độ dài giới hạn theo từ điển, nhận dạng tỉnh → huyện → phường → đường.
4. Ưu tiên khớp chính xác; lỗi OCR tối đa một phép thêm/xóa/thay ký tự trên tên dài từ 5 ký tự. Truy xuất ứng viên qua chỉ mục, không quét toàn database.
5. Lọc theo version và chuỗi cha đã tìm được, chọn tên dài hơn; nếu các ID cùng điểm vẫn mơ hồ thì trả null. Không tái sử dụng đoạn đã nhận dạng.

Không dùng machine learning, API hoặc dịch vụ bên ngoài. Tiền xử lý tốn bộ nhớ tỷ lệ tổng độ dài alias; mỗi request phụ thuộc số cụm từ và ứng viên khớp. Giới hạn 512 ký tự/80 token/request, 512 ứng viên fuzzy/cụm để tránh truy vấn bệnh lý; vượt giới hạn địa chỉ báo ValueError. Alias cực phổ biến vẫn có thể tăng thời gian; không có bảo đảm thời gian thực cứng trên mọi máy.

Thời gian request chỉ tính `parse()`, không tính nạp JSON/tạo chỉ mục, khởi động Python, I/O hoặc in kết quả. Nạp một lần cho nhiều request. Mục tiêu người dùng <0,05 giây/request; đề PDF còn yêu cầu trung bình ≤0,01 giây. `benchmark.json` ghi mean, p95, p99, max và số request ≥0,05 giây thực đo trên máy chạy. Chạy lại trên máy chấm để xác nhận.

## Testcase và đánh giá

`python build_data.py` tái tạo database và 26.720 testcase xác định từ snapshot nguồn. `python evaluate.py` chạy toàn bộ không cache, ghi `benchmark.json` và `failures.json`.

- Mỗi xã/phường có một testcase tên đầy đủ và một testcase không dấu.
- Có testcase đường TP.HCM và chuỗi hoàn toàn không tồn tại.
- 10 unit test riêng cho ví dụ đề, alias LTK, không dấu/dính chữ, OCR, thiếu nhãn, lọc version, quan hệ cha, mơ hồ, chu trình và giới hạn input.

Expected của bộ lớn sinh trực tiếp từ bản ghi nguồn, không lấy output parser làm đáp án. Đây là kiểm tra tính nhất quán từ điển, không đại diện độ chính xác trên dữ liệu OCR thực hoặc private test. Test có thể thất bại khi tên không dấu trùng, địa chỉ chứa tên tỉnh khác như một phần phường/đường, hoặc thuật toán tham lam chọn nhầm. Xem failures.json; không thay expected để che lỗi. Chưa có 1.000 mẫu development của giảng viên nên chưa thể báo điểm bài chấm.

## Các file chính

- `segmenter.py`: thư viện và CLI.
- `build_data.py`: chuyển dữ liệu và tạo test.
- `evaluate.py`, `test_segmenter.py`: kiểm thử và đo tốc độ.
- `database.json`, `source_data/`: database chạy offline và snapshot gốc.
- `testcases.json`, `benchmark.json`, `failures.json`: test, kết quả, lỗi cần xem.

Đây là lời giải tham khảo để hiểu, chạy thử và chỉnh sửa. Cần tuân thủ quy định tự làm bài của môn học.

