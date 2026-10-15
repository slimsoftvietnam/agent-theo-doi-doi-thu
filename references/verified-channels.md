# Nguồn của FPT AI, Viettel AI và VNPT AI

Kiểm tra ngày 15/10/2026. Các URL được dùng để cấu hình theo dõi, không phải bằng chứng rằng API của nền tảng đã cấp quyền đọc.

| Đối thủ | Website tin tức | Fanpage | TikTok | YouTube |
|---|---|---|---|---|
| FPT AI | https://fpt.ai/news/ | `fptai.platform` trong cấu hình trước; chưa đối chiếu được từ website chính thức | Chưa xác nhận username | Channel ID `UC64g9GmKyG_N-xZHGFRITyQ` theo cấu hình trước; RSS hiện trả HTTP 404 |
| Viettel AI | https://viettelai.vn/tin-tuc | https://www.facebook.com/viettelai | https://www.tiktok.com/@viettelai | https://www.youtube.com/channel/UCEBCsy_47ZJ3z3kSH6AnO1w |
| VNPT AI | https://vnptai.io/vi/news | Chưa xác nhận Page ID | Chưa xác nhận username | Chưa xác nhận channel ID |

Viettel AI đặt trực tiếp ba liên kết mạng xã hội ở chân trang https://viettelai.vn/en. Trang tin FPT và VNPT được tìm từ website của mỗi đơn vị. Kết quả Google News về mạng xã hội có thể là bài nhắc thương hiệu từ tài khoản khác; vì vậy chỉ dùng mức `SEARCH_INDEX_ONLY` cho đến khi định danh nguồn và API được xác nhận.

Khi có URL chính thức mới, cập nhật `config/monitor.toml`, chạy `python monitor.py validate-config`, rồi chạy một lượt theo dõi để kiểm tra lại trạng thái.
