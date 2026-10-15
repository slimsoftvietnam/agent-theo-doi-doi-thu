# Kiểm chứng mạng xã hội và bản tin điều hành

Đọc tài liệu này khi người dùng cần bản báo cáo cuối, thay vì chỉ xuất dữ liệu collector. Đây là bước biên tập bổ sung; giữ nguyên kết quả chạy tự động và lịch sử SQLite.

## Thu thập theo kỳ

1. Chốt khoảng thời gian và múi giờ. “Tuần trước” là thứ Hai 00:00 đến Chủ nhật 23:59:59 của tuần liền trước tại múi giờ cấu hình. Ghi thời điểm kiểm tra nếu số lượt xem/tương tác có thể thay đổi.
2. Với **từng đối thủ**, xác minh URL fanpage Facebook, profile TikTok và kênh YouTube từ cấu hình hoặc liên kết trên website/kênh chính thức. Đánh dấu chưa xác minh thay vì đoán handle. Thử API miễn phí được cấp quyền, sau đó RSS/feed hợp lệ. Nếu vẫn thiếu, dùng tìm kiếm web để tìm URL bài công khai và đọc bài gốc.
3. Nếu chưa đủ dữ liệu, dùng trình duyệt tích hợp Codex chỉ sau khi xác nhận phiên đăng nhập hiện có là tài khoản phụ được phép dùng cho lần chạy. Vào **trực tiếp kênh chính thức**, xem tab bài đăng/video mới, lần lượt mở các mục trong kỳ. Ghi URL từng bài, ngày, nội dung thực sự đọc được và tương tác nếu hiển thị. Không dùng search từ khóa trong Facebook/TikTok/YouTube thay cho bước này.
4. Chỉ khi vẫn thiếu mới đề nghị Chrome hoặc trình duyệt ngoài; phải có đồng ý cho **lần chạy hiện tại**. Nếu không có phiên hoặc bị lỗi, dừng tại mức bằng chứng đã có. Tuyệt đối không vượt captcha, rào đăng nhập hoặc hạn chế truy cập.
5. Sau khi đã rà xã hội mới dùng website, blog, báo và Google News để bù/đối chiếu. Tin ngành không được gán thành bài đăng của đối thủ. Không dùng tần suất đăng làm bằng chứng nhu cầu thị trường.

Mọi bước chỉ đọc: không thích, bình luận, theo dõi, nhắn tin, đăng bài. Có thể dùng chỉ mục tìm kiếm để *phát hiện* một URL, nhưng nhãn `SEARCH_INDEX_ONLY` phải giữ nguyên cho đến khi mở và kiểm được bài gốc. Với video dài chỉ có mô tả/transcript, nói rõ đang tóm theo phần nào. Không có số tương tác thì để trống, không ước lượng.

## Bảng bằng chứng tối thiểu

Mỗi mục giữ: đối thủ, kênh, tiêu đề/chủ đề, ngày đăng (và múi giờ nếu biết), URL gốc, nội dung tóm tắt, tương tác và thời điểm đọc nếu có, phương thức (`API`, `RSS`, `WEB_ORIGINAL`, `CODEX_BROWSER`, `EXTERNAL_BROWSER`, `SEARCH_INDEX_ONLY`), mức chắc chắn, ghi chú giới hạn. Chống trùng bằng URL chuẩn hóa và khóa nội dung; không xuất lại bài cũ như bài mới.

Tách **sự kiện** (“kênh đăng video X ngày Y”) khỏi **nhận định** (“đây là cơ hội nội dung”). Góc bỏ trống chỉ là giả thuyết trong mẫu tiếp cận, không khẳng định đối thủ chưa từng làm. Nêu lý do và cách khắc phục cho từng nguồn không truy cập được, đặc biệt TikTok/Facebook/YouTube.

## HTML điều hành

- Mặc định đọc khoảng 3 phút, đáp ứng người đi làm không biết lập trình. Một cột dọc; mỗi heading là một section riêng. Không đặt phần “Đối thủ đang làm gì?” bên cạnh “Chủ đề nổi bật”.
- Tiêu đề chính: **Báo cáo phân tích đối thủ**. Dùng font **K2D** (Google Fonts và font dự phòng nếu offline). Thiết kế như landing page chuyên nghiệp, tương phản tốt, responsive và in được.
- Sau hero có khối **tóm tắt ngắn** trước nội dung chi tiết. Bốn phần chính: **5 chủ đề nổi bật**, **Đối thủ đang làm gì?**, **3 góc nội dung còn bỏ trống**, **5 ý tưởng cho tuần tới**. Nguồn thu thập ở cuối trang.
- Bỏ lời chú thích phòng vệ lặp lại ngay dưới các heading. Đặt giới hạn phương pháp ngắn ở cuối nguồn nếu cần. Không trình bày suy luận như sự kiện.
- Số 01–05 ngay trong các mục chủ đề phải mở **trực tiếp bài/video gốc**. Nếu một chủ đề có nhiều bằng chứng, liên kết bằng chứng phụ vào cụm từ tương ứng trong đoạn văn. Không bắt người đọc nhảy xuống cuối trang chỉ để mở nguồn.
- Trong phần đối thủ, xếp bằng chứng xã hội trước website. Gắn nhãn “web bổ sung” hoặc “thiếu dữ liệu” khi cần. Danh sách nguồn cuối trang ghi nền tảng và phương pháp lấy.
- Nếu có Excel/Markdown, cùng dùng một bộ bằng chứng đã biên tập, giữ URL gốc và trạng thái truy cập.

Không sao chép sự kiện hoặc ngày từ báo cáo kỳ cũ sang kỳ mới. Không giả định phiên đăng nhập hoặc quyền Chrome của lần trước còn hiệu lực.
