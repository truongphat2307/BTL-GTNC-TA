"""Generate readable examples with independently specified expected outputs."""
import json
from pathlib import Path

ROOT = Path(__file__).parent


def main():
    cases = []
    def add(category, address, street=None, ward=None, province='Thành phố Hồ Chí Minh',
            version='after', database='real'):
        cases.append(dict(id=len(cases)+1, category=category, address=address,
                          version=version, database=database,
                          expected=dict(street=street, ward=ward, province=province)))

    add('Đầy đủ', '268 Lý Thường Kiệt, Phường Diên Hồng, TP HCM', 'Lý Thường Kiệt', 'Phường Diên Hồng')
    add('Không dấu', '268 Ly Thuong Kiet, Dien Hong, TP HCM', 'Lý Thường Kiệt', 'Phường Diên Hồng')
    add('Dính chữ', '268 LyThuongKiet, DienHong, TPHCM', 'Lý Thường Kiệt', 'Phường Diên Hồng')
    add('Viết tắt HXH', '12 HXH, TP HCM', 'Hồ Xuân Hương')
    add('Viết tắt có dấu chấm', '12/3 H.X.H, TP. HCM', 'Hồ Xuân Hương')
    add('Viết tắt chữ thường', '12 hxh, tphcm', 'Hồ Xuân Hương')
    add('Alias LTK', '268 LTK, Diên Hồng, TP HCM', 'Lý Thường Kiệt', 'Phường Diên Hồng')
    add('Alias SVH', '10 SVH, TP HCM', 'Sư Vạn Hạnh')
    add('Alias NTP', '20 NTP, TP HCM', 'Nguyễn Tri Phương')
    add('OCR sai một ký tự', '268 Ly Thuong Kiet, Dien Hongg, TP HCM', 'Lý Thường Kiệt', 'Phường Diên Hồng')
    add('Thiếu phường', '12 HXH, TP HCM', 'Hồ Xuân Hương')
    add('Phường không có trong database', '12 HXH, qqqqqq, TP HCM', 'Hồ Xuân Hương')
    add('Trước sáp nhập', 'Xã Thuận Thành, Huyện Cần Giuộc, Tỉnh Long An',
        ward='Xã Thuận Thành', province='Tỉnh Long An', version='before')
    add('HXH trước sáp nhập', '12 HXH, TP HCM', 'Hồ Xuân Hương', version='before')
    add('BĐ không có địa danh trong từ điển', 'BĐ qqqqqq, TP HCM')
    add('Hoàn toàn không biết', 'zzzzzz qqqqqq', province=None)
    add('Chuỗi rỗng', '', province=None)
    add('Địa chỉ dài 80 token', ' '.join(['zzzzz'] * 80), province=None)
    # These records are intentionally synthetic, not geographic source data.
    for alias in ('BĐ', 'BD', 'B.Đ', 'bđ', 'bán đảo'):
        add('Bán đảo - dữ liệu giả lập', alias + ' Minh Họa, Tỉnh Minh Họa',
            street='Bán đảo Minh Họa', province='Tỉnh Minh Họa', database='synthetic')
    (ROOT / 'demo_tests.json').write_text(json.dumps(cases, ensure_ascii=False, indent=2), encoding='utf-8')
    fixture = [dict(id='demo:p', kind='province', name='Tỉnh Minh Họa', version='after'),
               dict(id='demo:s', kind='street', name='Bán đảo Minh Họa', parent_id='demo:p', version='after')]
    (ROOT / 'demo_fixture_SYNTHETIC.json').write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Created {len(cases)} demo cases; synthetic geography is explicitly labeled.')


if __name__ == '__main__':
    main()
