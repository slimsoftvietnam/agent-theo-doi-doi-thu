---
name: competitor-news-monitor
description: Theo dõi fanpage Facebook, kênh YouTube/TikTok và tin ngành của đối thủ để lập báo cáo thị trường có nguồn, nêu khoảng trống nội dung và ý tưởng hành động. Dùng cho bản tin tuần/ngày hoặc hồ sơ đối thủ tùy ngành; không dùng để tương tác hay vượt giới hạn nền tảng.
---

# Agent theo dõi đối thủ

Agent chạy cục bộ bằng Python 3.11+ và SQLite, không cần dịch vụ trả phí. Cấu hình mặc định ở `config/monitor.toml`; dữ liệu và lịch sử nằm trong `work/`. Skill bao gồm collector tự động **và** bước kiểm chứng xã hội thủ công: báo cáo cuối không được nâng tín hiệu tìm kiếm thành bài đã đọc trực tiếp.

## Hợp đồng đầu ra — bắt buộc

Khi người dùng yêu cầu phân tích/báo cáo đối thủ, **đầu ra chính luôn là tệp HTML đẹp có thể mở trực tiếp**, không phải Markdown, JSON hay chỉ một đoạn trả lời trong chat. Dùng bộ dựng `monitor.py` và `assets/report-style.css` kế thừa phong cách [báo cáo mẫu 05–11/10/2026](assets/example-report-2026-10-05_11.html); thay **toàn bộ dữ liệu kỳ mẫu** bằng dữ liệu mới, không sao chép ảnh hoặc nhận định cũ. Mở/kiểm tra tệp HTML trước khi bàn giao và đặt liên kết tới HTML lên trước; Markdown/Excel chỉ là tệp bổ sung khi cần.

Mục tiêu là tối đa 5 chủ đề nổi bật có bằng chứng; **số đối thủ không quyết định số chủ đề**. Mỗi chủ đề được trình bày phải có đúng một ảnh chụp màn hình thật của URL nguồn tương ứng trong `*-final.html` (1–5 chủ đề → 1–5 ảnh). Agent tự chụp và kiểm ảnh, không giao bước này cho người dùng; không dùng ảnh mẫu, thumbnail, ảnh dựng hay ảnh của bài khác. Nếu không lấy/chụp được một hoặc nhiều nguồn, vẫn bàn giao **HTML bản nháp theo cùng thiết kế**, ghi rõ phạm vi thiếu và cách khắc phục; không gọi bản nháp là báo cáo cuối có ảnh, và **không bao giờ thay HTML bằng file `.md`**.

## Lần đầu sau khi cài skill

Ở **lần gọi skill đầu tiên**, chạy `python monitor.py preview` để lấy đường dẫn, mở và đưa người dùng xem [báo cáo mẫu 05–11/10/2026](assets/example-report-2026-10-05_11.html). Mẫu này đã có 5 ảnh chụp trực tiếp từ 5 nguồn tương ứng, nhúng trong HTML; đây vẫn là ví dụ lịch sử, không phải báo cáo cập nhật hay dữ liệu mặc định của người cài. Sau đó hỏi trong một lượt:

1. Tên các đối thủ muốn theo dõi; URL fanpage Facebook, kênh TikTok, YouTube của **từng** đối thủ (có thể ghi “chưa biết” để agent hỗ trợ xác minh); URL website/blog là **tùy chọn**.
2. Thông tin doanh nghiệp người dùng: tên công ty, sản phẩm/dịch vụ chính, khách hàng mục tiêu và thị trường/ngành; website công ty nếu có. Dùng bối cảnh này để chọn chủ đề, góc nội dung và ý tưởng phù hợp, không công bố thông tin nhạy cảm nếu chưa được phép.

Chỉ sau khi có câu trả lời mới lập cấu hình riêng cho người dùng trong `work/` theo [hướng dẫn cấu hình](references/configuration.md); không mặc định dùng hồ sơ ERP/CRM mẫu như dữ liệu của họ. Nếu thiếu URL xã hội, đánh dấu chưa xác minh, tìm kênh chính thức công khai và xin người dùng xác nhận nếu còn mơ hồ. Không tự ý tạo lịch hay bắt đầu thu thập trước khi phạm vi được chốt. Skill cài đặt không tự chạy/có sự kiện hậu cài đặt: bước xem mẫu và hỏi thông tin diễn ra khi người dùng gọi skill lần đầu.

## Hồ sơ ERP/CRM Việt Nam

`config/erp-crm-vn.toml` theo dõi riêng Base.vn, MISA AMIS, 1Office, ECOUNT, FastWork, CloudGO và Odoo. Không dùng chung SQLite với hồ sơ AI mặc định. Chạy trong thư mục skill:

```powershell
python .\monitor.py --config .\config\erp-crm-vn.toml --db .\work\erp-crm-vn\monitor-market.db --runs .\work\erp-crm-vn\runs run
```

