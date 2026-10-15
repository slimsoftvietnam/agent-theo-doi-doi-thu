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

- Mặc định đọc khoảng 3 phút, đáp ứng người đi làm không biết lập trình. Một cột dọc; mỗi heading là một section riêng. Không đặt phần “Đối thủ đang làm gì?” bên cạnh “Chủ đề nổi bật”.
- Tiêu đề chính: **Báo cáo phân tích đối thủ**. Dùng font **K2D** (Google Fonts và font dự phòng nếu offline). Thiết kế như landing page chuyên nghiệp, tương phản tốt, responsive và in được.
- Sau hero có khối **tóm tắt ngắn** trước nội dung chi tiết. Bốn phần chính: **5 chủ đề nổi bật**, **Đối thủ đang làm gì?**, **3 góc nội dung còn bỏ trống**, **5 ý tưởng cho tuần tới**. Nguồn thu thập ở cuối trang.
- Bỏ lời chú thích phòng vệ lặp lại ngay dưới các heading. Đặt giới hạn phương pháp ngắn ở cuối nguồn nếu cần. Không trình bày suy luận như sự kiện.
- Số 01–05 ngay trong các mục chủ đề phải mở **trực tiếp bài/video gốc**. Nếu một chủ đề có nhiều bằng chứng, liên kết bằng chứng phụ vào cụm từ tương ứng trong đoạn văn. Không bắt người đọc nhảy xuống cuối trang chỉ để mở nguồn.
- Trong phần đối thủ, xếp bằng chứng xã hội trước website. Gắn nhãn “web bổ sung” hoặc “thiếu dữ liệu” khi cần. Danh sách nguồn cuối trang ghi nền tảng và phương pháp lấy.
- Nếu có Excel/Markdown, cùng dùng một bộ bằng chứng đã biên tập, giữ URL gốc và trạng thái truy cập.

Không sao chép sự kiện hoặc ngày từ báo cáo kỳ cũ sang kỳ mới. Không giả định phiên đăng nhập hoặc quyền Chrome của lần trước còn hiệu lực.
