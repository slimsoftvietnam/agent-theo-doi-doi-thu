# Agent theo dõi đối thủ

Agent Skill cho Codex: theo dõi fanpage Facebook, kênh YouTube/TikTok, website và tin ngành; chống trùng bằng SQLite; lập bản tin có nguồn và ghi rõ những kênh chưa truy cập được.

## Cách dùng nhanh

1. Cài repository này như skill Codex rồi gọi `$competitor-news-monitor` (tên hiển thị: **Agent theo dõi đối thủ**). Ở lần gọi đầu tiên, agent sẽ đưa [báo cáo mẫu 05–11/10/2026](assets/example-report-2026-10-05_11.html) để xem trước và hỏi thông tin trước khi chạy. Có thể tự lấy đường dẫn mẫu bằng `python monitor.py preview`. Việc cài đặt đơn thuần không tự kích hoạt agent.
2. Cung cấp tên đối thủ và URL Facebook/TikTok/YouTube của từng bên (nếu chưa biết, agent sẽ hỗ trợ xác minh); website đối thủ là tùy chọn. Cung cấp tên công ty của bạn, sản phẩm/dịch vụ, khách hàng mục tiêu và ngành/thị trường. Agent sẽ tạo cấu hình riêng trong `work/`; [config/erp-crm-vn.toml](config/erp-crm-vn.toml) và [config/monitor.toml](config/monitor.toml) chỉ là hồ sơ mẫu.
3. Cài Python 3.11+; với cấu hình riêng, chạy `python monitor.py --config work/<ten-ho-so>.toml setup`, rồi thay `setup` bằng `validate-config` và `doctor` để kiểm tra. `setup.cmd` chỉ dành cho cấu hình demo mặc định.
4. Chạy với đường dẫn cấu hình riêng như trong [hướng dẫn cấu hình](references/configuration.md). Để thử hồ sơ ERP/CRM mẫu, dùng `python monitor.py --config config/erp-crm-vn.toml --db work/erp-crm-vn/monitor-market.db --runs work/erp-crm-vn/runs run`. Kết quả tự động gồm Markdown, HTML landing page dùng CSS của mẫu, Excel và lịch sử SQLite trong `work/` (không được đưa lên GitHub).
5. HTML từ lệnh `run` là **bản nháp**. Khi người dùng yêu cầu báo cáo, agent phải tự chụp nguồn và tạo **HTML cuối đẹp có ảnh**, không dừng ở bản nháp hoặc nhờ người dùng chụp hộ: chạy `python monitor.py screenshot-plan <run.json>`, mở đúng URL nguồn của 5 chủ đề và lưu 5 ảnh khác nhau vào `screenshots/`, điền thời điểm/phương thức/đường dẫn ảnh trong manifest, rồi chạy `python monitor.py finalize-report <run.json>`. File `*-final.html` dùng thiết kế landing page K2D một cột và nhúng ảnh trực tiếp, không phụ thuộc thư mục ảnh khi chia sẻ. Nếu thiếu nguồn/ảnh thật, báo rõ giới hạn và chỉ bàn giao bản nháp. Xem [quy trình social-first](references/social-first-report.md); mẫu lịch sử có 5 ảnh chụp nguồn của tuần 05–11/10/2026, không được dùng lại chúng làm bằng chứng cho kỳ mới.

Thứ tự kiểm chứng: API miễn phí hợp lệ → RSS/feed → tìm và đọc bài công khai → trình duyệt Codex khi đã xác nhận tài khoản phụ → trình duyệt ngoài khi có đồng ý riêng cho lần chạy. Trong trình duyệt, vào trực tiếp kênh chính thức và đọc các bài/video mới, không dùng tìm kiếm từ khóa trên nền tảng thay cho bước này. Mọi bước chỉ đọc; không thích, bình luận, theo dõi hoặc nhắn tin. Nếu bị chặn, báo lý do và cách khắc phục; không nhận là đã quét thành công.

Chạy kiểm thử: `python -m unittest discover -s tests -v`. Đóng gói: `python scripts/package.py` (ZIP trong `dist/`).
