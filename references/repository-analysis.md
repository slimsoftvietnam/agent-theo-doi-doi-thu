# Quan hệ với repository tham khảo

Agent này được thiết kế sau khi xem xét repository `slimai-content-engine` của cùng tài khoản. Bản công khai chỉ ghi các nguyên tắc được áp dụng, không chứa mã nguồn, commit, chi tiết nội bộ hay thông tin đăng nhập của repository tham khảo.

- Giữ cách triển khai cục bộ bằng Python và SQLite để dễ chạy, lưu lịch sử và chống trùng.
- Tận dụng API/RSS hợp lệ, chuẩn hóa URL/ngày, ghi trạng thái nguồn và lưu manifest từng lượt chạy.
- Không đưa chức năng xuất bản, nhắn tin hoặc quản lý credential vào Agent chỉ-đọc này.
- Bổ sung collector Facebook, TikTok, YouTube, website và tin ngành; phân biệt bài gốc đã kiểm chứng với tín hiệu chỉ mục.
- Bổ sung quy trình kiểm chứng trực tiếp trên kênh chính thức và báo cáo thị trường theo PEAS.

Mã trong skill là bản triển khai độc lập cho mục đích theo dõi đối thủ.
