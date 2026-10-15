# Cấu hình `monitor.toml`

## Khởi tạo hồ sơ cho người dùng mới

Sau khi trình bày [báo cáo mẫu](../assets/example-report-2026-10-05_11.html), hỏi tên đối thủ và URL Facebook/TikTok/YouTube của từng bên; website đối thủ tùy chọn. Hỏi tên công ty người dùng, sản phẩm/dịch vụ, khách hàng mục tiêu và ngành/thị trường (website công ty tùy chọn). Không suy ra những thông tin này từ hồ sơ demo. Sao chép cấu hình gần nhất vào `work/<ten-ho-so>.toml`, rồi thay **toàn bộ** danh sách đối thủ, nguồn và từ khóa cho phạm vi mới; file trong `work/` không được đóng gói/đẩy lên GitHub. Trường hợp URL chưa biết, ghi rõ và chỉ thêm nguồn khi đã xác minh.

Có thể thêm bối cảnh doanh nghiệp vào cấu hình riêng:

```toml
[company]
name = "Tên công ty người dùng"
product = "Sản phẩm hoặc dịch vụ chính"
target_customers = "Nhóm khách hàng mục tiêu"
website = "" # tùy chọn
```

Chạy với `--config work/<ten-ho-so>.toml --db work/<ten-ho-so>/monitor.db --runs work/<ten-ho-so>/runs` để không trộn dữ liệu và lịch sử với hồ sơ mẫu. `monitor.py run` xuất HTML theo CSS của báo cáo mẫu; nội dung tự động vẫn cần kiểm chứng/biên tập nếu muốn kết luận tương đương bản mẫu lịch sử.

## Đổi ngành

Sửa `agent.industry`, danh sách `keywords`, rồi thay toàn bộ `[[competitors]]`, `[[topics]]` và `[[sources]]`. Chạy:

```powershell
python monitor.py validate-config
python monitor.py run
```

## Loại nguồn

| Type | Trường cần thiết | Ghi chú |
|---|---|---|
| `rss` | `url` | RSS hoặc Atom trực tiếp. |
| `website` | `url`, tùy chọn `rss_url`, `sitemap_url` | Tìm RSS trước, rồi crawler robots/sitemap/JSON-LD được phép. |
| `google_news` | `query` | Dùng Google News RSS, không giả định bài gốc truy cập được. |
| `web_search` | `search_query` | Brave/Google CSE nếu có khóa, Google News RSS làm fallback; luôn gắn `SEARCH_INDEX_ONLY`. |
| `youtube` | `channel_id` | Data API uploads playlist khi có khóa, sau đó RSS và chỉ mục web. |
| `facebook` | `page_id`, `token_env` | Graph API; thiếu quyền thì chỉ mục web nếu `fallback_search=true`. |
| `tiktok` | `api_mode`, token env hoặc `feed_url` | Display API, Research API được duyệt, feed được phép, sau đó chỉ mục web. |

Mỗi nguồn có `priority` 1–4, `enabled=true/false`. Nguồn ưu tiên cao tăng nhẹ điểm liên quan nhưng không thay thế khớp từ khóa. Hồ sơ ERP/CRM dùng `agent.source_type_priority` để ưu tiên Facebook/TikTok/YouTube (1), rồi website (3) và Google News (4); nếu không cấu hình, từng nguồn giữ `priority` riêng. Đây là thứ tự xem xét/trình bày, không nâng độ tin cậy của tín hiệu chỉ mục.

## Credential

Ví dụ PowerShell cho phiên làm việc hiện tại:

```powershell
$env:YOUTUBE_API_KEY = "..."
$env:FACEBOOK_PAGE_ACCESS_TOKEN = "..."
$env:TIKTOK_ACCESS_TOKEN = "..."                 # Display API, tài khoản đã cấp quyền
$env:TIKTOK_RESEARCH_ACCESS_TOKEN = "..."        # Chỉ khi được TikTok duyệt Research API
$env:BRAVE_SEARCH_API_KEY = "..."                 # Tùy chọn
$env:GOOGLE_SEARCH_API_KEY = "..."                # Tùy chọn, đi cùng GOOGLE_SEARCH_CX
$env:GOOGLE_SEARCH_CX = "..."
python monitor.py run
```

`[discovery].provider = "auto"` thử Brave, Google CSE rồi Google News RSS. Không có khóa vẫn chạy được tầng Google News RSS. Kết quả chỉ mục không có ngày hoặc tương tác sẽ để trống thay vì ước đoán.

Crawler website luôn đọc `robots.txt`, ưu tiên sitemap/RSS/JSON-LD, giới hạn `max_crawl_pages`, tôn trọng `request_delay_seconds` và lưu cache HTTP trong `work/http-cache/`.

Không ghi token trực tiếp vào TOML. Khi chạy bằng Task Scheduler, đặt biến môi trường ở tài khoản Windows chạy tác vụ hoặc dùng trình quản lý secret của doanh nghiệp.

## Lịch

Script mặc định đọc `frequency`, `time` và `weekday` từ khối `[schedule]` trong TOML. Xem trước, không thay đổi hệ thống:

```powershell
powershell -File scripts/install-schedule.ps1
```

Tạo lịch sau khi xác nhận:

```powershell
powershell -File scripts/install-schedule.ps1 -Install
```

Tham số dòng lệnh vẫn có thể ghi đè cấu hình, ví dụ `-Frequency weekly -Weekday MON`. Gỡ lịch bằng `-Remove`.