Lấy đường dẫn JSON của lượt chạy để tạo kế hoạch ảnh theo số chủ đề có nguồn và bản HTML cuối bằng `screenshot-plan` rồi `finalize-report` như [quy trình bên dưới](#quy-trình). `market_profile_report.py` chỉ dùng khi cần khám phá dữ liệu, không phải đường xuất bản báo cáo cuối.

Hồ sơ này ưu tiên Facebook, TikTok và YouTube trong thứ tự xem xét và trình bày; website/tin ngành chỉ đối chiếu, bổ sung khi kênh xã hội không đủ bằng chứng. Ưu tiên kênh không thay đổi mức tin cậy: tín hiệu chỉ mục luôn tách khỏi bài gốc đã xác minh, không dùng để tính tương tác hoặc khẳng định đã quét nền tảng. Bản Excel chuẩn được `monitor.py` xuất tự động. Khi cần bản HTML biên tập ngắn, đọc [quy trình social-first và chuẩn báo cáo](references/social-first-report.md) trước khi kết luận hay xuất bản. `market_profile_report.py` là báo cáo khám phá dữ liệu, **không phải** bản tin xã hội đã kiểm chứng.

## Quy trình

1. Nếu chưa khởi tạo, chạy `setup.cmd` hoặc `python monitor.py setup`.
2. Kiểm tra cấu hình bằng `python monitor.py validate-config` và xem các quyền API đang có bằng `python monitor.py doctor`. Lệnh doctor chỉ báo có/không, không in secret. Khi đổi ngành, đối thủ hoặc nguồn, đọc [hướng dẫn cấu hình](references/configuration.md).
3. Chạy thủ công bằng `run.cmd` hoặc `python monitor.py run`.
4. Đọc `primary_report` (HTML bản nháp) và JSON lượt chạy từ kết quả lệnh; Markdown và Excel chỉ bổ sung. **Không kết thúc công việc bằng `.md`**. Chạy `python monitor.py screenshot-plan <run.json>`, tự mở/chụp đúng nguồn cho mỗi chủ đề có bằng chứng, điền manifest rồi chạy `python monitor.py finalize-report <run.json>`. Lệnh cuối chỉ xuất `*-final.html` khi số ảnh bằng số chủ đề được chọn (tối đa 5), ảnh khác nhau và khớp URL; ảnh nhúng trong HTML nên mở ngoại tuyến không mất. Mở và xem lại HTML cuối, ảnh và các liên kết trước khi bàn giao. Nếu không thể hoàn thiện ảnh, bàn giao HTML bản nháp đã có sẵn cùng lý do/cách khắc phục, tuyệt đối không thay bằng Markdown hoặc ngầm báo đã hoàn tất. Đọc [quy trình ảnh chụp](references/social-first-report.md). Không sửa lịch sử của lượt cũ.
5. Nếu người dùng muốn tự động hóa Windows, dùng `scripts/install-schedule.ps1 -Install` sau khi họ xác nhận lịch. Không tự ý tạo lịch hệ thống.

## Nguyên tắc bắt buộc

- Theo dõi đúng khoảng thời gian người dùng yêu cầu; với “tuần trước”, lấy thứ Hai–Chủ nhật trước ngày chạy theo múi giờ trong cấu hình, không lấy cửa sổ 7 hoặc 30 ngày trượt.
- Với hồ sơ ERP/CRM, xét kênh xã hội trước rồi mới dùng website/tin ngành để kiểm chứng hoặc bù dữ liệu. Thử theo thứ tự: API miễn phí hợp lệ → RSS nếu nền tảng có → tìm và đọc bài công khai trên web → trình duyệt tích hợp Codex **chỉ khi đã xác nhận phiên đăng nhập bằng tài khoản phụ được phép dùng** → Chrome/trình duyệt ngoài **chỉ khi người dùng đồng ý riêng cho lần chạy đó**. Chỉ chuyển tầng khi tầng trước không lấy đủ thông tin cần thiết; không xem kết quả tìm kiếm là đã đọc bài gốc.
- Khi dùng trình duyệt, đi thẳng vào fanpage/kênh chính thức đã xác minh; lướt từng bài/video mới trong kỳ, mở bài/video gốc để kiểm ngày, nội dung và chỉ số tương tác nếu hiển thị. Không dùng tìm kiếm từ khóa *trên nền tảng* thay cho việc kiểm kênh trực tiếp. Với video dài chỉ đọc tiêu đề/mô tả thì ghi đúng mức đó, không nhận là đã xem hết.
- Riêng Facebook: nếu trình duyệt tích hợp chưa đăng nhập tài khoản phụ được phép dùng, **bỏ qua bước xem fanpage trong trình duyệt tích hợp**, nhưng vẫn tìm và phân tích các kết quả đã được máy tìm kiếm lập chỉ mục với nhãn `SEARCH_INDEX_ONLY`. Báo cáo nói rõ chưa dùng được trình duyệt tích hợp vì chưa đăng nhập; đề nghị người dùng tự đăng nhập tài khoản phụ để kiểm chứng bài gốc ở lượt sau. Nếu chỉ chưa xác nhận trạng thái đăng nhập, ghi “chưa xác nhận phiên đăng nhập”, không khẳng định đã đăng xuất. Không yêu cầu mật khẩu.
- Nếu trang tìm kiếm TikTok hiển thị lỗi tạm thời cùng nút **Thử lại**, bấm nút này trên màn hình rồi kiểm tra lại kết quả trước khi đánh dấu nguồn bị giới hạn. Không lặp vô hạn; nếu vẫn lỗi, ghi lỗi và mức dữ liệu thực sự lấy được. Khi đã xác minh URL kênh, vào trực tiếp profile và từng video mới thay vì chỉ dựa vào tìm kiếm.
- Website dùng feed discovery, sitemap, JSON-LD, ETag/Last-Modified và content hash; không đi qua URL bị `robots.txt` từ chối.
- YouTube dùng Data API uploads playlist khi có khóa, rồi RSS. Facebook dùng Graph API. TikTok dùng Display API, Research API đã được duyệt hoặc feed được cấp quyền.
- Khi thiếu quyền Facebook/TikTok/YouTube, có thể phát hiện URL qua Brave, Google Custom Search hoặc Google News RSS nhưng bắt buộc gắn `SEARCH_INDEX_ONLY`.
- Ghi `LIMITED`, `MANUAL_REVIEW` hoặc `ERROR` khi không truy cập được. `SEARCH_INDEX_ONLY` không được diễn đạt như đã quét trực tiếp nền tảng.
- Giữ sự kiện có nguồn tách khỏi nhận định suy ra từ dữ liệu. Mỗi dòng dữ liệu phải có URL, ngày đăng nếu nguồn cung cấp, phương thức thu thập và trạng thái bằng chứng.
- Dùng URL chuẩn hóa và khóa nội dung trong SQLite để tránh lặp giữa các lượt chạy. Không xóa lịch sử khi thay cấu hình.
- Ở mọi tầng chỉ xem và ghi chép: không thích, bình luận, theo dõi, nhắn tin hay đăng bài. Không dùng phiên đăng nhập cá nhân nếu người dùng chỉ cho phép tài khoản phụ.
- Mỗi nhận định cần nguồn gốc trực tiếp khi có thể, ngày đăng, cách thu thập và mức bằng chứng. Nếu nền tảng chặn, kênh chưa xác minh hoặc không có bài đúng kỳ, nêu lý do và cách khắc phục; không biến “không lấy được” thành “không có hoạt động”.
- Bản tin HTML cuối mặc định: **tệp `*-final.html` đẹp, mở độc lập**, theo [mẫu có 5 ảnh thật](assets/example-report-2026-10-05_11.html): tiêu đề “Báo cáo phân tích đối thủ”, font K2D, bố cục landing page một cột, tóm tắt ngắn trước tối đa **5 chủ đề nổi bật, mỗi chủ đề một ảnh chụp nguồn**, tiếp theo là hoạt động đối thủ, 3 góc nội dung bỏ trống, 5 ý tưởng tuần tới và nguồn ở cuối. Số thứ tự chủ đề liên kết thẳng tới bài/video gốc. Kiểm số ảnh nhúng bằng số chủ đề hiển thị, mở HTML và xem ảnh thật trước khi bàn giao. Nếu không có chủ đề đủ nguồn hoặc không chụp được ảnh thật, dùng HTML bản nháp cùng thiết kế, nói rõ giới hạn và cách khắc phục; không giả vờ có ảnh và không bàn giao Markdown thay HTML.
- Nếu người dùng cần Excel/Markdown, xuất cùng dữ liệu đã kiểm chứng với URL nguồn. Chỉ gửi email hoặc cài lịch khi người dùng yêu cầu rõ; xác nhận địa chỉ/lịch cho tác vụ đó, không suy ra từ lần chạy trước.

## PEAS

- **P:** số tin mới, tỷ lệ nguồn truy cập được, tỷ lệ bằng chứng đầy đủ, số mục trùng bị loại, mức bao phủ đối thủ/chủ đề và các giới hạn còn lại.
- **E:** website, RSS, Google News, Brave/Google Search, YouTube Data API/RSS, Facebook Graph API, TikTok Display/Research API và feed xã hội được phép.
- **A:** thu thập → chuẩn hóa → chống trùng → lọc liên quan → gắn đối thủ/chủ đề → phân tích xu hướng → báo cáo và đề xuất.
- **S:** `monitor.toml`, nội dung nguồn, ngày đăng, URL, metadata và chỉ số tương tác có thật.

Đọc [kiến trúc](references/architecture.md) khi mở rộng collector hoặc schema. Đọc [phân tích repository tham khảo](references/repository-analysis.md) khi cần biết thành phần nào đã được kế thừa và thành phần nào bị loại khỏi phạm vi.
Khi cập nhật ba đối thủ AI mặc định, xem [các kênh đã và chưa xác nhận](references/verified-channels.md). Với hồ sơ ERP/CRM, xem [danh sách kênh đã kiểm](references/erp-crm-channels.md) trước khi mở trình duyệt trực tiếp.
