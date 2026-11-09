# Hướng dẫn chạy thử trên Windows

## 1. Chuẩn bị

Tải repo bằng **Code → Download ZIP** trên GitHub rồi giải nén, hoặc chạy `git clone https://github.com/truongphat230799/BTL-GTNC-TA.git`. Mở thư mục chứa `run_demo.py`, bấm thanh địa chỉ của File Explorer, gõ `powershell` rồi Enter. Cần Python 3.10 trở lên. Chương trình chạy offline với các file đi kèm.

Kiểm tra Python:

```powershell
python --version
```

Nếu máy nhận lệnh `py` thay vì `python`, thay `python` bằng `py -3` trong các lệnh dưới.

## 2. Chạy 23 testcase minh họa

```powershell
python -X utf8 run_demo.py
```

Mỗi testcase hiển thị input, output, thời gian theo **ms**, PASS/FAIL. 50 ms = 0,05 giây. PASS chỉ khi đúng cả output và thời gian <= 50 ms. Xem kết quả đầy đủ trong `demo_results.json`.

`demo_tests.json` là file dữ liệu test có thể mở bằng Notepad. Mỗi mẫu gồm address, version, database và expected. `database: real` dùng database hành chính/đường kèm bài. `database: synthetic` dùng `demo_fixture_SYNTHETIC.json`: tên Minh Họa chỉ là dữ liệu giả lập để kiểm tra BĐ → bán đảo, không phải địa chỉ thật.

Muốn thêm testcase, copy một object trong mảng, đổi id/address/expected rồi chạy lại. `null` là trường trống trong JSON, không viết thành chuỗi `"null"`. Có thể chạy `python create_demo_tests.py` để phục hồi bộ mẫu ban đầu (ghi đè file demo_tests.json).

## 3. Thử địa chỉ của anh

Tệp `data_mau.jsonl` có một địa chỉ mỗi dòng, kèm phiên bản dữ liệu. Chạy cả tệp trong PowerShell bằng lệnh dưới đây. Kết quả xuất theo thứ tự các dòng đầu vào. Thêm `--district` để hiện huyện của địa chỉ cũ.

```powershell
cmd /c "python -X utf8 segmenter.py --district < data_mau.jsonl"
```

Để chạy một địa chỉ riêng, dùng `--address`.

```powershell
python -X utf8 segmenter.py --version after --address "12 HXH, TP HCM"
python -X utf8 segmenter.py --version after --address "268 LTK, Diên Hồng, TP HCM"
python -X utf8 segmenter.py --version before --district --address "Xã Thuận Thành, Huyện Cần Giuộc, Tỉnh Long An"
```

`before` là database trước sáp nhập; `after` là sau sáp nhập. `--district` cho xuất thêm huyện cũ. `elapsed_seconds` tính bằng **giây**, còn run_demo hiển thị **ms**.

## 4. Chạy bộ kiểm thử lớn

```powershell
python -m unittest test_segmenter.py
python -X utf8 evaluate.py
```

Lệnh thứ nhất chạy 16 unit test. Lệnh thứ hai chạy 26.828 request, có thể mất vài phút cho cả bộ; đây không phải thời gian của một request. Kết quả lưu tại `benchmark.json`; trường `max_seconds` là thời gian request chậm nhất, `requests_over_005` đếm request >= 0,05 giây. `failures.json` giữ các mẫu chưa khớp, không chỉ các mẫu đã đạt.

Thời gian từng request tính sau khi engine đã nạp database. CLI gọi riêng từng lần vẫn phải khởi động Python và nạp lại database, nên tổng thời gian chờ ngoài terminal sẽ dài hơn. Khi tích hợp ứng dụng, tạo một engine rồi gọi parse nhiều lần như README hướng dẫn. Cơ chế ngân sách xử lý không bảo đảm thời gian thực cứng nếu hệ điều hành ngắt tiến trình.

Giới hạn dữ liệu: hành chính có hai snapshot; danh sách đường chỉ có dữ liệu lịch sử TP.HCM, không có bản đồ đường-phường sau sáp nhập đã xác minh. Địa chỉ ngoài phạm vi này có thể trả null.
