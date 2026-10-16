# Kiểm chứng mạng xã hội và bản tin điều hành

Đọc tài liệu này khi người dùng cần bản báo cáo cuối, thay vì chỉ xuất dữ liệu collector. Đây là bước biên tập bổ sung; giữ nguyên kết quả chạy tự động và lịch sử SQLite.

## Thu thập theo kỳ

1. Chốt khoảng thời gian và múi giờ. “Tuần trước” là thứ Hai 00:00 đến Chủ nhật 23:59:59 của tuần liền trước tại múi giờ cấu hình. Ghi thời điểm kiểm tra nếu số lượt xem/tương tác có thể thay đổi.
2. Với **từng đối thủ**, xác minh URL fanpage Facebook, profile TikTok và kênh YouTube từ cấu hình hoặc liên kết trên website/kênh chính thức. Đánh dấu chưa xác minh thay vì đoán handle. Thử API miễn phí được cấp quyền, sau đó RSS/feed hợp lệ. Nếu vẫn thiếu, dùng tìm kiếm web để tìm URL bài công khai và đọc bài gốc.
3. Nếu chưa đủ dữ liệu, dùng trình duyệt tích hợp Codex chỉ sau khi xác nhận phiên đăng nhập hiện có là tài khoản phụ được phép dùng cho lần chạy. Vào **trực tiếp kênh chính thức**, xem tab bài đăng/video mới, lần lượt mở các mục trong kỳ. Ghi URL từng bài, ngày, nội dung thực sự đọc được và tương tác nếu hiển thị. Không dùng search từ khóa trong Facebook/TikTok/YouTube thay cho bước này.
4. Chỉ khi vẫn thiếu mới đề nghị Chrome hoặc trình duyệt ngoài; phải có đồng ý cho **lần chạy hiện tại**. Nếu không có phiên hoặc bị lỗi, dừng tại mức bằng chứng đã có. Tuyệt đối không vượt captcha, rào đăng nhập hoặc hạn chế truy cập.
5. Sau khi đã rà xã hội mới dùng website, blog, báo và Google News để bù/đối chiếu. Tin ngành không được gán thành bài đăng của đối thủ. Không dùng tần suất đăng làm bằng chứng nhu cầu thị trường.

### Khi Facebook chưa đăng nhập trong trình duyệt Codex

- Vẫn dùng tìm kiếm web/lập chỉ mục để phát hiện bài hoặc tín hiệu Facebook công khai. Giữ từng mục ở `SEARCH_INDEX_ONLY` nếu chưa mở và đọc được bài gốc; không ghi là đã lướt fanpage, xem nội dung đầy đủ hay kiểm tương tác.
- Nếu kiểm tra cho thấy chưa đăng nhập tài khoản phụ, bỏ qua riêng bước Facebook trong trình duyệt Codex; không thử vượt màn đăng nhập. Ghi trong kết quả: “Chưa đăng nhập tài khoản phụ trong trình duyệt Codex, nên chưa thể kiểm trực tiếp fanpage. Dữ liệu Facebook hiện chỉ từ chỉ mục tìm kiếm; vui lòng tự đăng nhập tài khoản phụ để kiểm chứng bài gốc.” Không yêu cầu thông tin đăng nhập.
- Nếu chưa kiểm được trạng thái phiên, dùng câu “Chưa xác nhận phiên đăng nhập tài khoản phụ...” thay vì quả quyết người dùng đã đăng xuất. Nếu đang đăng nhập nhưng chưa được xác nhận là tài khoản phụ được phép dùng, cũng không sử dụng phiên đó. Chỉ dùng Chrome/trình duyệt ngoài khi được người dùng đồng ý riêng cho lần chạy.

### Khi tìm kiếm TikTok báo lỗi

- Nếu giao diện hiện nút **Thử lại**, bấm một lần và đợi trang tải xong, rồi kiểm tra lại kết quả. Nếu lỗi tạm thời vẫn còn, có thể thử thêm một lần; sau đó dừng và ghi tình trạng, không lặp vô hạn hoặc báo đã quét thành công.
- Nếu tìm kiếm hoạt động trở lại, chỉ dùng nó để xác minh profile/URL. Sau đó vào trực tiếp kênh đối thủ, lướt từng video trong kỳ và ghi những gì thật sự đọc/xem được. Nếu vẫn lỗi nhưng đã có URL profile chính thức, thử mở trực tiếp profile theo đúng tầng truy cập đã được phép.

Mọi bước chỉ đọc: không thích, bình luận, theo dõi, nhắn tin, đăng bài. Có thể dùng chỉ mục tìm kiếm để *phát hiện* một URL, nhưng nhãn `SEARCH_INDEX_ONLY` phải giữ nguyên cho đến khi mở và kiểm được bài gốc. Với video dài chỉ có mô tả/transcript, nói rõ đang tóm theo phần nào. Không có số tương tác thì để trống, không ước lượng.

## Bảng bằng chứng tối thiểu

Mỗi mục giữ: đối thủ, kênh, tiêu đề/chủ đề, ngày đăng (và múi giờ nếu biết), URL gốc, nội dung tóm tắt, tương tác và thời điểm đọc nếu có, phương thức (`API`, `RSS`, `WEB_ORIGINAL`, `CODEX_BROWSER`, `EXTERNAL_BROWSER`, `SEARCH_INDEX_ONLY`), mức chắc chắn, ghi chú giới hạn. Chống trùng bằng URL chuẩn hóa và khóa nội dung; không xuất lại bài cũ như bài mới.

