---
name: competitor-news-monitor
description: Theo dõi fanpage Facebook, kênh YouTube/TikTok và tin ngành của đối thủ để lập báo cáo thị trường có nguồn, nêu khoảng trống nội dung và ý tưởng hành động. Dùng cho bản tin tuần/ngày hoặc hồ sơ đối thủ tùy ngành; không dùng để tương tác hay vượt giới hạn nền tảng.
---

# Agent theo dõi đối thủ

Agent chạy cục bộ bằng Python 3.11+ và SQLite, không cần dịch vụ trả phí. Cấu hình mặc định ở `config/monitor.toml`; dữ liệu và lịch sử nằm trong `work/`. Skill bao gồm collector tự động **và** bước kiểm chứng xã hội thủ công: báo cáo cuối không được nâng tín hiệu tìm kiếm thành bài đã đọc trực tiếp.

## Hồ sơ ERP/CRM Việt Nam

`config/erp-crm-vn.toml` theo dõi riêng Base.vn, MISA AMIS, 1Office, ECOUNT, FastWork, CloudGO và Odoo. Không dùng chung SQLite với hồ sơ AI mặc định. Chạy trong thư mục skill:

```powershell
python .\monitor.py --config .\config\erp-crm-vn.toml --db .\work\erp-crm-vn\monitor-market.db --runs .\work\erp-crm-vn\runs run
```

Lấy đường dẫn JSON của lượt chạy rồi tạo HTML kiểm duyệt bằng:

```powershell
python .\market_profile_report.py <duong-dan-json-cua-luot-chay> <thu-muc-dau-ra>
```

Hồ sơ này ưu tiên Facebook, TikTok và YouTube trong thứ tự xem xét và trình bày; website/tin ngành chỉ đối chiếu, bổ sung khi kênh xã hội không đủ bằng chứng. Ưu tiên kênh không thay đổi mức tin cậy: tín hiệu chỉ mục luôn tách khỏi bài gốc đã xác minh, không dùng để tính tương tác hoặc khẳng định đã quét nền tảng. Bản Excel chuẩn được `monitor.py` xuất tự động. Khi cần bản HTML biên tập ngắn, đọc [quy trình social-first và chuẩn báo cáo](references/social-first-report.md) trước khi kết luận hay xuất bản. `market_profile_report.py` là báo cáo khám phá dữ liệu, **không phải** bản tin xã hội đã kiểm chứng.

## Quy trình

1. Nếu chưa khởi tạo, chạy `setup.cmd` hoặc `python monitor.py setup`.
2. Kiểm tra cấu hình bằng `python monitor.py validate-config` và xem các quyền API đang có bằng `python monitor.py doctor`. Lệnh doctor chỉ báo có/không, không in secret. Khi đổi ngành, đối thủ hoặc nguồn, đọc [hướng dẫn cấu hình](references/configuration.md).
3. Chạy thủ công bằng `run.cmd` hoặc `python monitor.py run`.
4. Đọc đường dẫn kết quả từ JSON in ra cuối lệnh. Báo cáo mỗi lượt gồm Markdown, HTML và Excel; bảng trạng thái nguồn có lý do và cách khắc phục khi chưa lấy trực tiếp. Không sửa lịch sử của lượt cũ. Nếu cần báo cáo quyết định cho lãnh đạo, kiểm chứng bài gốc và biên tập riêng theo mẫu trong [chuẩn báo cáo](references/social-first-report.md).
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
- Bản tin HTML mặc định: tiêu đề “Báo cáo phân tích đối thủ”, font K2D, bố cục landing page một cột, tóm tắt ngắn trước 5 chủ đề, tiếp theo là hoạt động đối thủ, 3 góc nội dung bỏ trống, 5 ý tưởng tuần tới và nguồn ở cuối. Số thứ tự chủ đề liên kết thẳng tới bài/video gốc, không nhảy tới phụ lục. Ít chú thích, đọc khoảng 3 phút. Các con số 5/3/5 là mặc định cho bản tin này, không ép nếu người dùng yêu cầu dạng khác.
- Nếu người dùng cần Excel/Markdown, xuất cùng dữ liệu đã kiểm chứng với URL nguồn. Chỉ gửi email hoặc cài lịch khi người dùng yêu cầu rõ; xác nhận địa chỉ/lịch cho tác vụ đó, không suy ra từ lần chạy trước.

## PEAS

- **P:** số tin mới, tỷ lệ nguồn truy cập được, tỷ lệ bằng chứng đầy đủ, số mục trùng bị loại, mức bao phủ đối thủ/chủ đề và các giới hạn còn lại.
- **E:** website, RSS, Google News, Brave/Google Search, YouTube Data API/RSS, Facebook Graph API, TikTok Display/Research API và feed xã hội được phép.
- **A:** thu thập → chuẩn hóa → chống trùng → lọc liên quan → gắn đối thủ/chủ đề → phân tích xu hướng → báo cáo và đề xuất.
- **S:** `monitor.toml`, nội dung nguồn, ngày đăng, URL, metadata và chỉ số tương tác có thật.

Đọc [kiến trúc](references/architecture.md) khi mở rộng collector hoặc schema. Đọc [phân tích repository tham khảo](references/repository-analysis.md) khi cần biết thành phần nào đã được kế thừa và thành phần nào bị loại khỏi phạm vi.
Khi cập nhật ba đối thủ AI mặc định, xem [các kênh đã và chưa xác nhận](references/verified-channels.md). Với hồ sơ ERP/CRM, xem [danh sách kênh đã kiểm](references/erp-crm-channels.md) trước khi mở trình duyệt trực tiếp.
