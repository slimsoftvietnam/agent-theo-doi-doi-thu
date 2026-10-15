# Kiến trúc Agent theo dõi đối thủ

```text
monitor.toml
   │
   ├── Competitors / aliases
   ├── Topics / keywords
   ├── Sources / schedule
   ▼
Collector registry (tối đa 10 worker)
   │  API/RSS · robots/sitemap/JSON-LD · search index fallback
   ▼
Normalize + Evidence + Access status
   ▼
Relevance + Competitor/topic tagging + Event/opinion heuristic
   ▼
SQLite history ── URL/title-date dedupe ── current vs previous window
   ▼
Markdown · HTML · XLSX · JSON
```

## Ranh giới module

- `collectors.py`: chỉ lấy và chuẩn hóa dữ liệu. Không suy luận xu hướng.
- `analysis.py`: gắn thẻ, chấm liên quan và tạo nhận định có nhãn.
- `db.py`: giao dịch, lịch sử và chống trùng.
- `reporting.py`: cùng một payload tạo bốn định dạng.
- `xlsx_writer.py`: writer OOXML tối thiểu bằng thư viện chuẩn; hyperlink và ngày vẫn là dữ liệu có kiểu.

## Trạng thái nguồn

- `HEALTHY`: API/feed/crawler hợp lệ hoàn tất, kể cả khi kỳ này không có mục mới.
- `SEARCH_INDEX_ONLY`: chỉ phát hiện qua chỉ mục tìm kiếm; không chứng minh đã đọc trực tiếp nền tảng.
- `LIMITED`: nền tảng cần credential/feed chưa cấu hình.
- `MANUAL_REVIEW`: URL truy cập được nhưng không tìm thấy phương thức thu thập tự động hợp lệ.
- `ERROR`: HTTP, mạng hoặc parser lỗi.

## Chống trùng

Mỗi mục có hai khóa: URL chuẩn hóa và hash của tiêu đề chuẩn hóa + ngày đăng. Một trong hai trùng sẽ nối mục cũ vào lượt chạy với `is_new=0`, không tạo bản ghi mới.

## Bảo mật

Token không xuất hiện trong TOML mẫu, SQLite, JSON hoặc log. Cấu hình chỉ chứa tên biến môi trường. Agent không tự động hóa trình duyệt để vượt đăng nhập, captcha hoặc giới hạn nền tảng. Cache HTTP chỉ lưu phản hồi công khai của website/feed, không lưu phản hồi API có token.
