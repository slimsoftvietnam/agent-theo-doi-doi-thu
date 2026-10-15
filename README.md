# Agent theo dõi đối thủ

Agent Skill cho Codex: theo dõi fanpage Facebook, kênh YouTube/TikTok, website và tin ngành; chống trùng bằng SQLite; lập bản tin có nguồn và ghi rõ những kênh chưa truy cập được.

## Cách dùng nhanh

1. Tải repository này và mở thư mục trong Codex. Skill nằm tại [SKILL.md](SKILL.md), được gọi bằng `$competitor-news-monitor` (tên hiển thị: **Agent theo dõi đối thủ**).
2. Chỉnh đối thủ, từ khóa và nguồn trong [config/erp-crm-vn.toml](config/erp-crm-vn.toml) hoặc [config/monitor.toml](config/monitor.toml). Hồ sơ ERP/CRM mẫu gồm Base.vn, MISA AMIS, 1Office, ECOUNT, FastWork, CloudGO và Odoo.
3. Cài Python 3.11+; chạy `setup.cmd` hoặc `python monitor.py setup`, rồi `python monitor.py validate-config` và `python monitor.py doctor`.
4. Với hồ sơ mặc định, chạy `run.cmd` hoặc `python monitor.py run`. Với ERP/CRM, chạy `python monitor.py --config config/erp-crm-vn.toml --db work/erp-crm-vn/monitor-market.db --runs work/erp-crm-vn/runs run`. Kết quả tự động gồm Markdown, HTML, Excel và lịch sử SQLite trong `work/` (không được đưa lên GitHub).
5. Khi cần báo cáo ngắn cho lãnh đạo, yêu cầu Codex kiểm chứng bài gốc mạng xã hội và biên tập theo [quy trình social-first](references/social-first-report.md). Đầu ra mặc định là HTML một cột, font K2D, có tóm tắt, 5 chủ đề, hoạt động đối thủ, 3 góc bỏ trống, 5 ý tưởng và nguồn cuối trang.

Thứ tự kiểm chứng: API miễn phí hợp lệ → RSS/feed → tìm và đọc bài công khai → trình duyệt Codex khi đã xác nhận tài khoản phụ → trình duyệt ngoài khi có đồng ý riêng cho lần chạy. Trong trình duyệt, vào trực tiếp kênh chính thức và đọc các bài/video mới, không dùng tìm kiếm từ khóa trên nền tảng thay cho bước này. Mọi bước chỉ đọc; không thích, bình luận, theo dõi hoặc nhắn tin. Nếu bị chặn, báo lý do và cách khắc phục; không nhận là đã quét thành công.

Chạy kiểm thử: `python -m unittest discover -s tests -v`. Đóng gói: `python scripts/package.py` (ZIP trong `dist/`).