Tách **sự kiện** (“kênh đăng video X ngày Y”) khỏi **nhận định** (“đây là cơ hội nội dung”). Góc bỏ trống chỉ là giả thuyết trong mẫu tiếp cận, không khẳng định đối thủ chưa từng làm. Nêu lý do và cách khắc phục cho từng nguồn không truy cập được, đặc biệt TikTok/Facebook/YouTube.

## HTML điều hành

Dùng [mẫu landing page tuần 05–11/10/2026](../assets/example-report-2026-10-05_11.html) làm chuẩn hình thức (font, khoảng trắng, thứ bậc nội dung, màu, một cột). Bộ dựng tự động đã dùng [CSS mẫu](../assets/report-style.css), nhưng **không** coi nội dung lịch sử của mẫu là dữ liệu cho kỳ mới. Sau khi kiểm chứng mạng xã hội, thay tóm tắt, 5 chủ đề, hoạt động, góc bỏ trống, ý tưởng và nguồn bằng bằng chứng kỳ hiện tại. Nếu dưới 5 chủ đề đủ nguồn, hiển thị số thực tế, không bịa cho đủ mẫu.

### Năm ảnh chụp cho năm chủ đề

1. Sau `run`, mở JSON lượt chạy và chạy `python monitor.py screenshot-plan <duong-dan-run.json>`. Lệnh tạo `screenshots/manifest.json` trong thư mục lượt chạy với đúng URL bằng chứng mà HTML đã chọn cho từng chủ đề. Nếu chưa có 5 chủ đề có nguồn, dừng ở bản nháp và báo người dùng; không bù bằng chủ đề tưởng tượng.
2. Với mỗi dòng manifest, mở **đúng URL nguồn** theo thứ tự truy cập được phép, chụp màn hình phần bài đăng/video/trang chứa thông tin được dẫn, lưu `screenshots/topic-01.png` … `topic-05.png`. Xem lại ảnh để chắc tiêu đề/nội dung hiển thị khớp chủ đề. Điền `captured_at` (ngày giờ và múi giờ) cùng `method` (`CODEX_BROWSER`, `EXTERNAL_BROWSER`, hoặc phương thức chụp hợp lệ thực tế). Nếu chỉ chụp được kết quả chỉ mục, ghi rõ `SEARCH_INDEX_ONLY` và không gọi đó là bài gốc. Không sử dụng thumbnail, ảnh stock, ảnh dựng lại hoặc ảnh chụp của chủ đề khác.
3. Chạy `python monitor.py finalize-report <duong-dan-run.json>`. Lệnh kiểm đúng 5 ảnh khác nhau, đúng 5 chủ đề và URL nguồn, rồi nhúng ảnh trực tiếp vào file `*-final.html` để gửi/mở độc lập. Xem lại cả 5 ảnh và chú thích trước khi bàn giao. Nếu nguồn chặn chụp, không có phiên đăng nhập hợp lệ hoặc ảnh không khớp, giữ bản nháp và báo rõ lý do/cách khắc phục; không báo đã hoàn tất 5 ảnh.

Báo cáo mẫu lưu trong skill chứa 5 ảnh chụp trực tiếp từ reel Facebook Base.vn và bốn video YouTube được dẫn trong tuần 05–11/10/2026. Đây là bằng chứng lịch sử của **riêng kỳ mẫu**; không tái sử dụng ảnh này thay ảnh nguồn của kỳ mới.

- Mặc định đọc khoảng 3 phút, đáp ứng người đi làm không biết lập trình. Một cột dọc; mỗi heading là một section riêng. Không đặt phần “Đối thủ đang làm gì?” bên cạnh “Chủ đề nổi bật”.
- Tiêu đề chính: **Báo cáo phân tích đối thủ**. Dùng font **K2D** (Google Fonts và font dự phòng nếu offline). Thiết kế như landing page chuyên nghiệp, tương phản tốt, responsive và in được.
- Sau hero có khối **tóm tắt ngắn** trước nội dung chi tiết. Bốn phần chính: **5 chủ đề nổi bật**, **Đối thủ đang làm gì?**, **3 góc nội dung còn bỏ trống**, **5 ý tưởng cho tuần tới**. Nguồn thu thập ở cuối trang.
- Bỏ lời chú thích phòng vệ lặp lại ngay dưới các heading. Đặt giới hạn phương pháp ngắn ở cuối nguồn nếu cần. Không trình bày suy luận như sự kiện.
- Số 01–05 ngay trong các mục chủ đề phải mở **trực tiếp bài/video gốc**. Nếu một chủ đề có nhiều bằng chứng, liên kết bằng chứng phụ vào cụm từ tương ứng trong đoạn văn. Không bắt người đọc nhảy xuống cuối trang chỉ để mở nguồn.
- Trong phần đối thủ, xếp bằng chứng xã hội trước website. Gắn nhãn “web bổ sung” hoặc “thiếu dữ liệu” khi cần. Danh sách nguồn cuối trang ghi nền tảng và phương pháp lấy.
- Nếu có Excel/Markdown, cùng dùng một bộ bằng chứng đã biên tập, giữ URL gốc và trạng thái truy cập.

Không sao chép sự kiện hoặc ngày từ báo cáo kỳ cũ sang kỳ mới. Không giả định phiên đăng nhập hoặc quyền Chrome của lần trước còn hiệu lực.
